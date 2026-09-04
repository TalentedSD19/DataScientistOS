from __future__ import annotations

from typing import Any, TypedDict


class State(TypedDict):
    question: str

    dataset: str | None
    profile: dict[str, Any]

    plan: dict[str, Any] | None

    findings: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    critique: dict[str, Any] | None
    evidence: list[dict[str, Any]]

    report: dict[str, Any] | None

    errors: list[dict[str, Any]]

    steps: int
    critic_rounds: int