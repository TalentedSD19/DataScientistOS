import json

from backend.llm import get_llm
from backend.mcp_client import call
from backend.schemas import VerifierResult
from backend.config import MAX_STEPS

PROMPT = """You are an expert data analyst.
Your task is to check whether the current plan and its code implementation is enough to
answer the question.

# Plan
{plan}

# Code
```python
{code}
```

# Execution result of code
{result}

# Files currently in the workspace (from `find . -type f` in the sandbox)
{workspace_files}

# Question
{prompt}

# Your task
- Verify whether the current plan and its code implementation is enough to answer the
  question.
- If the question or plan requires creating a file (e.g. a saved chart, trained model,
  or processed dataset), check the file listing above and confirm that file actually
  exists there -- do not take the code's print statements or comments as proof it was
  saved.
- If it is enough, answer SUFFICIENT. Otherwise, answer INSUFFICIENT.
"""


async def _list_workspace_files(task_id: str) -> str:
    """Ground truth for what's actually on disk, via the shell tool -- not just
    what the generated code claims to have printed or saved."""
    raw = await call("execute_shell", task_id=task_id, command="find . -type f | sort")
    result = json.loads(raw) if isinstance(raw, str) else raw
    return result.get("stdout") or "(no files found)"


async def verifier_node(state: dict) -> dict:
    llm = get_llm("verifier").with_structured_output(VerifierResult)
    run = state.get("execution_result", {})
    plan = state.get("plan", [])

    workspace_files = await _list_workspace_files(state["task_id"])

    result: VerifierResult = await llm.ainvoke(PROMPT.format(
        plan="\n".join(f"{s['step_id']}. {s['goal']}" for s in plan),
        code=state.get("code", ""),
        result=(run.get("stdout") or "")[-3000:],
        workspace_files=workspace_files,
        prompt=state["user_prompt"],
    ))

    message = f"verifier: {result.status} ({len(workspace_files.splitlines())} file(s) on disk)"
    if result.status != "SUFFICIENT" and state.get("step_count", 0) >= MAX_STEPS:
        message += f" - reached the {MAX_STEPS}-step limit, stopping here"

    return {
        "verifier_status": result.status,
        "logs": [message],
    }
