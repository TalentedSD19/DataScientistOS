from backend.config import MAX_REPAIR_ATTEMPTS


def manager_node(state: dict) -> dict:
    """Count the attempts and decide whether to keep trying."""
    status = state.get("status", "planning")

    if status == "repairing":
        attempts = state.get("retry_count", 0) + 1

        if attempts > MAX_REPAIR_ATTEMPTS:
            return {
                "retry_count": attempts,
                "status": "failed",
                "logs": [f"manager: giving up after {attempts} attempts"],
            }

        return {
            "retry_count": attempts,
            "status": "coding",
            "logs": [f"manager: repair attempt {attempts}"],
        }

    return {"logs": [f"manager: status is {status}"]}


def manager_router(state: dict) -> str:
    """Which node should run next after the manager."""
    status = state.get("status")

    if status in (None, "planning"):
        return "plan"
    if status == "coding":
        return "code"
    if status in ("reporting", "failed"):
        return "report"   # even a failure gets a report, so the user sees something
    return "code"