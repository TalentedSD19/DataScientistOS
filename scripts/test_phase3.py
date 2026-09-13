import asyncio
import json
import uuid

from backend.workspace import create_workspace, add_input_file, list_workspace_files
from backend.docker_runner import get_or_create
from backend.agents.planner import plan_node
from backend.agents.coder import code_node
from backend.agents.executor import execute_node

PROMPT = (
    "Using input/data.csv, train a random forest to predict the Outcome column. "
    "Use 10-fold cross validation. "
    "Save the trained model as model.pkl, the per-fold accuracies as "
    "accuracy_results.csv, and a confusion matrix chart as confusion_matrix.png."
)


async def main():
    task_id = uuid.uuid4().hex[:8]
    print("task id:", task_id)

    create_workspace(task_id)
    name = add_input_file(task_id, "samples/data.csv")
    get_or_create(task_id)

    # We build up the state dict step by step, the way the graph will later
    state = {
        "task_id": task_id,
        "user_prompt": PROMPT,
        "input_files": [name],
        "retry_count": 0,
        "status": "planning",
        "logs": [],
    }

    state.update(await plan_node(state))
    print("\n--- PLAN ---")
    print("required outputs:", state["spec"]["required_outputs"])
    print("constraints:", state["spec"]["constraints"])

    state.update(await code_node(state))
    print("\n--- CODE (first 500 chars) ---")
    print(state["code"][:500])

    state.update(await execute_node(state))
    print("\n--- RUN ---")
    print("exit code:", state["execution_result"]["exit_code"])
    print(state["execution_result"]["stdout"][-1500:])
    if state["execution_result"]["exit_code"] != 0:
        print("ERROR:", state["execution_result"]["error_summary"])

    print("\n--- FILES IN WORKSPACE ---")
    for f in list_workspace_files(task_id):
        print(" ", f)

    print(f"\nOpen it: storage\\tasks\\{task_id}\\workspace")


asyncio.run(main())