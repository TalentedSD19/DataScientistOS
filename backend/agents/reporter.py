import json

from backend.llm import get_llm
from backend.mcp_client import call
from backend.config import workspace_dir

PROMPT = """Write a short, plain report for a data science task.

WHAT WAS ASKED FOR:
{prompt}

WHAT THE SCRIPT PRINTED:
{stdout}

FILES THAT WERE PRODUCED:
{manifest}

RESULT OF THE CHECKS:
{validation}

Write markdown with these four headings:
## What was done
## Results
## Files produced
## Anything to be careful about

Use only numbers that appear above. Never make a number up.
Keep it under 400 words.
"""


async def report_node(state: dict) -> dict:
    task_id = state["task_id"]

    # The manifest file was written by the validator
    manifest_path = workspace_dir(task_id) / "state" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    llm = get_llm("reporter")
    response = await llm.ainvoke(PROMPT.format(
        prompt=state["user_prompt"],
        stdout=(state.get("execution_result", {}).get("stdout") or "")[-4000:],
        manifest=json.dumps(manifest, indent=2)[:4000],
        validation=json.dumps(state.get("validation", {}), indent=2)[:2000],
    ))

    await call("workspace", "write_file",
               task_id=task_id, path="report.md", content=response.content)

    passed = state.get("validation", {}).get("status") == "PASS"

    return {
        "final_report": response.content,
        "status": "done" if passed else "failed",
        "logs": ["reporter: report.md written"],
    }