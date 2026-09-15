import json

from backend.mcp_client import call
from backend.config import EXEC_TIMEOUT


def _summarise_error(result: dict) -> dict:
    """Turn a long traceback into one short line. Long tracebacks waste tokens."""
    if result.get("exit_code") == 0:
        return {"error_type": None, "error_summary": None}

    lines = [l for l in (result.get("stderr") or "").strip().splitlines() if l.strip()]
    last_line = lines[-1] if lines else "unknown error"
    error_type = last_line.split(":")[0].strip() if ":" in last_line else "Error"

    return {
        "error_type": error_type,
        "error_summary": last_line[:300],
        "relevant_traceback": "\n".join(lines[-15:]),
    }


async def execute_node(state: dict) -> dict:
    raw = await call("execute_file",
                     task_id=state["task_id"], path="src/main.py",
                     timeout=EXEC_TIMEOUT)
    result = json.loads(raw) if isinstance(raw, str) else raw

    return {
        "execution_result": {**result, **_summarise_error(result)},
        "generated_files": result.get("files_created", []),
        "logs": [f"executor: exit code {result.get('exit_code')}, "
                 f"{len(result.get('files_created', []))} new files"],
    }
