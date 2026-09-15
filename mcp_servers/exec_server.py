import json

from mcp.server.fastmcp import FastMCP

from backend import docker_runner
from backend.config import workspace_dir

mcp = FastMCP("execution", host="127.0.0.1", port=8012)


def _snapshot(task_id: str) -> set[str]:
    """Set of every file currently in the workspace. Used to spot new files."""
    ws = workspace_dir(task_id)
    return {str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()}


@mcp.tool()
def execute_file(task_id: str, path: str, timeout: int = 600) -> str:
    """Run a Python file that already exists in the workspace, inside the Docker sandbox."""
    before = _snapshot(task_id)
    result = docker_runner.run_python_file(task_id, path, timeout=timeout)
    result["files_created"] = sorted(_snapshot(task_id) - before)
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
