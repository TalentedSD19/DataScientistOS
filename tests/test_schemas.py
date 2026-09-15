import pytest
from pydantic import ValidationError

from backend.schemas import NextStep, VerifierResult, RouterDecision


def test_next_step_valid():
    step = NextStep(goal="load the csv file")
    assert step.goal == "load the csv file"


def test_verifier_result_accepts_known_status():
    assert VerifierResult(status="SUFFICIENT").status == "SUFFICIENT"
    assert VerifierResult(status="INSUFFICIENT").status == "INSUFFICIENT"


def test_verifier_result_rejects_unknown_status():
    with pytest.raises(ValidationError):
        VerifierResult(status="MAYBE")


def test_router_decision_add_step():
    decision = RouterDecision(action="ADD_STEP")
    assert decision.action == "ADD_STEP"
    assert decision.backtrack_to is None


def test_router_decision_backtrack_with_step_id():
    decision = RouterDecision(action="BACKTRACK", backtrack_to=2)
    assert decision.backtrack_to == 2


def test_router_decision_rejects_unknown_action():
    with pytest.raises(ValidationError):
        RouterDecision(action="RESTART")
