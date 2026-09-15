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

# How many planning/verify/route rounds a single task can take (paper default: 20)
MAX_STEPS = int(os.getenv("MAX_STEPS", "20"))

# How many times the debugger can try to fix a crashing script before giving up
MAX_DEBUG_ATTEMPTS = int(os.getenv("MAX_DEBUG_ATTEMPTS", "3"))

# The paper's retriever only kicks in above 100 input files, and pulls the top 100
MANY_FILES_THRESHOLD = int(os.getenv("MANY_FILES_THRESHOLD", "100"))
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "100"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Limits for the sandbox container
CPU_LIMIT = float(os.getenv("CPU_LIMIT", "4"))
MEM_LIMIT = os.getenv("MEM_LIMIT", "6g")

# Internet is OFF inside the sandbox unless you turn it on
ALLOW_NETWORK = os.getenv("ALLOW_NETWORK", "false").lower() == "true"

# The single MCP server (mcp_servers/server.py) that exposes every tool the
# agents use: write_file and execute_file.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8011/mcp")


def task_dir(task_id: str) -> Path:
    """storage/tasks/<task_id>"""
    return STORAGE / task_id


def workspace_dir(task_id: str) -> Path:
    """storage/tasks/<task_id>/workspace  -- this folder becomes /workspace inside Docker"""
    return task_dir(task_id) / "workspace"