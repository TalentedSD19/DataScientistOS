import json
import uuid

from mcp.server.fastmcp import FastMCP

from backend import docker_runner
from backend.config import workspace_dir

mcp = FastMCP("execution", host="127.0.0.1", port=8012)


def _snapshot(task_id: str) -> set[str]:
    """Set of every file currently in the workspace. Used to spot new files."""
    ws = workspace_dir(task_id)
    return {str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()}


@mcp.tool()
def execute_python(task_id: str, code: str, timeout: int = 600) -> str:
    """Run a short piece of Python inside the sandbox."""
    name = f"src/_snippet_{uuid.uuid4().hex[:6]}.py"
    path = workspace_dir(task_id) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")

    before = _snapshot(task_id)
    result = docker_runner.run_python_file(task_id, name, timeout=timeout)
    result["files_created"] = sorted(_snapshot(task_id) - before)
    return json.dumps(result)


@mcp.tool()
def execute_file(task_id: str, path: str = "src/main.py", timeout: int = 600) -> str:
    """Run a Python file that already exists in the workspace."""
    before = _snapshot(task_id)
    result = docker_runner.run_python_file(task_id, path, timeout=timeout)
    result["files_created"] = sorted(_snapshot(task_id) - before)

    # Save the run log so we can look at it later
    logs = workspace_dir(task_id) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "execution.log").write_text(json.dumps(result, indent=2), encoding="utf-8")

    return json.dumps(result)


@mcp.tool()
def execute_shell(task_id: str, command: str, timeout: int = 300) -> str:
    """Run a shell command inside the sandbox."""
    return json.dumps(docker_runner.exec_shell(task_id, command, timeout))


@mcp.tool()
def install_package(task_id: str, package: str) -> str:
    """Install a python package inside the sandbox (needs internet turned on)."""
    return json.dumps(docker_runner.install_package(task_id, package))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")