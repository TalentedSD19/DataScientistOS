from __future__ import annotations

from backend.evidence.validator import validate_evidence
from backend.graph.workflow import (
    MAX_CRITIC_ROUNDS,
    MAX_STEPS,
    route_after_critic,
    route_after_eda,
    route_after_scout,
    route_after_sql,
)


def test_graph_limits() -> None:
    assert MAX_STEPS == 10
    assert MAX_CRITIC_ROUNDS == 2


def test_descriptive_route_after_scout() -> None:
    state = {
        "plan": {
            "analysis_type": "descriptive",
        },
        "critic_rounds": 0,
        "steps": 1,
    }

    assert route_after_scout(state) == "sql"


def test_diagnostic_route_after_scout() -> None:
    state = {
        "plan": {
            "analysis_type": "diagnostic",
        },
        "critic_rounds": 0,
        "steps": 1,
    }

    assert route_after_scout(state) == "sql"


def test_predictive_route_after_scout() -> None:
    state = {
        "plan": {
            "analysis_type": "predictive",
        },
        "critic_rounds": 0,
        "steps": 1,
    }

    assert route_after_scout(state) == "eda"


def test_diagnostic_route_after_eda() -> None:
    state = {
        "plan": {
            "analysis_type": "diagnostic",
        },
    }

    assert route_after_eda(state) == "stats_ml"


def test_descriptive_route_after_eda() -> None:
    state = {
        "plan": {
            "analysis_type": "descriptive",
        },
    }

    assert route_after_eda(state) == "critic"


def test_diagnostic_route_after_sql() -> None:
    state = {
        "plan": {
            "analysis_type": "diagnostic",
        },
    }

    assert route_after_sql(state) == "eda"


def test_revise_routes_to_sql() -> None:
    state = {
        "critique": {
            "verdict": "revise",
            "issues": [
                {
                    "severity": "high",
                    "description": "Wrong SQL aggregation.",
                    "suggested_fix": "Fix the query.",
                }
            ],
        },
        "critic_rounds": 1,
        "steps": 5,
    }

    assert route_after_critic(state) == "sql"


def test_revise_routes_to_stats() -> None:
    state = {
        "critique": {
            "verdict": "revise",
            "issues": [
                {
                    "severity": "high",
                    "description": "Wrong statistical test.",
                    "suggested_fix": "Use an appropriate test.",
                }
            ],
        },
        "critic_rounds": 1,
        "steps": 5,
    }

    assert route_after_critic(state) == "stats_ml"


def test_revise_routes_to_eda() -> None:
    state = {
        "critique": {
            "verdict": "revise",
            "issues": [
                {
                    "severity": "medium",
                    "description": "The exploratory analysis is incomplete.",
                    "suggested_fix": "Run another focused analysis.",
                }
            ],
        },
        "critic_rounds": 1,
        "steps": 5,
    }

    assert route_after_critic(state) == "eda"


def test_critic_limit_routes_to_validation() -> None:
    state = {
        "critique": {
            "verdict": "revise",
            "issues": [],
        },
        "critic_rounds": MAX_CRITIC_ROUNDS,
        "steps": 5,
    }

    assert route_after_critic(state) == "validate"


def test_step_limit_routes_to_validation() -> None:
    state = {
        "critique": {
            "verdict": "revise",
            "issues": [],
        },
        "critic_rounds": 1,
        "steps": MAX_STEPS,
    }

    assert route_after_critic(state) == "validate"


def test_evidence_validation_passes() -> None:
    findings = [
        {
            "claim": "Segment A has the highest churn.",
            "evidence_ids": ["ev_001"],
        }
    ]

    evidence = [
        {
            "evidence_id": "ev_001",
            "kind": "sql",
        }
    ]

    valid, errors = validate_evidence(
        findings,
        evidence,
    )

    assert valid is True
    assert errors == []


def test_evidence_validation_fails() -> None:
    findings = [
        {
            "claim": "Segment A has the highest churn.",
            "evidence_ids": ["ev_missing"],
        }
    ]

    evidence = [
        {
            "evidence_id": "ev_001",
            "kind": "sql",
        }
    ]

    valid, errors = validate_evidence(
        findings,
        evidence,
    )

    assert valid is False
    assert len(errors) == 1