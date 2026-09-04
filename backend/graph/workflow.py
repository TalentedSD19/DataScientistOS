from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.agents.critic import run_critic
from backend.agents.eda_agent import run_eda_agent
from backend.agents.manager import run_manager
from backend.agents.reporter import run_reporter
from backend.agents.scout import run_scout
from backend.agents.sql_agent import run_sql_agent
from backend.agents.stats_ml_agent import run_stats_ml_agent
from backend.evidence.validator import validate_evidence
from backend.mcp.client import MCPToolClient
from backend.graph.state import State


MAX_STEPS = 10
MAX_RETRIES = 2
MAX_CRITIC_ROUNDS = 2


def _append_unique(
    current: list[dict[str, Any]],
    new_items: list[Any],
) -> list[dict[str, Any]]:
    """
    Append serialized items without mutating the original list.
    """

    result = list(current)

    for item in new_items:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        else:
            result.append(item)

    return result


def _step_allowed(state: State) -> bool:
    return state["steps"] < MAX_STEPS


def _increment_step(state: State) -> int:
    return state["steps"] + 1


def _get_profile(state: State) -> dict[str, Any]:
    return state.get("profile", {})


def _get_dataset(state: State) -> str:
    dataset = state.get("dataset")

    if not dataset:
        raise RuntimeError(
            "No dataset selected after scout step."
        )

    return dataset


async def manager_node(state: State) -> dict[str, Any]:
    if not _step_allowed(state):
        return {
            "errors": state["errors"]
            + [
                {
                    "type": "step_limit",
                    "message": "Maximum graph steps reached.",
                }
            ]
        }

    async with MCPToolClient() as mcp:
        datasets = await mcp.call(
            "list_datasets",
            {},
        )

    available_datasets = datasets.get(
        "datasets",
        [],
    )

    plan, step = await run_manager(
        state["question"],
        available_datasets,
    )

    return {
        "plan": plan.model_dump(),
        "dataset": plan.dataset,
        "steps": _increment_step(state),
        "errors": state["errors"],
    }


async def scout_node(state: State) -> dict[str, Any]:
    if not _step_allowed(state):
        return {
            "errors": state["errors"]
            + [
                {
                    "type": "step_limit",
                    "message": "Maximum graph steps reached.",
                }
            ]
        }

    plan = state.get("plan") or {}

    dataset = (
        state.get("dataset")
        or plan.get("dataset")
    )

    output = await run_scout(
        dataset=dataset,
    )

    selected_dataset = dataset
    profile: dict[str, Any] = {}

    for item in output.tool_results:
        if item.get("tool") == "inspect_dataset":
            selected_dataset = item.get("dataset")
            profile = item.get("result", {})

    return {
        "dataset": selected_dataset,
        "profile": profile,
        "tool_results": _append_unique(
            state["tool_results"],
            output.tool_results,
        ),
        "steps": _increment_step(state),
        "errors": state["errors"]
        + output.errors,
    }


async def sql_node(state: State) -> dict[str, Any]:
    if not _step_allowed(state):
        return {
            "errors": state["errors"]
            + [
                {
                    "type": "step_limit",
                    "message": "Maximum graph steps reached.",
                }
            ]
        }

    output = await run_sql_agent(
        question=state["question"],
        dataset=_get_dataset(state),
        profile=_get_profile(state),
    )

    return {
        "findings": _append_unique(
            state["findings"],
            output.findings,
        ),
        "evidence": _append_unique(
            state["evidence"],
            output.evidence,
        ),
        "tool_results": _append_unique(
            state["tool_results"],
            output.tool_results,
        ),
        "steps": _increment_step(state),
        "errors": state["errors"]
        + output.errors,
    }


async def eda_node(state: State) -> dict[str, Any]:
    if not _step_allowed(state):
        return {
            "errors": state["errors"]
            + [
                {
                    "type": "step_limit",
                    "message": "Maximum graph steps reached.",
                }
            ]
        }

    output = await run_eda_agent(
        question=state["question"],
        dataset=_get_dataset(state),
        profile=_get_profile(state),
    )

    return {
        "findings": _append_unique(
            state["findings"],
            output.findings,
        ),
        "evidence": _append_unique(
            state["evidence"],
            output.evidence,
        ),
        "tool_results": _append_unique(
            state["tool_results"],
            output.tool_results,
        ),
        "steps": _increment_step(state),
        "errors": state["errors"]
        + output.errors,
    }


async def stats_ml_node(state: State) -> dict[str, Any]:
    if not _step_allowed(state):
        return {
            "errors": state["errors"]
            + [
                {
                    "type": "step_limit",
                    "message": "Maximum graph steps reached.",
                }
            ]
        }

    plan = state.get("plan") or {}

    analysis_type = plan.get(
        "analysis_type",
        "diagnostic",
    )

    target = plan.get("target")

    output = await run_stats_ml_agent(
        question=state["question"],
        dataset=_get_dataset(state),
        profile=_get_profile(state),
        analysis_type=analysis_type,
        target=target,
    )

    return {
        "findings": _append_unique(
            state["findings"],
            output.findings,
        ),
        "evidence": _append_unique(
            state["evidence"],
            output.evidence,
        ),
        "tool_results": _append_unique(
            state["tool_results"],
            output.tool_results,
        ),
        "steps": _increment_step(state),
        "errors": state["errors"]
        + output.errors,
    }


