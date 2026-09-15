from backend.llm import get_llm
from backend.config import workspace_dir
from backend.workspace import list_workspace_files

SUCCESS_PROMPT = """You are writing a short report for someone who just ran a data analysis task.

# Their question
{prompt}

# Steps taken
{steps}

# What the code printed
{output}

# Files created
{files}

# Your task
Write a short report in markdown, in plain language, with these sections:
## Answer
Directly answer the question above, using the output. Give real numbers or values where you have them.
## Steps
A short bullet list of what was done, one line per step.
## Files
List the files created, one per line. If none were created, say so.

Keep it brief and readable. Do not restate the question, and do not add extra sections.
"""

FAILURE_PROMPT = """You are writing a short report for someone whose data analysis task did not finish successfully.

# Their question
{prompt}

# Steps attempted
{steps}

# What went wrong
{reason}

# Your task
Write a short report in markdown, in plain language, with these sections:
## What happened
Explain plainly why this didn't produce an answer, based on what went wrong above.
## Steps attempted
A short bullet list of what was tried, one line per step.

Keep it brief and honest. Do not apologize, and do not add extra sections.
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("markdown"):
            text = text[len("markdown"):]
    return text.strip()


def _created_files(task_id: str) -> list[str]:
    """Files worth telling the user about -- not the ones they uploaded,
    not our own internal bookkeeping."""
    return [
        f for f in list_workspace_files(task_id)
        if not f.startswith("input/") and not f.startswith("state/")
    ]


def _steps_text(plan: list[dict]) -> str:
    if not plan:
        return "(no steps were taken)"
    return "\n".join(f"{s['step_id']}. {s['goal']}" for s in plan)


async def reporter_node(state: dict) -> dict:
    task_id = state["task_id"]
    llm = get_llm("reporter")
    steps = _steps_text(state.get("plan", []))
    files = _created_files(task_id)
    run = state.get("execution_result") or {}

    if state.get("verifier_status") == "SUFFICIENT":
        prompt = SUCCESS_PROMPT.format(
            prompt=state["user_prompt"],
            steps=steps,
            output=(run.get("stdout") or "")[-3000:] or "(no output)",
            files="\n".join(f"- {f}" for f in files) or "(none)",
        )
    else:
        reason = (
            f"The code kept failing: {run['error_summary']}"
            if run.get("error_summary")
            else "The verifier could not confirm a complete answer within the step limit."
        )
        prompt = FAILURE_PROMPT.format(prompt=state["user_prompt"], steps=steps, reason=reason)

    response = await llm.ainvoke(prompt)
    report = _strip_fences(response.content)

    (workspace_dir(task_id) / "report.md").write_text(report, encoding="utf-8")

    return {"report": report, "logs": ["reporter: wrote report.md"]}
