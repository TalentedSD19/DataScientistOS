import json

from backend.llm import get_llm
from backend.schemas import NextStep

PROMPT = """You are an expert data analyst.
In order to answer factoid questions based on the given data, you have to first plan effectively.

# Question
{prompt}

# Given data
{descriptions}

# Current plans
{plan}

# Obtained results from the current plans
{observation}

# Your task
- Suggest your next step to answer the question above.
- Your next step does not need to be sufficient to answer the question, but if it
  requires only one final simple step you may suggest it.
- If no steps have been taken yet, suggest a very simple first step that acts as a good
  starting point.
- Your response should only contain the next step.
"""


def _plan_text(plan: list[dict]) -> str:
    if not plan:
        return "(none yet)"
    return "\n".join(f"{s['step_id']}. {s['goal']}" for s in plan)


async def planner_node(state: dict) -> dict:
    llm = get_llm("planner").with_structured_output(NextStep)

    relevant = state.get("relevant_files") or state.get("input_files", [])
    descriptions = {f: state.get("data_descriptions", {}).get(f, "") for f in relevant}

    run = state.get("execution_result") or {}
    observation = (run.get("stdout") or "")[-1500:] or "(nothing has run yet)"

    next_step: NextStep = await llm.ainvoke(PROMPT.format(
        prompt=state["user_prompt"],
        descriptions=json.dumps(descriptions, indent=2)[:6000],
        plan=_plan_text(state.get("plan", [])),
        observation=observation,
    ))

    step_id = state.get("step_count", 0)
    plan = state.get("plan", []) + [{"step_id": step_id, "goal": next_step.goal}]

    return {
        "plan": plan,
        "step_count": step_id + 1,
        "debug_attempts": 0,
        "logs": [f"planner: step {step_id} - {next_step.goal}"],
    }
