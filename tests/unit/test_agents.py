from __future__ import annotations

from backend.db.models import (
    Critique,
    Evidence,
    Finding,
    Plan,
    RunStep,
)


def test_plan_is_structured() -> None:
    plan = Plan(
        analysis_type="diagnostic",
        target="churn",
        dataset="demo",
        steps=[
            "inspect dataset",
            "compare churn by segment",
            "test significance",
        ],
        specialists=[
            "sql_analyst",
            "stats_ml",
        ],
        rationale="Compare customer segments.",
    )

    assert plan.analysis_type == "diagnostic"
    assert plan.target == "churn"
    assert len(plan.steps) == 3


def test_finding_is_structured() -> None:
    finding = Finding(
        claim="Segment A has the highest churn rate.",
        evidence_ids=["ev_123"],
        numbers={
            "churn_rate": 0.75,
        },
        limitations=[
            "Small sample size.",
        ],
    )

    assert finding.evidence_ids == ["ev_123"]
    assert finding.numbers["churn_rate"] == 0.75


def test_evidence_is_structured() -> None:
    evidence = Evidence(
        evidence_id="ev_001",
        kind="sql",
        step_id="step_001",
        summary="Churn by customer segment.",
    )

    assert evidence.kind == "sql"


def test_critique_verdict() -> None:
    critique = Critique(
        verdict="revise",
        issues=[],
        confidence=0.9,
    )

    assert critique.verdict == "revise"


def test_run_step() -> None:
    step = RunStep(
        step_id="step_001",
        agent="sql_analyst",
        action="run_sql",
        status="success",
        duration_ms=120,
        message="Query completed.",
    )

    assert step.agent == "sql_analyst"
    assert step.status == "success"