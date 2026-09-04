from __future__ import annotations

import time
from typing import Any

from backend.agents.common import compact_json, create_step, structured_llm
from backend.db.models import Critique


SYSTEM_PROMPT = """
You are the critic for a data-science workflow.

Try to find reasons the proposed answer could be wrong.

Check:
- dataset selection
- schema usage
- joins
- SQL aggregation
- statistical method
- statistical interpretation
- ML leakage
- baseline comparison
- unsupported numbers
- unsupported claims
- limitations

Important:
Correlation or association must not be presented as causation.

Return:
- accept
- revise
- reject

Use revise when the work can realistically be repaired.
Use reject when the requested conclusion cannot be supported.
"""


async def run_critic(
    question: str,
    plan: dict[str, Any],
    findings: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> tuple[Critique, object]:

    start = int(time.time() * 1000)

    prompt = f"""
{SYSTEM_PROMPT}

Question:
{question}

Plan:
{compact_json(plan)}

Findings:
{compact_json(findings)}

Evidence:
{compact_json(evidence)}

Errors:
{compact_json(errors)}
"""

    model = structured_llm(Critique)

    critique: Critique = await model.ainvoke(prompt)

    step = create_step(
        agent="critic",
        action="critique_analysis",
        status="success",
        duration=int(time.time() * 1000) - start,
        message=(
            f"Critic verdict: {critique.verdict}"
        ),
    )

    return critique, step