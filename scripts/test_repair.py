import asyncio
import uuid

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.graph.graph import build_graph
from backend.workspace import create_workspace, add_input_file
from backend.docker_runner import get_or_create, destroy
from backend.agents import coder

PROMPT = (
    "Using input/data.csv, train a random forest to predict Outcome. "
    "Save the model as model.pkl, the accuracies as accuracy_results.csv, "
    "and a confusion matrix chart as confusion_matrix.png."
)

# A first draft that deliberately forgets the chart
BROKEN_CODE = """
import pandas as pd, joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

df = pd.read_csv('input/data.csv')
X = df.drop(columns=['Outcome'])
y = df['Outcome']

model = RandomForestClassifier(random_state=42).fit(X, y)
joblib.dump(model, 'model.pkl')

scores = cross_val_score(model, X, y, cv=10)
pd.DataFrame({'fold': range(1, 11), 'accuracy': scores}).to_csv(
    'accuracy_results.csv', index=False)
print('mean accuracy:', scores.mean())
# note: no confusion_matrix.png -- the validator should catch this
"""

original_code_node = coder.code_node
first_call = {"done": False}


async def fake_code_node(state):
    """First time: write the broken code. After that: behave normally."""
    if not first_call["done"]:
        first_call["done"] = True
        from backend.mcp_client import call
        await call("workspace", "write_file", task_id=state["task_id"],
                   path="src/main.py", content=BROKEN_CODE)
        return {"code": BROKEN_CODE, "status": "executing",
                "logs": ["coder: BROKEN first draft (on purpose)"]}
    return await original_code_node(state)


coder.code_node = fake_code_node


async def main():
    # import after patching so the graph picks up the fake node
    import importlib
    from backend.graph import graph as graph_module
    importlib.reload(graph_module)

    task_id = uuid.uuid4().hex[:8]
    create_workspace(task_id)
    name = add_input_file(task_id, "samples/data.csv")
    get_or_create(task_id)

    async with AsyncSqliteSaver.from_conn_string("storage/checkpoints.db") as saver:
        g = graph_module.build_graph(checkpointer=saver)
        state = await g.ainvoke(
            {"task_id": task_id, "user_prompt": PROMPT, "input_files": [name],
             "retry_count": 0, "status": "planning", "logs": []},
            config={"configurable": {"thread_id": task_id}, "recursion_limit": 60},
        )

    for line in state["logs"]:
        print(" ", line)
    print("\nfinal:", state["validation"]["status"],
          "after", state["retry_count"], "repair(s)")

    destroy(task_id)


asyncio.run(main())