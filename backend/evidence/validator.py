from __future__ import annotations

from typing import Any


def validate_evidence(
    findings: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """
    Verify that every finding points to existing evidence.

    This is intentionally simple for Day 4.
    More advanced numerical verification can be added later.
    """

    evidence_ids = {
        item.get("evidence_id")
        for item in evidence
        if item.get("evidence_id")
    }

    errors: list[str] = []

    for index, finding in enumerate(findings):
        finding_evidence = finding.get("evidence_ids", [])

        if not finding_evidence:
            errors.append(
                f"Finding {index} has no evidence IDs."
            )
            continue

        for evidence_id in finding_evidence:
            if evidence_id not in evidence_ids:
                errors.append(
                    f"Finding {index} references missing evidence "
                    f"'{evidence_id}'."
                )

    return len(errors) == 0, errors