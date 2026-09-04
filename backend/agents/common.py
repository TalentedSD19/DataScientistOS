from __future__ import annotations

import json
import time
import uuid
from typing import Any

from backend.llm import get_llm
from backend.db.models import AgentOutput, Finding, RunStep


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def now_ms() -> int:
    return int(time.time() * 1000)


def duration_ms(start_ms: int) -> int:
    return now_ms() - start_ms


def create_step(
    *,
    agent: str,
    action: str,
    status: str,
    duration: int,
    message: str = "",
    evidence_ids: list[str] | None = None,
) -> RunStep:
    return RunStep(
        step_id=new_id("step"),
        agent=agent,
        action=action,
        status=status,
        duration_ms=duration,
        message=message,
        evidence_ids=evidence_ids or [],
    )


def compact_json(value: Any, max_chars: int = 12000) -> str:
    text = json.dumps(
        value,
        ensure_ascii=False,
        default=str,
        indent=2,
    )

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n...[truncated]"


def structured_llm(schema: type[Any]):
    """
    Return an LLM that produces a validated Pydantic object.

    Function calling is used instead of OpenAI native JSON-schema
    output because it is more tolerant of the Pydantic schemas used
    by this project.
    """
    return get_llm().with_structured_output(
        schema,
        method="function_calling",
    )

def make_agent_output(
    *,
    findings: list[Finding] | None = None,
    evidence=None,
    tool_results=None,
    steps=None,
    errors=None,
) -> AgentOutput:
    return AgentOutput(
        findings=findings or [],
        evidence=evidence or [],
        tool_results=tool_results or [],
        steps=steps or [],
        errors=errors or [],
    )