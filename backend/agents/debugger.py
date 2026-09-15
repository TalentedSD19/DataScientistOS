import json
import re

from backend.llm import get_llm
from backend.mcp_client import call
from backend.config import MAX_DEBUG_ATTEMPTS

SYSTEM = "You fix broken Python scripts. Reply with the corrected script only, no explanation, no markdown fences."

PROMPT = """CODE WITH AN ERROR:
{code}
{attempt_note}
OUTPUT BEFORE THE ERROR:
{stdout}

ERROR:
{traceback}
{context}
Please revise the code to fix the error. Reply with the complete corrected script."""

ATTEMPT_NOTE = """
This is attempt {attempt} of {max_attempts} to fix this same error -- the previous
fix did not work, so don't just repeat it. Look for a different, more fundamental cause
(e.g. a change that looks like it worked but silently didn't, such as a pandas chained
assignment that doesn't actually mutate the DataFrame).
"""

WITH_CONTEXT = """
DATA:
{descriptions}
"""

# Matches the last line of a ModuleNotFoundError / ImportError traceback, e.g.
# "ModuleNotFoundError: No module named 'xgboost'"
MISSING_MODULE = re.compile(r"No module named ['\"]([\w.\-]+)['\"]")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("python"):
            text = text[len("python"):]
    return text.strip()


async def install_missing_package(task_id: str, traceback: str) -> str | None:
    """If the traceback is a missing-import error, pip install that package inside
    the task's sandbox via the execute_shell tool, instead of asking the LLM to
    rewrite code that was already correct. Returns the package name if one was
    found and successfully installed, otherwise None (nothing to install, or the
    install itself failed -- either way the caller should fall back to fix_code)."""
    match = MISSING_MODULE.search(traceback)
    if not match:
        return None

    package = match.group(1).split(".")[0]
    raw = await call("execute_shell", task_id=task_id, command=f"pip install --quiet {package}")
    result = json.loads(raw) if isinstance(raw, str) else raw
    return package if result.get("exit_code") == 0 else None


async def fix_code(
    code: str, traceback: str, stdout: str = "", attempt: int = 1,
    data_descriptions: dict | None = None,
) -> str:
    """Ask the debugger agent to fix one script. With no data_descriptions this matches
    the analyzer's debug step (Eq. 8: fix using only the traceback); with
    data_descriptions given it matches the solution-code debug step (Eq. 9), since a
    traceback alone is often not enough to fix a data-centric script.

    stdout is whatever the script printed before it crashed -- often the only way to
    tell that an earlier "fix" silently didn't do what it claimed. attempt lets the
    model know if it's already tried (and failed) to fix this same error before."""
    llm = get_llm("debugger")
    context = WITH_CONTEXT.format(
        descriptions=json.dumps(data_descriptions, indent=2)[:6000]
    ) if data_descriptions else ""
    attempt_note = ATTEMPT_NOTE.format(
        attempt=attempt, max_attempts=MAX_DEBUG_ATTEMPTS,
    ) if attempt > 1 else ""

    response = await llm.ainvoke([("system", SYSTEM), ("user", PROMPT.format(
        code=code, stdout=stdout[-1500:], traceback=traceback[-2000:],
        attempt_note=attempt_note, context=context,
    ))])
    return _strip_fences(response.content)


async def debugger_node(state: dict) -> dict:
    task_id = state["task_id"]
    run = state.get("execution_result") or {}
    traceback = run.get("stderr") or ""
    stdout = run.get("stdout") or ""
    attempts = state.get("debug_attempts", 0) + 1

    installed = await install_missing_package(task_id, traceback)
    if installed:
        # The code itself was fine -- the sandbox just lacked this package. Leave
        # src/main.py untouched and let the executor simply retry it.
        return {
            "debug_attempts": attempts,
            "logs": [f"debugger: attempt {attempts} - installed missing package '{installed}'"],
        }

    relevant = state.get("relevant_files") or state.get("input_files", [])
    descriptions = {f: state.get("data_descriptions", {}).get(f, "") for f in relevant}

    code = await fix_code(
        code=state.get("code", ""),
        traceback=traceback,
        stdout=stdout,
        attempt=attempts,
        data_descriptions=descriptions,
    )
    await call("write_file", task_id=task_id, path="src/main.py", content=code)

    return {
        "code": code,
        "debug_attempts": attempts,
        "logs": [f"debugger: attempt {attempts}"],
    }
