from __future__ import annotations

import time
from typing import Any

from backend.agents.common import create_step, structured_llm
from backend.db.models import Plan


SYSTEM_PROMPT = """
You are the manager of a data-analysis workflow.

Understand the user's data-science question.
Determine the analysis type.
Identify the likely target if one exists.
Choose the specialist agents that should work on the problem.

Allowed analysis types:
- descriptive
- diagnostic
- predictive
- insufficient_data

Possible specialists:
- sql_analyst
- eda_analyst
- stats_ml

Rules:
- Do not calculate statistics.
- Do not invent data values.
- Do not claim results.
- Create a short, practical plan.
"""


async def run_manager(
    question: str,
    available_datasets: list[dict[str, Any]],
) -> tuple[Plan, object]:
    start = int(time.time() * 1000)

    prompt = f"""
{SYSTEM_PROMPT}

User question:
{question}

Available datasets:
{available_datasets}

Return a concise structured plan.
"""

    model = structured_llm(Plan)

    plan: Plan = await model.ainvoke(prompt)

    step = create_step(
        agent="manager",
        action="create_plan",
        status="success",
        duration=int(time.time() * 1000) - start,
        message=(
            f"Selected analysis type: "
            f"{plan.analysis_type}"
        ),
    )

    return plan, step