async def critic_node(state: State) -> dict[str, Any]:
    if not _step_allowed(state):
        return {
            "errors": state["errors"]
            + [
                {
                    "type": "step_limit",
                    "message": "Maximum graph steps reached.",
                }
            ]
        }

    critique, step = await run_critic(
        question=state["question"],
        plan=state.get("plan") or {},
        findings=state["findings"],
        evidence=state["evidence"],
        errors=state["errors"],
    )

    return {
        "critique": critique.model_dump(),
        "critic_rounds": state["critic_rounds"] + 1,
        "steps": _increment_step(state),
    }


async def evidence_validation_node(
    state: State,
) -> dict[str, Any]:
    valid, validation_errors = validate_evidence(
        state["findings"],
        state["evidence"],
    )

    if valid:
        return {}

    return {
        "errors": state["errors"]
        + [
            {
                "type": "evidence_validation",
                "message": error,
            }
            for error in validation_errors
        ]
    }


async def reporter_node(state: State) -> dict[str, Any]:
    report, step = await run_reporter(
        question=state["question"],
        plan=state.get("plan") or {},
        findings=state["findings"],
        evidence=state["evidence"],
    )

    return {
        "report": report.model_dump(),
    }


def route_after_manager(state: State) -> str:
    return "scout"


def route_after_scout(state: State) -> str:
    plan = state.get("plan") or {}

    analysis_type = plan.get(
        "analysis_type",
        "insufficient_data",
    )

    if analysis_type == "insufficient_data":
        return "reporter"

    if analysis_type == "predictive":
        return "eda"

    return "sql"


def route_after_sql(state: State) -> str:
    plan = state.get("plan") or {}

    analysis_type = plan.get(
        "analysis_type",
        "descriptive",
    )

    if analysis_type == "descriptive":
        return "eda"

    if analysis_type == "diagnostic":
        return "eda"

    return "critic"


def route_after_eda(state: State) -> str:
    plan = state.get("plan") or {}

    analysis_type = plan.get(
        "analysis_type",
        "descriptive",
    )

    if analysis_type in {
        "diagnostic",
        "predictive",
    }:
        return "stats_ml"

    return "critic"


_SEVERITY_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def _issue_category(
    issue: dict[str, Any],
) -> str | None:
    text = (
        str(issue.get("description", ""))
        + " "
        + str(issue.get("suggested_fix", ""))
    ).lower()

    if any(
        term in text
        for term in (
            "sql",
            "query",
            "join",
            "aggregation",
            "table",
            "column",
        )
    ):
        return "sql"

    if any(
        term in text
        for term in (
            "statistic",
            "p-value",
            "p value",
            "correlation",
            "test",
            "significance",
            "model",
            "leakage",
            "baseline",
        )
    ):
        return "stats_ml"

    return None


def _repair_target(
    state: State,
) -> str:
    critique = state.get("critique") or {}

    issues = critique.get("issues", [])

    # Evaluate each issue on its own text, most severe first, so a
    # stray keyword in a low-priority issue (e.g. "aggregation" used
    # in a non-SQL sense) can't outrank the category the *worst*
    # issue actually belongs to.
    ordered_issues = sorted(
        issues,
        key=lambda issue: _SEVERITY_RANK.get(
            issue.get("severity", "low"),
            2,
        ),
    )

    for issue in ordered_issues:
        category = _issue_category(issue)

        if category is not None:
            return category

    return "eda"


def route_after_critic(state: State) -> str:
    critique = state.get("critique") or {}

    verdict = critique.get(
        "verdict",
        "reject",
    )

    if verdict == "revise":
        if state["critic_rounds"] >= MAX_CRITIC_ROUNDS:
            return "validate"

        if state["steps"] >= MAX_STEPS:
            return "validate"

        return _repair_target(state)

    return "validate"


def route_after_validation(state: State) -> str:
    """
    Day 4 behavior:
    validation failures are recorded and the reporter is still given
    only the evidence-backed findings already collected.
    """

    return "reporter"


def build_graph():
    builder = StateGraph(State)

    builder.add_node("manager", manager_node)
    builder.add_node("scout", scout_node)
    builder.add_node("sql", sql_node)
    builder.add_node("eda", eda_node)
    builder.add_node("stats_ml", stats_ml_node)
    builder.add_node("critic", critic_node)
    builder.add_node(
        "validate",
        evidence_validation_node,
    )
    builder.add_node("reporter", reporter_node)

    builder.add_edge(START, "manager")

    builder.add_conditional_edges(
        "manager",
        route_after_manager,
        {
            "scout": "scout",
        },
    )

    builder.add_conditional_edges(
        "scout",
        route_after_scout,
        {
            "sql": "sql",
            "eda": "eda",
            "reporter": "reporter",
        },
    )

    builder.add_conditional_edges(
        "sql",
        route_after_sql,
        {
            "eda": "eda",
            "critic": "critic",
        },
    )

    builder.add_conditional_edges(
        "eda",
        route_after_eda,
        {
            "stats_ml": "stats_ml",
            "critic": "critic",
        },
    )

    builder.add_edge(
        "stats_ml",
        "critic",
    )

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "sql": "sql",
            "eda": "eda",
            "stats_ml": "stats_ml",
            "validate": "validate",
        },
    )

    builder.add_edge(
        "validate",
        "reporter",
    )

    builder.add_edge(
        "reporter",
        END,
    )

    return builder.compile()


graph = build_graph()