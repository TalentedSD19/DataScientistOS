"""CLI entry point: run one DS-STAR task from the command line.

Usage:
    python scripts/run_task.py "your question about the data" input/data.csv [more files...]

All progress is printed live by backend.runner.run as the agent works.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.runner import run_new_task

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/run_task.py \"<prompt>\" [file ...]")
        sys.exit(1)

    prompt = sys.argv[1]
    files = sys.argv[2:]
    asyncio.run(run_new_task(prompt, files))
