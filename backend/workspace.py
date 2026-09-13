import shutil
from pathlib import Path

from backend.config import workspace_dir

# The fixed folder layout every task gets
SUBDIRS = ["input", "src", "outputs", "figures", "models", "logs", "state"]


def create_workspace(task_id: str) -> Path:
    """Make the empty folder structure for a new task."""
    ws = workspace_dir(task_id)
    for name in SUBDIRS:
        (ws / name).mkdir(parents=True, exist_ok=True)
    return ws


def add_input_file(task_id: str, source_path: str) -> str:
    """Copy one of the user's files into the task's input/ folder.
    Returns just the file name, e.g. 'data.csv'."""
    ws = workspace_dir(task_id)
    file_name = Path(source_path).name
    shutil.copy(source_path, ws / "input" / file_name)
    return file_name


def list_workspace_files(task_id: str) -> list[str]:
    """Every file in the workspace, as paths relative to the workspace folder."""
    ws = workspace_dir(task_id)
    return sorted(str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file())