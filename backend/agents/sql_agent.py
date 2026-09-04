from __future__ import annotations

import time
from typing import Any

from backend.agents.common import (
    compact_json,
    create_step,
    new_id,
    structured_llm,
)
from backend.mcp.client import MCPToolClient, MCPToolError
from backend.db.models import (
    AgentOutput,
    Evidence,
    Finding,
    SQLAction,
)


SYSTEM_PROMPT = """
You are the SQL analyst for DataScientistOS.

Use the actual schema.
Write read-only SQL.
Execute the SQL through MCP.
Read the actual result before interpreting it.

Rules:
- Never invent table names.
- Never invent column names.
- Never invent query results.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or ATTACH.
- Keep the query focused on the question.
"""


async def run_sql_agent(
    question: str,
    dataset: str,
    profile: dict[str, Any],
    mcp: MCPToolClient | None = None,
) -> AgentOutput:

    if mcp is None:
        async with MCPToolClient() as client:
            return await _run_sql_agent(
                client,
                question,
                dataset,
                profile,
            )

    return await _run_sql_agent(
        mcp,
        question,
        dataset,
        profile,
    )


async def _run_sql_agent(
    mcp: MCPToolClient,
    question: str,
    dataset: str,
    profile: dict[str, Any],
) -> AgentOutput:

    findings: list[Finding] = []
    evidence: list[Evidence] = []
    tool_results: list[dict[str, Any]] = []
    steps = []
    errors = []

    schema_result = await mcp.call(
        "inspect_dataset",
        {
            "dataset": dataset,
        },
    )

    current_error: str | None = None

    # Initial attempt + maximum two repairs.
    for attempt in range(3):
        start = int(time.time() * 1000)

        model = structured_llm(SQLAction)

        prompt = f"""
{SYSTEM_PROMPT}

Question:
{question}

Dataset:
{dataset}

Schema/profile:
{compact_json(schema_result)}

Attempt:
{attempt + 1}

Previous error:
{current_error or "None"}

Generate one read-only SQL query.
"""

        try:
            action: SQLAction = await model.ainvoke(prompt)

            result = await mcp.call(
                "run_sql",
                {
                    "dataset": dataset,
                    "query": action.query,
                },
            )

            evidence_id = new_id("evidence")

            evidence.append(
                Evidence(
                    evidence_id=evidence_id,
                    kind="sql",
                    step_id="pending",
                    summary=action.purpose,
                )
            )

            tool_results.append(
                {
                    "tool": "run_sql",
                    "query": action.query,
                    "result": result,
                }
            )

            interpretation_prompt = f"""
You are interpreting a SQL result.

Question:
{question}

SQL:
{action.query}

Actual tool result:
{compact_json(result)}

Return ONE Finding.

Critical rule:
Every numeric value in `numbers` must be copied
exactly from the tool result.

Do not calculate new values.
Do not invent values.
Use association language rather than causation.
"""

            try:
                finding_model = structured_llm(Finding)

                finding: Finding = await finding_model.ainvoke(
                    interpretation_prompt
                )

            except Exception as exc:
                duration = (
                    int(time.time() * 1000) - start
                )

                step = create_step(
                    agent="sql_analyst",
                    action="generate_finding",
                    status="failed",
                    duration=duration,
                    message=str(exc),
                )

                steps.append(step)

                errors.append(
                    {
                        "type": "runtime",
                        "message": str(exc),
                        "phase": "finding_generation",
                    }
                )

                # SQL already succeeded, so DO NOT retry SQL.
                return AgentOutput(
                    findings=[],
                    evidence=evidence,
                    tool_results=tool_results,
                    steps=steps,
                    errors=errors,
                )

            finding.evidence_ids = [evidence_id]

            findings.append(finding)

            duration = (
                int(time.time() * 1000) - start
            )

            step = create_step(
                agent="sql_analyst",
                action="run_sql",
                status="success",
                duration=duration,
                message=f"SQL succeeded on attempt {attempt + 1}",
                evidence_ids=[evidence_id],
            )

            evidence[-1].step_id = step.step_id

            steps.append(step)

            return AgentOutput(
                findings=findings,
                evidence=evidence,
                tool_results=tool_results,
                steps=steps,
                errors=errors,
            )

        except MCPToolError as exc:
            current_error = str(exc)

            errors.append(
                {
                    "type": "schema"
                    if "column" in current_error.lower()
                    or "table" in current_error.lower()
                    else "runtime",
                    "message": current_error,
                    "attempt": attempt + 1,
                }
            )

            steps.append(
                create_step(
                    agent="sql_analyst",
                    action="run_sql",
                    status="failed",
                    duration=int(time.time() * 1000) - start,
                    message=current_error,
                )
            )

            if attempt == 2:
                break

        except Exception as exc:
            current_error = str(exc)

            errors.append(
                {
                    "type": "runtime",
                    "message": current_error,
                    "attempt": attempt + 1,
                }
            )

            steps.append(
                create_step(
                    agent="sql_analyst",
                    action="generate_sql",
                    status="failed",
                    duration=int(time.time() * 1000) - start,
                    message=current_error,
                )
            )

            if attempt == 2:
                break

    return AgentOutput(
        findings=findings,
        evidence=evidence,
        tool_results=tool_results,
        steps=steps,
        errors=errors,
    )