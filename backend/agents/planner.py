import json
import re

from backend.llm import get_llm
from backend.mcp_client import call
from backend.schemas import TaskSpec
from backend.config import workspace_dir

PLANNER_PROMPT = """You are a senior data scientist planning a task.

USER REQUEST:
{prompt}

WHAT THE DATA ACTUALLY LOOKS LIKE (never invent column names):
{profiles}

Produce a task specification.

Rules:
1. required_outputs must list EVERY file the request asks for, with the exact
   file name and folder. This is the most important field.
2. For each required output add a matching entry in requirements, picking the right
   kind (csv / image / model / text / file) and filling in expected columns or
   keywords whenever the request states them.
3. constraints must capture every hard number or rule, for example
   "10-fold cross validation", "epochs = 60", "try k from 2 to 10 and pick the
   best silhouette score".
4. subtasks: a short ordered list of 5 to 10 steps, each with one clear job.
5. Only use column names that appear in the data profile above.
"""

# Matches anything that looks like a file name in the prompt
FILE_PATTERN = re.compile(
    r"[\w./\\-]+\.(?:csv|xlsx|xls|json|txt|md|png|jpg|jpeg|pdf|pkl|joblib|h5|pt|pth)",
    re.IGNORECASE,
)


def _merge_outputs(found_by_llm: list[str], prompt: str, input_files: list[str]) -> list[str]:
    """Safety net: add any file name in the prompt that the model missed."""
    from_prompt = {m.group(0).strip("'\"`") for m in FILE_PATTERN.finditer(prompt)}
    # don't treat the input files as outputs
    from_prompt -= set(input_files)
    merged = list(found_by_llm) + sorted(from_prompt)
    return list(dict.fromkeys(merged))   # remove duplicates, keep order


async def plan_node(state: dict) -> dict:
    task_id = state["task_id"]

    # Step 1: look at every input file
    profiles = {}
    for file_name in state.get("input_files", []):
        raw = await call("workspace", "inspect_dataset",
                         task_id=task_id, path=f"input/{file_name}")
        profiles[file_name] = json.loads(raw) if isinstance(raw, str) else raw

    # Step 2: ask the model for a plan in a fixed shape
    llm = get_llm("planner").with_structured_output(TaskSpec)
    spec: TaskSpec = await llm.ainvoke(
        PLANNER_PROMPT.format(
            prompt=state["user_prompt"],
            profiles=json.dumps(profiles, indent=2)[:12000],
        )
    )

    # Step 3: the safety net
    spec.input_files = state.get("input_files", [])
    spec.required_outputs = _merge_outputs(
        spec.required_outputs, state["user_prompt"], spec.input_files
    )

    # Save the plan so you can read it yourself
    (workspace_dir(task_id) / "state" / "spec.json").write_text(
        spec.model_dump_json(indent=2), encoding="utf-8"
    )

    return {
        "dataset_profiles": profiles,
        "spec": spec.model_dump(),
        "status": "coding",
        "logs": [f"planner: {len(spec.required_outputs)} required outputs, "
                 f"{len(spec.constraints)} constraints"],
    }