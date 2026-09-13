import asyncio
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.config import workspace_dir
from backend.workspace import create_workspace, list_workspace_files
from backend.docker_runner import get_or_create
from backend.graph.graph import build_graph

app = FastAPI(title="DataScientistOS")

# Lets the simple HTML page talk to this API from a different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Simple in-memory record of every task. Swap for a database later if you want.
TASKS: dict[str, dict] = {}


@app.post("/tasks")
async def create_task(prompt: str = Form(...),
                      files: list[UploadFile] = File(default=[])):
    """Start a new task. Returns straight away; the work happens in the background."""
    task_id = uuid.uuid4().hex[:8]
    ws = create_workspace(task_id)

    names = []
    for f in files:
        (ws / "input" / f.filename).write_bytes(await f.read())
        names.append(f.filename)

    TASKS[task_id] = {"status": "queued", "logs": [], "prompt": prompt}

    # Run it in the background so the request doesn't hang for 5 minutes
    asyncio.create_task(_run_in_background(task_id, prompt, names))

    return {"task_id": task_id, "status": "queued"}


async def _run_in_background(task_id: str, prompt: str, names: list[str]):
    TASKS[task_id]["status"] = "running"
    get_or_create(task_id)

    try:
        async with AsyncSqliteSaver.from_conn_string("storage/checkpoints.db") as saver:
            graph = build_graph(checkpointer=saver)

            # astream gives us updates as each agent finishes, so the UI can show progress
            async for event in graph.astream(
                {"task_id": task_id, "user_prompt": prompt, "input_files": names,
                 "retry_count": 0, "status": "planning", "logs": []},
                config={"configurable": {"thread_id": task_id},
                        "recursion_limit": 60},
            ):
                for node_name, update in event.items():
                    TASKS[task_id]["status"] = update.get("status", node_name)
                    TASKS[task_id]["logs"].extend(update.get("logs", []))
                    if update.get("validation"):
                        TASKS[task_id]["validation"] = update["validation"]
                    if update.get("final_report"):
                        TASKS[task_id]["report"] = update["final_report"]

    except Exception as e:
        TASKS[task_id]["status"] = "error"
        TASKS[task_id]["logs"].append(f"error: {e}")


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Current status, logs, report."""
    if task_id not in TASKS:
        raise HTTPException(404, "no such task")
    return TASKS[task_id]


@app.get("/tasks/{task_id}/logs")
def get_logs(task_id: str):
    return {"logs": TASKS.get(task_id, {}).get("logs", [])}


@app.get("/tasks/{task_id}/artifacts")
def get_artifacts(task_id: str):
    """List every file the task produced."""
    return {"files": list_workspace_files(task_id)}


@app.get("/tasks/{task_id}/artifacts/{path:path}")
def download_artifact(task_id: str, path: str):
    """Download one file."""
    file_path = workspace_dir(task_id) / path
    if not file_path.exists():
        raise HTTPException(404, "file not found")
    return FileResponse(file_path, filename=file_path.name)


@app.get("/tasks/{task_id}/result")
def get_result(task_id: str):
    """Everything in one call, for when the task is finished."""
    task = TASKS.get(task_id, {})
    return {
        "status": task.get("status"),
        "summary": task.get("report"),
        "validation": task.get("validation"),
        "artifacts": list_workspace_files(task_id),
    }