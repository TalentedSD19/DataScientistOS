from typing import Annotated, TypedDict
from operator import add


class TaskState(TypedDict, total=False):
    task_id: str
    user_prompt: str
    input_files: list[str]

    dataset_profiles: dict     # file name -> what inspect_dataset found
    spec: dict                 # the TaskSpec as a plain dict

    code: str                  # the current src/main.py
    execution_result: dict     # exit code, output, new files
    validation: dict           # filled in later, Phase 4

    generated_files: list[str]
    logs: Annotated[list[str], add]   # 'add' means new log lines get appended

    retry_count: int
    status: str
    final_report: str