import asyncio
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config import workspace_dir
from backend.workspace import create_workspace, list_workspace_files
from backend.runner import run as run_task

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


def _record_update(task_id: str, node_name: str, update: dict) -> None:
    """Mirror one graph step into the TASKS dict so /tasks/{id} has live status."""
    TASKS[task_id]["status"] = node_name
    TASKS[task_id]["logs"].extend(update.get("logs", []))
    for key in ("plan", "code", "execution_result", "verifier_status"):
        if update.get(key):
            TASKS[task_id][key] = update[key]


async def _run_in_background(task_id: str, prompt: str, names: list[str]):
    TASKS[task_id]["status"] = "running"
    try:
        await run_task(
            task_id, prompt, names,
            on_update=lambda node_name, update: _record_update(task_id, node_name, update),
        )
        TASKS[task_id]["status"] = "done"
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
    """Everything in one call: the final code, its output, and the plan that led there."""
    task = TASKS.get(task_id, {})
    run = task.get("execution_result", {})
    return {
        "status": task.get("status"),
        "verifier_status": task.get("verifier_status"),
        "plan": task.get("plan"),
        "code": task.get("code"),
        "answer": run.get("stdout"),
        "artifacts": list_workspace_files(task_id),
    }
