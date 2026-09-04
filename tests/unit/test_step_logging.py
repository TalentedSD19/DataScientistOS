from backend.db.models import RunStep


def test_sql_step_is_recorded() -> None:
    step = RunStep(
        step_id="step_001",
        agent="sql_analyst",
        action="run_sql",
        status="success",
        duration_ms=812,
        message="Query succeeded",
        evidence_ids=["ev_001"],
    )

    assert step.agent == "sql_analyst"
    assert step.action == "run_sql"
    assert step.status == "success"
    assert step.duration_ms == 812
    assert step.evidence_ids == ["ev_001"]