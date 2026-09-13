import asyncio
import json
import uuid

from backend.workspace import create_workspace, add_input_file
from backend.docker_runner import get_or_create, destroy
from backend.agents.planner import plan_node
from backend.agents.coder import code_node
from backend.agents.executor import execute_node
from backend.agents.validator import validate_node

PROMPT = (
    "Using input/data.csv, train a random forest to predict the Outcome column. "
    "Use 10-fold cross validation. "
    "Save the trained model as model.pkl, the per-fold accuracies as "
    "accuracy_results.csv, and a confusion matrix chart as confusion_matrix.png."
)


async def main():
    task_id = uuid.uuid4().hex[:8]
    create_workspace(task_id)
    name = add_input_file(task_id, "samples/data.csv")
    get_or_create(task_id)

    state = {"task_id": task_id, "user_prompt": PROMPT,
             "input_files": [name], "retry_count": 0,
             "status": "planning", "logs": []}

    state.update(await plan_node(state))
    state.update(await code_node(state))
    state.update(await execute_node(state))
    state.update(await validate_node(state))

    print("\n--- VERDICT ---")
    print(json.dumps(state["validation"], indent=2))

    # Now prove the validator actually fails when a file is missing
    print("\n--- SAME RUN, BUT ASKING FOR A FILE THAT DOESN'T EXIST ---")
    state["spec"]["required_outputs"].append("does_not_exist.csv")
    state["validation"] = None
    state.update(await validate_node(state))
    print("status:", state["validation"]["status"])
    print("repair note:\n", state["validation"]["repair_instruction"])

    destroy(task_id)


asyncio.run(main())