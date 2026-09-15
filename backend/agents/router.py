import json

from backend.llm import get_llm
from backend.schemas import RouterDecision

PROMPT = """You are an expert data analyst.
Since the current plan is insufficient to answer the question, your task is to decide
how to refine the plan.

# Question
{prompt}

# Given data
{descriptions}

# Current plans
{plan}

# Obtained results from the current plans
{observation}

# Your task
- If you think one of the steps in the current plan is wrong, choose BACKTRACK and give
  its step_id; that step and everything after it will be redone.
- If you think the plan is correct but incomplete, choose ADD_STEP.
"""


async def router_node(state: dict) -> dict:
    llm = get_llm("router").with_structured_output(RouterDecision)
    plan = state.get("plan", [])
    run = state.get("execution_result") or {}

    relevant = state.get("relevant_files") or state.get("input_files", [])
    descriptions = {f: state.get("data_descriptions", {}).get(f, "") for f in relevant}

    decision: RouterDecision = await llm.ainvoke(PROMPT.format(
        prompt=state["user_prompt"],
        descriptions=json.dumps(descriptions, indent=2)[:6000],
        plan="\n".join(f"{s['step_id']}. {s['goal']}" for s in plan),
        observation=(run.get("stdout") or "")[-1500:] or "(nothing has run yet)",
    ))

    if decision.action == "BACKTRACK" and decision.backtrack_to is not None:
        kept = [s for s in plan if s["step_id"] < decision.backtrack_to]
        return {
            "plan": kept,
            "logs": [f"router: backtrack to step {decision.backtrack_to}"],
        }

    return {"logs": ["router: add step"]}
