import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.graph.graph import build_graph
from backend.workspace import create_workspace, add_input_file, list_workspace_files
from backend.docker_runner import get_or_create, destroy


async def run(prompt: str, files: list[str], keep_container: bool = True) -> dict:
    task_id = uuid.uuid4().hex[:8]
    print(f"task id: {task_id}\n")

    # Set up the folders, copy the data in, start the sandbox
    create_workspace(task_id)
    names = [add_input_file(task_id, f) for f in files]
    get_or_create(task_id)

    # The checkpointer saves progress, so a crash doesn't lose everything
    async with AsyncSqliteSaver.from_conn_string("storage/checkpoints.db") as saver:
        graph = build_graph(checkpointer=saver)

        final_state = await graph.ainvoke(
            {
                "task_id": task_id,
                "user_prompt": prompt,
                "input_files": names,
                "retry_count": 0,
                "status": "planning",
                "logs": [],
            },
            config={
                "configurable": {"thread_id": task_id},
                "recursion_limit": 60,   # safety net so it can never spin forever
            },
        )

    print("--- WHAT HAPPENED ---")
    for line in final_state.get("logs", []):
        print(" ", line)

    print("\n--- CHECKS ---")
    verdict = final_state.get("validation", {})
    print(f"  status: {verdict.get('status')}   score: {verdict.get('final_score')}")
    for issue in verdict.get("issues", []):
        print(f"  - {issue['message']}")

    print("\n--- REPORT ---")
    print(final_state.get("final_report", "(none)"))

    print("\n--- FILES ---")
    for f in list_workspace_files(task_id):
        print(" ", f)

    print(f"\nfolder: storage\\tasks\\{task_id}\\workspace")

    if not keep_container:
        destroy(task_id)

    return final_state


if __name__ == "__main__":
    user_prompt = sys.argv[1]
    input_files = sys.argv[2:]
    asyncio.run(run(user_prompt, input_files))