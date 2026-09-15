import json

from backend.llm import get_llm
from backend.mcp_client import call

FIRST_STEP = """# Given data
{descriptions}

# Plan
{plan}

# Your task
- Implement the plan with the given data.
- Reply with a single Python code block only, no explanation.
- The script must run as `python src/main.py`. Input files are under input/.
- Print every result you compute, with a label, so it shows up in stdout.
"""

NEXT_STEP = """# Given data
{descriptions}

# Base code
```python
{code}
```

# Previous plans
{previous_plan}

# Current plan to implement
{step}

# Your task
- Implement the current plan with the given data.
- The implementation should be done based on the base code, which already implements the
  previous plans.
- If a previous step turns out to be wrong given the current plan, fix it here rather
  than building on top of it.
- Reply with the complete, updated src/main.py as a single Python code block, no explanation.
- Print every result you compute, with a label, so it shows up in stdout.
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("python"):
            text = text[len("python"):]
    return text.strip()


async def coder_node(state: dict) -> dict:
    task_id = state["task_id"]
    llm = get_llm("coder")

    plan = state.get("plan", [])
    relevant = state.get("relevant_files") or state.get("input_files", [])
    descriptions = {f: state.get("data_descriptions", {}).get(f, "") for f in relevant}

    if state.get("code"):
        message = NEXT_STEP.format(
            descriptions=json.dumps(descriptions, indent=2)[:6000],
            code=state["code"],
            previous_plan="\n".join(f"{s['step_id']}. {s['goal']}" for s in plan[:-1]),
            step=plan[-1]["goal"] if plan else state["user_prompt"],
        )
        mode = "extend"
    else:
        message = FIRST_STEP.format(
            descriptions=json.dumps(descriptions, indent=2)[:6000],
            plan="\n".join(f"{s['step_id']}. {s['goal']}" for s in plan) or state["user_prompt"],
        )
        mode = "first step"

    response = await llm.ainvoke(message)
    code = _strip_fences(response.content)

    await call("workspace", "write_file",
               task_id=task_id, path="src/main.py", content=code)

    return {"code": code, "logs": [f"coder: {mode}, {len(code)} characters"]}
