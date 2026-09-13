from langgraph.graph import StateGraph, START, END

from backend.graph.state import TaskState
from backend.agents.manager import manager_node, manager_router
from backend.agents.planner import plan_node
from backend.agents.coder import code_node
from backend.agents.executor import execute_node
from backend.agents.validator import validate_node
from backend.agents.reporter import report_node
from backend.config import MAX_REPAIR_ATTEMPTS


def validator_router(state: dict) -> str:
    """After checking: finish, try again, or stop trying."""
    verdict = state.get("validation", {})

    if verdict.get("status") == "PASS":
        return "pass"
    if state.get("retry_count", 0) >= MAX_REPAIR_ATTEMPTS:
        return "abort"
    return "repair"


def build_graph(checkpointer=None):
    graph = StateGraph(TaskState)

    # Every agent is a node
    graph.add_node("manager", manager_node)
    graph.add_node("planner", plan_node)
    graph.add_node("coder", code_node)
    graph.add_node("executor", execute_node)
    graph.add_node("validator", validate_node)
    graph.add_node("reporter", report_node)

    # Start at the manager
    graph.add_edge(START, "manager")

    # The manager picks where to go
    graph.add_conditional_edges("manager", manager_router, {
        "plan": "planner",
        "code": "coder",
        "report": "reporter",
    })

    # Planning always returns to the manager
    graph.add_edge("planner", "manager")

    # Code is always run, and a run is always checked
    graph.add_edge("coder", "executor")
    graph.add_edge("executor", "validator")

    # This is the repair loop
    graph.add_conditional_edges("validator", validator_router, {
        "pass": "reporter",
        "repair": "manager",   # manager bumps the counter, sends it back to coder
        "abort": "reporter",
    })

    graph.add_edge("reporter", END)

    return graph.compile(checkpointer=checkpointer)