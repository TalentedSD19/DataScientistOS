import uuid

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.graph.graph import build_graph
from backend.workspace import create_workspace, add_input_file
from backend.docker_runner import get_or_create


async def run(prompt: str, files: list[str], task_id: str | None = None) -> dict:
    """Run one task. Returns the final graph state."""
    task_id = task_id or uuid.uuid4().hex[:8]
    create_workspace(task_id)
    names = [add_input_file(task_id, f) for f in files]
    get_or_create(task_id)

    async with AsyncSqliteSaver.from_conn_string("storage/checkpoints.db") as saver:
        graph = build_graph(checkpointer=saver)
        state = await graph.ainvoke(
            {"task_id": task_id, "user_prompt": prompt, "input_files": names,
             "step_count": 0, "debug_attempts": 0, "logs": []},
            config={"configurable": {"thread_id": task_id}, "recursion_limit": 80},
        )
    return state