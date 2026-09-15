from backend.llm import get_llm
from backend.schemas import VerifierResult

PROMPT = """You are an expert data analyst.
Your task is to check whether the current plan and its code implementation is enough to
answer the question.

# Plan
{plan}

# Code
```python
{code}
```

# Execution result of code
{result}

# Question
{prompt}

# Your task
- Verify whether the current plan and its code implementation is enough to answer the
  question.
- If it is enough, answer SUFFICIENT. Otherwise, answer INSUFFICIENT.
"""


async def verifier_node(state: dict) -> dict:
    llm = get_llm("verifier").with_structured_output(VerifierResult)
    run = state.get("execution_result", {})
    plan = state.get("plan", [])

    result: VerifierResult = await llm.ainvoke(PROMPT.format(
        plan="\n".join(f"{s['step_id']}. {s['goal']}" for s in plan),
        code=state.get("code", ""),
        result=(run.get("stdout") or "")[-3000:],
        prompt=state["user_prompt"],
    ))

    return {
        "verifier_status": result.status,
        "logs": [f"verifier: {result.status}"],
    }
