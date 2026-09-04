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
    Evidence,
    Finding,
    MLAction,
    StatisticsAction,
)


STATS_PROMPT = """
You are the statistics and machine-learning analyst.

Choose an appropriate statistical test or predictive approach.

Supported statistical operations:
- chi_square
- t_test
- pearson
- spearman

Rules:
- Use the actual dataset schema.
- Do not invent values.
- Use statistical tests only when appropriate.
- Do not interpret correlation as causation.
- Write one read-only SQL query that returns the raw rows the test
  needs. The values used by the test come from the query's actual
  result, never from your own estimate.

SQL query shape required per operation (exactly two columns, in
this order, aliased however you like):
- chi_square: one row per record, column 1 = first categorical
  variable, column 2 = second categorical variable. A contingency
  table is built from the raw rows.
- t_test: column 1 = the grouping column (must contain exactly two
  distinct values across the returned rows), column 2 = the numeric
  value being compared.
- pearson / spearman: column 1 = numeric x, column 2 = numeric y.

For ML:
1. validate the target
2. choose sensible features
3. establish a baseline
4. train the candidate model
5. compare against the baseline
6. inspect leakage warnings
"""


def _build_chi_square_spec(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(columns) < 2:
        raise ValueError(
            "chi_square query must return two columns."
        )

    col_a, col_b = columns[0], columns[1]

    a_values = sorted(
        {row[col_a] for row in rows},
        key=str,
    )
    b_values = sorted(
        {row[col_b] for row in rows},
        key=str,
    )

    a_index = {
        value: index
        for index, value in enumerate(a_values)
    }
    b_index = {
        value: index
        for index, value in enumerate(b_values)
    }

    table = [
        [0] * len(b_values)
        for _ in a_values
    ]

    for row in rows:
        table[a_index[row[col_a]]][
            b_index[row[col_b]]
        ] += 1

    return {"observed": table}


def _build_t_test_spec(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(columns) < 2:
        raise ValueError(
            "t_test query must return a group column "
            "and a numeric value column."
        )

    group_col, value_col = columns[0], columns[1]

    groups: dict[Any, list[float]] = {}

    for row in rows:
        groups.setdefault(
            row[group_col],
            [],
        ).append(row[value_col])

    if len(groups) != 2:
        raise ValueError(
            f"t_test requires exactly two distinct groups "
            f"in '{group_col}', found {len(groups)}."
        )

    group_a, group_b = groups.values()

    return {
        "group_a": group_a,
        "group_b": group_b,
    }


def _build_correlation_spec(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(columns) < 2:
        raise ValueError(
            "correlation query must return two numeric columns."
        )

    x_col, y_col = columns[0], columns[1]

    return {
        "x": [row[x_col] for row in rows],
        "y": [row[y_col] for row in rows],
    }


def _build_statistics_data_spec(
    operation: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if operation == "chi_square":
        return _build_chi_square_spec(columns, rows)

    if operation == "t_test":
        return _build_t_test_spec(columns, rows)

    if operation in ("pearson", "spearman"):
        return _build_correlation_spec(columns, rows)

    raise ValueError(
        f"Unsupported statistical operation: {operation}"
    )


async def run_stats_ml_agent(
    question: str,
    dataset: str,
    profile: dict[str, Any],
    analysis_type: str,
    target: str | None,
    mcp: MCPToolClient | None = None,
) -> AgentOutput:

    if mcp is None:
        async with MCPToolClient() as client:
            return await _run_stats_ml_agent(
                client,
                question,
                dataset,
                profile,
                analysis_type,
                target,
            )

    return await _run_stats_ml_agent(
        mcp,
        question,
        dataset,
        profile,
        analysis_type,
        target,
    )


async def _run_stats_ml_agent(
    mcp: MCPToolClient,
    question: str,
    dataset: str,
    profile: dict[str, Any],
    analysis_type: str,
    target: str | None,
) -> AgentOutput:

    if analysis_type == "predictive" and target:
        return await _run_ml(
            mcp,
            question,
            dataset,
            profile,
            target,
        )

    return await _run_statistics(
        mcp,
        question,
        dataset,
        profile,
    )


async def _run_statistics(
    mcp: MCPToolClient,
    question: str,
    dataset: str,
    profile: dict[str, Any],
) -> AgentOutput:

    start = int(time.time() * 1000)

    prompt = f"""
{STATS_PROMPT}

Question:
{question}

Dataset:
{dataset}

Profile:
{compact_json(profile)}

Choose one appropriate statistical operation and write the SQL
query that returns the raw rows it needs, per the shape rules
above.
"""

    model = structured_llm(StatisticsAction)

    action: StatisticsAction = await model.ainvoke(prompt)

    sql_result: dict[str, Any] | None = None

    try:
        sql_result = await mcp.call(
            "run_sql",
            {
                "dataset": dataset,
                "query": action.sql_query,
            },
        )

        if not sql_result.get("success", False):
            raise ValueError(
                sql_result.get(
                    "error",
                    "run_sql reported failure.",
                )
            )

        data_spec = _build_statistics_data_spec(
            action.operation,
            sql_result["columns"],
            sql_result["rows"],
        )

    except Exception as exc:
        step = create_step(
            agent="stats_ml",
            action="run_sql",
            status="failed",
            duration=int(time.time() * 1000) - start,
            message=str(exc),
        )

        return AgentOutput(
            tool_results=[
                {
                    "tool": "run_sql",
                    "query": action.sql_query,
                    "result": sql_result,
                }
            ],
            steps=[step],
            errors=[
                {
                    "type": "runtime",
                    "message": str(exc),
                }
            ],
        )

    result = await mcp.call(
        "run_statistics",
        {
            "test": action.operation,
            "data": data_spec,
        },
    )

    if not result.get("success", False):
        error_message = result.get(
            "error",
            "run_statistics reported failure.",
        )

        step = create_step(
            agent="stats_ml",
            action="run_statistics",
            status="failed",
            duration=int(time.time() * 1000) - start,
            message=error_message,
        )

        return AgentOutput(
            tool_results=[
                {
                    "tool": "run_sql",
                    "query": action.sql_query,
                    "result": sql_result,
                },
                {
                    "tool": "run_statistics",
                    "operation": action.operation,
                    "data": data_spec,
                    "result": result,
                },
            ],
            steps=[step],
            errors=[
                {
                    "type": "runtime",
                    "message": error_message,
                }
            ],
        )

    evidence_id = new_id("evidence")

    evidence = Evidence(
        evidence_id=evidence_id,
        kind="stat_test",
        step_id="pending",
        summary=action.purpose,
    )

    finding_prompt = f"""
Question:
{question}

Statistical operation:
{action.operation}

Actual result:
{compact_json(result)}

Return one Finding.

Numbers must come exactly from the tool result.
Do not invent or calculate additional numbers.

Do not imply causation.
"""

    finding_model = structured_llm(Finding)

    finding: Finding = await finding_model.ainvoke(
        finding_prompt
    )

    finding.evidence_ids = [evidence_id]

    step = create_step(
        agent="stats_ml",
        action="run_statistics",
        status="success",
        duration=int(time.time() * 1000) - start,
        message=f"Ran {action.operation}",
        evidence_ids=[evidence_id],
    )

    evidence.step_id = step.step_id

    return AgentOutput(
        findings=[finding],
        evidence=[evidence],
        tool_results=[
            {
                "tool": "run_sql",
                "query": action.sql_query,
                "result": sql_result,
            },
            {
                "tool": "run_statistics",
                "operation": action.operation,
                "data": data_spec,
                "result": result,
            },
        ],
        steps=[step],
    )


async def _run_ml(
    mcp: MCPToolClient,
    question: str,
    dataset: str,
    profile: dict[str, Any],
    target: str,
) -> AgentOutput:

    start = int(time.time() * 1000)

    prompt = f"""
{STATS_PROMPT}

Question:
{question}

Dataset:
{dataset}

Profile:
{compact_json(profile)}

Target:
{target}

Choose features that are available in the schema.

Prefer logistic_regression first.
Choose random_forest or xgboost only when appropriate.

Do not include the target itself as a feature.
Watch for obvious leakage.
"""

    model = structured_llm(MLAction)

    action: MLAction = await model.ainvoke(prompt)

    result = await mcp.call(
        "train_model",
        {
            "dataset": dataset,
            "target": action.target,
            "features": action.features,
            "model_type": action.model_type,
        },
    )

    if not result.get("success", False):
        error_message = result.get(
            "error",
            "train_model reported failure.",
        )

        step = create_step(
            agent="stats_ml",
            action="train_model",
            status="failed",
            duration=int(time.time() * 1000) - start,
            message=error_message,
        )

        return AgentOutput(
            tool_results=[
                {
                    "tool": "train_model",
                    "model": action.model_type,
                    "result": result,
                }
            ],
            steps=[step],
            errors=[
                {
                    "type": "runtime",
                    "message": error_message,
                }
            ],
        )

    evidence_id = new_id("evidence")

    evidence = Evidence(
        evidence_id=evidence_id,
        kind="model",
        step_id="pending",
        summary=action.purpose,
    )

    finding_prompt = f"""
Question:
{question}

Model:
{action.model_type}

Target:
{action.target}

Features:
{action.features}

Actual model result:
{compact_json(result)}

Return one Finding.

Report only metrics present in the tool result.
Do not invent metrics.
State whether the candidate beats the baseline
only when the result explicitly contains that evidence.
Mention leakage warnings when present.
"""

    finding_model = structured_llm(Finding)

    finding: Finding = await finding_model.ainvoke(
        finding_prompt
    )

    finding.evidence_ids = [evidence_id]

    step = create_step(
        agent="stats_ml",
        action="train_model",
        status="success",
        duration=int(time.time() * 1000) - start,
        message=f"Trained {action.model_type}",
        evidence_ids=[evidence_id],
    )

    evidence.step_id = step.step_id

    return AgentOutput(
        findings=[finding],
        evidence=[evidence],
        tool_results=[
            {
                "tool": "train_model",
                "model": action.model_type,
                "result": result,
            }
        ],
        steps=[step],
    )