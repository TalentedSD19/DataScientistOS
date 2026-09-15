import docker

from backend.config import (
    RUNTIME_IMAGE, EXEC_TIMEOUT, CPU_LIMIT, MEM_LIMIT,
    ALLOW_NETWORK, workspace_dir,
)

# Connects to Docker Desktop
_client = docker.from_env()


def container_name(task_id: str) -> str:
    return f"ds-task-{task_id}"


def get_or_create(task_id: str):
    """Return the task's container. Create it the first time."""
    name = container_name(task_id)

    # Already exists? Just make sure it's running.
    try:
        container = _client.containers.get(name)
        if container.status != "running":
            container.start()
        return container
    except docker.errors.NotFound:
        pass

    # Doesn't exist yet -- create it.
    ws = workspace_dir(task_id)
    ws.mkdir(parents=True, exist_ok=True)

    return _client.containers.run(
        RUNTIME_IMAGE,
        name=name,
        command="sleep infinity",   # stay alive
        detach=True,
        working_dir="/workspace",
        # This line is the important one: the host folder becomes /workspace inside.
        # So anything the code writes, we can read directly from Windows.
        volumes={str(ws.resolve()): {"bind": "/workspace", "mode": "rw"}},
        nano_cpus=int(CPU_LIMIT * 1e9),
        mem_limit=MEM_LIMIT,
        pids_limit=256,
        network_disabled=not ALLOW_NETWORK,
        environment={"MPLBACKEND": "Agg", "PYTHONUNBUFFERED": "1"},
    )


def _quote(text: str) -> str:
    """Wrap a command in single quotes safely for bash."""
    return "'" + text.replace("'", "'\"'\"'") + "'"


def exec_shell(task_id: str, command: str, timeout: int = EXEC_TIMEOUT) -> dict:
    """Run any shell command inside the task container and capture the output."""
    container = get_or_create(task_id)

    # 'timeout N' kills the command if it runs too long
    wrapped = f"timeout {timeout} bash -lc {_quote(command)}"
    result = container.exec_run(wrapped, workdir="/workspace", demux=True)

    # demux=True gives us (stdout, stderr) separately
    out, err = result.output if isinstance(result.output, tuple) else (result.output, b"")

    return {
        "exit_code": result.exit_code,                              # 0 means success
        "stdout": (out or b"").decode("utf-8", "replace")[-20000:],  # keep the tail only
        "stderr": (err or b"").decode("utf-8", "replace")[-20000:],
    }


def run_python_file(task_id: str, rel_path: str, timeout: int = EXEC_TIMEOUT) -> dict:
    """Run a python file that lives inside the workspace, e.g. 'src/main.py'."""
    return exec_shell(task_id, f"python -u {rel_path}", timeout=timeout)


def destroy(task_id: str) -> None:
    """Delete the container. The files on disk stay."""
    try:
        _client.containers.get(container_name(task_id)).remove(force=True)
    except docker.errors.NotFound:
        pass