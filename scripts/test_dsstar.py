import asyncio
import uuid

from backend.workspace import create_workspace, add_input_file, list_workspace_files
from backend.docker_runner import get_or_create
from backend.agents.analyzer import analyzer_node
from backend.agents.retriever import retriever_node
from backend.agents.planner import planner_node
from backend.agents.coder import coder_node
from backend.agents.executor import execute_node
from backend.agents.verifier import verifier_node

PROMPT = (
    "Using input/data.csv, train a random forest to predict the Outcome column. "
    "Save the trained model as model.pkl, the per-fold accuracies as "
    "accuracy_results.csv, and a confusion matrix chart as confusion_matrix.png."
)


async def main():
    task_id = uuid.uuid4().hex[:8]
    print("task id:", task_id)

    create_workspace(task_id)
    name = add_input_file(task_id, "samples/data.csv")
    get_or_create(task_id)

    state = {
        "task_id": task_id,
        "user_prompt": PROMPT,
        "input_files": [name],
        "step_count": 0,
        "debug_attempts": 0,
        "logs": [],
    }

    state.update(await analyzer_node(state))
    print("\n--- DATA DESCRIPTIONS ---")
    print(state["data_descriptions"])

    state.update(await retriever_node(state))

    # One planner -> coder -> executor -> verifier cycle
    state.update(await planner_node(state))
    print("\n--- STEP 0 ---")
    print(state["plan"][-1]["goal"])

    state.update(await coder_node(state))
    print("\n--- CODE (first 500 chars) ---")
    print(state["code"][:500])

    state.update(await execute_node(state))
    print("\n--- RUN ---")
    print("exit code:", state["execution_result"]["exit_code"])
    print(state["execution_result"]["stdout"][-1500:])

    if state["execution_result"]["exit_code"] == 0:
        state.update(await verifier_node(state))
        print("\n--- VERIFIER ---")
        print(state["verifier_status"])

    print("\n--- FILES IN WORKSPACE ---")
    for f in list_workspace_files(task_id):
        print(" ", f)

    print(f"\nOpen it: storage\\tasks\\{task_id}\\workspace")


asyncio.run(main())
