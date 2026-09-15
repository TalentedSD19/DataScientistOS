import json

from backend.llm import get_llm

SYSTEM = "You fix broken Python scripts. Reply with the corrected script only, no explanation, no markdown fences."

PROMPT = """CODE WITH AN ERROR:
{code}

ERROR:
{traceback}
{context}
Please revise the code to fix the error. Reply with the complete corrected script."""

WITH_CONTEXT = """
DATA:
{descriptions}
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("python"):
            text = text[len("python"):]
    return text.strip()


async def fix_code(code: str, traceback: str, data_descriptions: dict | None = None) -> str:
    """Ask the debugger agent to fix one script. With no data_descriptions this matches
    the analyzer's debug step (Eq. 8: fix using only the traceback); with
    data_descriptions given it matches the solution-code debug step (Eq. 9), since a
    traceback alone is often not enough to fix a data-centric script."""
    llm = get_llm("debugger")
    context = WITH_CONTEXT.format(
        descriptions=json.dumps(data_descriptions, indent=2)[:6000]
    ) if data_descriptions else ""

    response = await llm.ainvoke([("system", SYSTEM), ("user", PROMPT.format(
        code=code, traceback=traceback[-2000:], context=context,
    ))])
    return _strip_fences(response.content)


async def debugger_node(state: dict) -> dict:
    task_id = state["task_id"]
    run = state.get("execution_result", {})
    relevant = state.get("relevant_files") or state.get("input_files", [])
    descriptions = {f: state.get("data_descriptions", {}).get(f, "") for f in relevant}

    from backend.mcp_client import call
    code = await fix_code(
        code=state.get("code", ""),
        traceback=run.get("stderr") or "",
        data_descriptions=descriptions,
    )
    await call("write_file", task_id=task_id, path="src/main.py", content=code)

    attempts = state.get("debug_attempts", 0) + 1
    return {
        "code": code,
        "debug_attempts": attempts,
        "logs": [f"debugger: attempt {attempts}"],
    }
