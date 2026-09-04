from __future__ import annotations

import time
from typing import Any

from backend.agents.common import (
    compact_json,
    create_step,
    new_id,
    structured_llm,
)
from backend.mcp.client import MCPToolClient
from backend.db.models import (
    AgentOutput,
    EDAAction,
    Evidence,
    Finding,
)


SYSTEM_PROMPT = """
You are the exploratory-data analyst.

Use Python tools to investigate patterns relevant to the question.

Keep the analysis focused.

Useful operations:
- groupby + aggregate
- missing-value summary
- numeric summary
- correlation
- histogram
- bar chart
- time trend

Create a chart when it actually helps.

The code runs in a locked-down sandbox with no network access.
Only these packages are installed: pandas, numpy, scipy,
scikit-learn, matplotlib, duckdb, xgboost. Do not import anything
else (no seaborn, no plotly, no requests). Use matplotlib directly
for charts and save them to /workspace/output/<name>.png instead of
calling plt.show().

The dataset is not preloaded. The dataset's original SQLite file is
copied read-only into /workspace/input/<filename>. Read it with
Python's built-in sqlite3 module (e.g. sqlite3.connect("/workspace/
input/<filename>")) and pandas.read_sql_query, using the real table
and column names from the data profile below. Do not hand-type
sample values as a substitute for the real table.

Do not invent numbers.
Do not claim Python ran unless the tool confirms execution.

If you compute a correlation, coefficient, or any other purely
numeric quantity, restrict it to numeric columns only. Encode or
exclude categorical (text) columns first -- never pass a text
column into a numeric computation.
"""


async def run_eda_agent(
    question: str,
    dataset: str,
    profile: dict[str, Any],
    mcp: MCPToolClient | None = None,
) -> AgentOutput:

    if mcp is None:
        async with MCPToolClient() as client:
            return await _run_eda_agent(
                client,
                question,
                dataset,
                profile,
            )

    return await _run_eda_agent(
        mcp,
        question,
        dataset,
        profile,
    )


async def _run_eda_agent(
    mcp: MCPToolClient,
    question: str,
    dataset: str,
    profile: dict[str, Any],
) -> AgentOutput:

    steps: list[Any] = []
    errors: list[dict[str, Any]] = []
    current_error: str | None = None

    # Initial attempt + maximum two repairs.
    for attempt in range(3):
        start = int(time.time() * 1000)

        prompt = f"""
{SYSTEM_PROMPT}

Question:
{question}

Dataset:
{dataset}

Data profile:
{compact_json(profile)}

Attempt:
{attempt + 1}

Previous error:
{current_error or "None"}

Generate one focused Python analysis.

The code should:
1. inspect/use the provided dataset
2. perform one useful analysis
3. print compact useful results
4. create a chart only when useful
"""

        try:
            model = structured_llm(EDAAction)

            action: EDAAction = await model.ainvoke(prompt)

            code = action.code

            # Some structured-output responses emit literal backslash-n
            # instead of real newlines (single-line code with escape
            # sequences, no actual line breaks). Normalize only that
            # pathological case rather than every occurrence of "\n",
            # since real code may legitimately contain it inside strings.
            if "\n" not in code and "\\n" in code:
                code = code.encode(
                    "utf-8"
                ).decode("unicode_escape")

            result = await mcp.call(
                "run_python",
                {
                    "dataset": dataset,
                    "code": code,
                },
            )

            if not result.get("success", False):
                error_message = result.get(
                    "error",
                    "run_python reported failure.",
                )

                current_error = error_message

                steps.append(
                    create_step(
                        agent="eda_analyst",
                        action="run_python",
                        status="failed",
                        duration=int(time.time() * 1000) - start,
                        message=error_message,
                    )
                )

                errors.append(
                    {
                        "type": "runtime",
                        "message": error_message,
                        "attempt": attempt + 1,
                    }
                )

                if attempt == 2:
                    return AgentOutput(
                        tool_results=[
                            {
                                "tool": "run_python",
                                "code": code,
                                "result": result,
                            }
                        ],
                        steps=steps,
                        errors=errors,
                    )

                continue

            evidence_id = new_id("evidence")

            evidence_kind = (
                "chart"
                if result.get("artifacts")
                else "python"
            )

            evidence = Evidence(
                evidence_id=evidence_id,
                kind=evidence_kind,
                step_id="pending",
                summary=action.purpose,
                artifact_path=(
                    result.get("artifacts", [None])[0]
                    if result.get("artifacts")
                    else None
                ),
            )

            finding_prompt = f"""
Question:
{question}

Python analysis purpose:
{action.purpose}

Actual Python tool result:
{compact_json(result)}

Return a concise Finding.

All numbers must come directly from the actual tool output.
Do not calculate new values.
Do not invent results.
"""

            finding_model = structured_llm(Finding)

            finding: Finding = await finding_model.ainvoke(
                finding_prompt
            )

            finding.evidence_ids = [evidence_id]

            step = create_step(
                agent="eda_analyst",
                action="run_python",
                status="success",
                duration=int(time.time() * 1000) - start,
                message=f"EDA analysis completed on attempt {attempt + 1}",
                evidence_ids=[evidence_id],
            )

            evidence.step_id = step.step_id

            steps.append(step)

            return AgentOutput(
                findings=[finding],
                evidence=[evidence],
                tool_results=[
                    {
                        "tool": "run_python",
                        "code": action.code,
                        "result": result,
                    }
                ],
                steps=steps,
                errors=errors,
            )

        except Exception as exc:
            current_error = str(exc)

            steps.append(
                create_step(
                    agent="eda_analyst",
                    action="run_python",
                    status="failed",
                    duration=int(time.time() * 1000) - start,
                    message=current_error,
                )
            )

            errors.append(
                {
                    "type": "runtime",
                    "message": current_error,
                    "attempt": attempt + 1,
                }
            )

            if attempt == 2:
                return AgentOutput(
                    steps=steps,
                    errors=errors,
                )

    return AgentOutput(
        steps=steps,
        errors=errors,
    )
