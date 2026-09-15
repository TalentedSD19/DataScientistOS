import json
import re
from pathlib import Path

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
6. For a "text" requirement, numeric_only and required_keywords are mutually
   exclusive: numeric_only means the ENTIRE file must be just one number, so
   never set numeric_only=true on a requirement that also has required_keywords.
   Use numeric_only only when the request asks for a single bare number in the
   file; use required_keywords when the file is a short written answer/summary.
7. Only set expected_rows on a csv requirement when the request states an exact
   row count in words (e.g. "keep exactly 500 rows"). Do not guess a row count
   from the input data size — the correct row count after cleaning/filtering is
   often unknowable in advance, and a wrong guess fails a script that behaved
   correctly.
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
    input_basenames = {Path(f).name.lower() for f in input_files}
    from_prompt = {f for f in from_prompt if Path(f).name.lower() not in input_basenames}
    merged = list(found_by_llm) + sorted(from_prompt)
    return list(dict.fromkeys(merged))   # remove duplicates, keep order


def _fix_contradictory_requirements(requirements: list) -> None:
    """Belt-and-braces for rule 6 above: a text requirement can't be both
    'just one number' and 'must contain these words'. If the model set both
    anyway, keyword content wins since it's the more specific instruction --
    otherwise validate_text can never pass no matter what the coder writes."""
    for req in requirements:
        if req.kind == "text" and req.numeric_only and req.required_keywords:
            req.numeric_only = False


def _trim_profiles(profiles: dict, max_cols: int = 15) -> dict:
    """Shrink a dataset profile before a retry. A very wide spreadsheet makes
    the model restate dozens of columns across column_names/dtypes/missing/
    unique/head, which is what pushes structured-output generation past the
    completion-token cap in the first place."""
    trimmed = {}
    for file_name, profile in profiles.items():
        if not isinstance(profile, dict):
            trimmed[file_name] = profile
            continue
        p = dict(profile)
        cols = p.get("column_names")
        if isinstance(cols, list) and len(cols) > max_cols:
            keep = set(cols[:max_cols])
            p["column_names"] = cols[:max_cols]
            p["note"] = f"{len(cols)} columns total, showing first {max_cols} only"
            for key in ("dtypes", "missing", "unique"):
                if isinstance(p.get(key), dict):
                    p[key] = {c: v for c, v in p[key].items() if c in keep}
            if isinstance(p.get("head"), list):
                p["head"] = [
                    {c: v for c, v in row.items() if c in keep}
                    for row in p["head"]
                ]
            p.pop("describe", None)
        trimmed[file_name] = p
    return trimmed


async def plan_node(state: dict) -> dict:
    task_id = state["task_id"]

    # Step 1: look at every input file
    profiles = {}
    for file_name in state.get("input_files", []):
        raw = await call("workspace", "inspect_dataset",
                         task_id=task_id, path=f"input/{file_name}")
        profiles[file_name] = json.loads(raw) if isinstance(raw, str) else raw

    # Step 2: ask the model for a plan in a fixed shape.
    # max_tokens is capped well below the API's hard limit so a run that's
    # about to blow the budget (e.g. a very wide spreadsheet making the model
    # restate dozens of columns) fails fast into the except-branch instead of
    # burning ~16k tokens and returning no spec at all.
    llm = get_llm("planner", max_tokens=4096).with_structured_output(TaskSpec)
    try:
        spec: TaskSpec = await llm.ainvoke(
            PLANNER_PROMPT.format(
                prompt=state["user_prompt"],
                profiles=json.dumps(profiles, indent=2)[:12000],
            )
        )
    except Exception:
        # Retry once with a drastically trimmed profile. This is what
        # actually causes the runaway generation on wide datasets, so
        # shrinking it is more reliable than just asking again.
        trimmed = _trim_profiles(profiles)
        spec = await llm.ainvoke(
            PLANNER_PROMPT.format(
                prompt=state["user_prompt"],
                profiles=json.dumps(trimmed, indent=2)[:4000],
            )
        )

    # Step 3: the safety net
    spec.input_files = state.get("input_files", [])
    spec.required_outputs = _merge_outputs(
        spec.required_outputs, state["user_prompt"], spec.input_files
    )
    _fix_contradictory_requirements(spec.requirements)

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