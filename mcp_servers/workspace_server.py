import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from backend.config import workspace_dir

mcp = FastMCP("workspace", host="127.0.0.1", port=8011)


def _resolve(task_id: str, rel_path: str) -> Path:
    """Turn 'src/main.py' into a real path, and refuse to go outside the workspace."""
    ws = workspace_dir(task_id).resolve()
    full = (ws / rel_path.lstrip("/\\")).resolve()
    if not str(full).startswith(str(ws)):
        raise ValueError("that path is outside the workspace")
    return full


@mcp.tool()
def write_file(task_id: str, path: str, content: str) -> str:
    """Write a script into the task's workspace. Creates folders if needed."""
    p = _resolve(task_id, path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return json.dumps({"ok": True, "path": path, "bytes": len(content)})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
