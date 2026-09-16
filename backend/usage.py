import os
from datetime import datetime, timedelta

from langsmith import Client

PROJECT = os.getenv("LANGCHAIN_PROJECT", "DataScientistOS")


def _tracing_enabled() -> bool:
    return os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and bool(os.getenv("LANGCHAIN_API_KEY"))


def get_usage(task_id: str, started_at: datetime) -> dict:
    """Token usage and cost for one task, straight from LangSmith.

    LangGraph automatically tags each run's root trace with the thread_id we
    give it -- which is our task_id -- and LangSmith rolls total tokens and
    cost up onto that root run. So this is just: find that run, read it.
    """
    if not _tracing_enabled():
        return {"available": False}

    client = Client()
    root = next(
        (r for r in client.list_runs(
            project_name=PROJECT, is_root=True,
            start_time=started_at - timedelta(seconds=10),
            limit=20,
        ) if (r.extra or {}).get("metadata", {}).get("thread_id") == task_id),
        None,
    )

    if root is None:
        return {"available": True, "found": False}

    return {
        "available": True,
        "found": True,
        "total_tokens": root.total_tokens,
        "prompt_tokens": root.prompt_tokens,
        "completion_tokens": root.completion_tokens,
        "total_cost": float(root.total_cost) if root.total_cost is not None else None,
    }
