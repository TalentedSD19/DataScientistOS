from typing import Annotated, TypedDict
from operator import add


class DSStarState(TypedDict, total=False):
    task_id: str
    user_prompt: str
    input_files: list[str]

    data_descriptions: dict     # file name -> description text, from exec(analyzer script)
    relevant_files: list[str]   # which files the planner/coder/router should look at

    plan: list[dict]            # [{"step_id": int, "goal": str}, ...] taken so far
    step_count: int             # every step ever planned, even ones later backtracked past

    code: str                   # the current solution script, cumulative across steps
    execution_result: dict      # exit code, stdout/stderr, files created
    debug_attempts: int         # resets whenever the planner adds a new step

    verifier_status: str        # SUFFICIENT / INSUFFICIENT
    report: str                 # the reporter's final markdown summary

    logs: Annotated[list[str], add]
