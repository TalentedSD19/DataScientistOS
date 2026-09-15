"""The single MCP server that exposes every tool DS-STAR's agents use to touch
the outside world.

Three tools, and that's all an agent needs:
  - write_file:     put a script into a task's workspace
  - execute_file:   run a script that's already there, inside that task's
                     Docker sandbox, and report what happened
  - execute_shell:  run any shell command in that same sandbox (e.g. `pip
                     install <package>` when the debugger hits a missing import)

Every agent (analyzer, coder, debugger, executor) talks to this one server
through backend.mcp_client -- there is no separate server per tool.
"""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from backend import docker_runner
from backend.config import workspace_dir

mcp = FastMCP("dsstar-tools", host="127.0.0.1", port=8011)


def _resolve(task_id: str, rel_path: str) -> Path:
    """Turn 'src/main.py' into a real path, and refuse to go outside the workspace."""
    ws = workspace_dir(task_id).resolve()
    full = (ws / rel_path.lstrip("/\\")).resolve()
    if not str(full).startswith(str(ws)):
        raise ValueError("that path is outside the workspace")
    return full


def _snapshot(task_id: str) -> set[str]:
    """Every file currently in the workspace. Used to spot files a run created."""
    ws = workspace_dir(task_id)
    return {str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()}


@mcp.tool()
def write_file(task_id: str, path: str, content: str) -> str:
    """Write a script into the task's workspace. Creates folders if needed."""
    p = _resolve(task_id, path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return json.dumps({"ok": True, "path": path, "bytes": len(content)})


@mcp.tool()
def execute_file(task_id: str, path: str, timeout: int = 600) -> str:
    """Run a Python file that already exists in the workspace, inside the task's
    Docker sandbox, and report exit code, stdout/stderr, and any new files."""
    before = _snapshot(task_id)
    result = docker_runner.run_python_file(task_id, path, timeout=timeout)
    result["files_created"] = sorted(_snapshot(task_id) - before)
    return json.dumps(result)


@mcp.tool()
def execute_shell(task_id: str, command: str, timeout: int = 600) -> str:
    """Run any shell command inside the task's Docker sandbox -- most commonly
    `pip install <package>` to add a library the generated code needs -- and
    report exit code, stdout/stderr, and any new files. Requires ALLOW_NETWORK=true
    (see backend/config.py) for anything that needs internet access, like pip."""
    before = _snapshot(task_id)
    result = docker_runner.exec_shell(task_id, command, timeout=timeout)
    result["files_created"] = sorted(_snapshot(task_id) - before)
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
