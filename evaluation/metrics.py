from __future__ import annotations

from typing import Any


def evaluate_task(
    prediction: Any,
    reference: Any | None = None,
) -> dict[str, Any]:
    """
    Day 1 placeholder evaluator.

    Actual benchmark-specific scoring will be added later.
    """
    return {
        "success": prediction is not None,
        "correct": None,
        "score": None,
        "reference_available": reference is not None,
    }