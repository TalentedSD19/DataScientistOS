import uuid

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.graph.graph import build_graph
from backend.docker_runner import get_or_create, destroy
from backend.workspace import save_state
from backend.config import ROOT, MAX_STEPS, MAX_DEBUG_ATTEMPTS

CHECKPOINTS_DB = str(ROOT / "storage" / "checkpoints.db")

# A planning round is planner+coder+executor+verifier+router (5 nodes), plus up
# to MAX_DEBUG_ATTEMPTS debugger+executor retries if the script crashes. Without
# this, a run that genuinely needs its full MAX_STEPS budget can hit LangGraph's
# recursion_limit and crash before after_verifier's own step_count >= MAX_STEPS
# check ever gets a chance to stop it gracefully.
RECURSION_LIMIT = MAX_STEPS * (5 + 2 * MAX_DEBUG_ATTEMPTS)


async def run(task_id: str, prompt: str, input_files: list[str], on_update=None) -> dict:
    """Run the DS-STAR agent loop for one task and return the final graph state.

    Expects the task's workspace to already exist with input_files sitting in its
    input/ folder (see backend.workspace.create_workspace / add_input_file).

    Prints every step as it happens -- analyzing files, planning, coding,
    executing, debugging, verifying, routing -- since watching the agent work
    step by step is the whole point of DS-STAR's iterative loop. If on_update
    is given, it is also called as (node_name, state_update) after each node,
    so callers like the API can keep a live status for the task.
    """
    print(f"\n=== DataScientistOS task {task_id} ===")
    print(f"query: {prompt}")
    print(f"input files: {', '.join(input_files) or '(none)'}\n")

    if on_update:
        on_update("sandbox", {"logs": ["sandbox: spinning up the sandbox container"]})
    print("  [sandbox] spinning up the sandbox container")
    get_or_create(task_id)  # make sure the task's sandbox container is up

    state: dict = {
        "task_id": task_id, "user_prompt": prompt, "input_files": input_files,
        "step_count": 0, "debug_attempts": 0, "logs": [],
    }

    try:
        async with AsyncSqliteSaver.from_conn_string(CHECKPOINTS_DB) as saver:
            graph = build_graph(checkpointer=saver)

            # astream yields one {node_name: partial_update} dict per finished node,
            # which lets us print progress live instead of waiting for the whole run.
            async for event in graph.astream(
                state,
                config={"configurable": {"thread_id": task_id}, "recursion_limit": RECURSION_LIMIT},
            ):
                for node_name, update in event.items():
                    for line in update.get("logs", []):
                        print(f"  [{node_name}] {line}")

                    merged_logs = state.get("logs", []) + update.get("logs", [])
                    state = {**state, **update, "logs": merged_logs}

                    if on_update:
                        on_update(node_name, update)
    finally:
        # The sandbox is single-use per task: once this loop is done -- whether
        # it finished cleanly or blew up -- there's nothing left to run in it,
        # so it must never be left behind as an orphaned container.
        save_state(task_id, state)
        destroy(task_id)
        print(f"  sandbox container removed")

    print(f"\n=== task {task_id} finished: verifier={state.get('verifier_status', 'unknown')} ===")
    print(f"workspace: storage/tasks/{task_id}/workspace\n")
    return state


async def run_new_task(prompt: str, source_files: list[str], task_id: str | None = None) -> dict:
    """Convenience entry point for the CLI: create a fresh workspace, copy the
    given source files into it, then run the task. Used by scripts/run_task.py."""
    from backend.workspace import create_workspace, add_input_file

    task_id = task_id or uuid.uuid4().hex[:8]
    create_workspace(task_id)
    names = [add_input_file(task_id, f) for f in source_files]
    return await run(task_id, prompt, names)
