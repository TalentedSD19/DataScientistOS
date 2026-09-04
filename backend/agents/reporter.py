from __future__ import annotations

import time
from typing import Any

from backend.agents.common import (
    compact_json,
    create_step,
    structured_llm,
)
from backend.db.models import Report


SYSTEM_PROMPT = """
You are the report writer for DataScientistOS.

Use only verified findings and evidence.

Every number must come from verified tool output.
Do not invent missing information.
Do not claim code ran when it did not.
Do not convert association into causation.
Include important limitations.

Produce:
- summary
- question interpretation
- data used
- key findings
- evidence
- statistics/model result when relevant
- limitations
"""


async def run_reporter(
    question: str,
    plan: dict[str, Any],
    findings: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> tuple[Report, object]:

    start = int(time.time() * 1000)

    prompt = f"""
{SYSTEM_PROMPT}

Question:
{question}

Plan:
{compact_json(plan)}

Verified findings:
{compact_json(findings)}

Verified evidence:
{compact_json(evidence)}
"""

    model = structured_llm(Report)

    report: Report = await model.ainvoke(prompt)

    step = create_step(
        agent="reporter",
        action="write_report",
        status="success",
        duration=int(time.time() * 1000) - start,
        message="Report generated from verified findings",
    )

    return report, step