from langgraph.graph import StateGraph, START, END

from backend.graph.state import DSStarState
from backend.agents.analyzer import analyzer_node
from backend.agents.retriever import retriever_node
from backend.agents.planner import planner_node
from backend.agents.coder import coder_node
from backend.agents.executor import execute_node
from backend.agents.debugger import debugger_node
from backend.agents.verifier import verifier_node
from backend.agents.router import router_node
from backend.config import MAX_DEBUG_ATTEMPTS, MAX_STEPS


def after_execution(state: dict) -> str:
    """Did the script run? A crash goes to the debugger, not the verifier -- a runtime
    error is a coding mistake, not a sign the plan is wrong."""
    run = state.get("execution_result", {})
    if run.get("exit_code") == 0:
        return "ok"
    if state.get("debug_attempts", 0) < MAX_DEBUG_ATTEMPTS:
        return "debug"
    return "give_up"


def after_verifier(state: dict) -> str:
    """Finished (or out of rounds), or does the plan need another step / a backtrack?"""
    if state.get("verifier_status") == "SUFFICIENT":
        return "done"
    if state.get("step_count", 0) >= MAX_STEPS:
        return "done"
    return "insufficient"


def build_graph(checkpointer=None):
    graph = StateGraph(DSStarState)

    graph.add_node("analyzer", analyzer_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("executor", execute_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("router", router_node)

    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "retriever")
    graph.add_edge("retriever", "planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "executor")

    graph.add_conditional_edges("executor", after_execution, {
        "ok": "verifier",
        "debug": "debugger",
        "give_up": END,
    })
    graph.add_edge("debugger", "executor")

    graph.add_conditional_edges("verifier", after_verifier, {
        "done": END,
        "insufficient": "router",
    })
    graph.add_edge("router", "planner")

    return graph.compile(checkpointer=checkpointer)
