import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads the .env file

# Project root folder (one level above backend/)
ROOT = Path(__file__).resolve().parent.parent

# Every task gets its own folder under storage/tasks/
STORAGE = ROOT / "storage" / "tasks"
STORAGE.mkdir(parents=True, exist_ok=True)

RUNTIME_IMAGE = os.getenv("RUNTIME_IMAGE", "datasci-runtime:latest")
EXEC_TIMEOUT = int(os.getenv("EXEC_TIMEOUT_SECONDS", "600"))

# Limits for the sandbox container
CPU_LIMIT = float(os.getenv("CPU_LIMIT", "4"))
MEM_LIMIT = os.getenv("MEM_LIMIT", "6g")

# Internet is OFF inside the sandbox unless you turn it on
ALLOW_NETWORK = os.getenv("ALLOW_NETWORK", "false").lower() == "true"

# Addresses of the three tool servers
MCP_WORKSPACE_URL = os.getenv("MCP_WORKSPACE_URL", "http://127.0.0.1:8011/mcp")
MCP_EXEC_URL = os.getenv("MCP_EXEC_URL", "http://127.0.0.1:8012/mcp")
MCP_VALIDATE_URL = os.getenv("MCP_VALIDATE_URL", "http://127.0.0.1:8013/mcp")


def task_dir(task_id: str) -> Path:
    """storage/tasks/<task_id>"""
    return STORAGE / task_id


def workspace_dir(task_id: str) -> Path:
    """storage/tasks/<task_id>/workspace  -- this folder becomes /workspace inside Docker"""
    return task_dir(task_id) / "workspace"