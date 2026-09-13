import json

from backend.llm import get_llm
from backend.mcp_client import call
from backend.schemas import ValidationReport, Issue

RULES_PROMPT = """You are checking whether a Python script follows the rules it
was given. Be strict, but do not invent problems.

RULES FROM THE REQUEST:
{constraints}

THE SCRIPT:
{code}

WHAT IT PRINTED:
{stdout}

For each rule, decide: followed, or not followed.
Reply with JSON only, in this exact shape:
{{"unmet": [{{"constraint": "...", "reason": "..."}}]}}
If every rule was followed, reply {{"unmet": []}}.
"""


async def validate_node(state: dict) -> dict:
    task_id = state["task_id"]
    spec = state["spec"]
    run = state.get("execution_result", {})
    issues: list[Issue] = []

    # ---------- Check 1: did the script run? ----------
    execution_score = 1.0 if run.get("exit_code") == 0 else 0.0
    if execution_score == 0.0:
        issues.append(Issue(
            severity="high",
            type="runtime_error",
            message=f"{run.get('error_type')}: {run.get('error_summary')}",
        ))

    # ---------- Check 2: were the requested files created? ----------
    required = spec.get("required_outputs", [])
    raw = await call("validation", "validate_manifest",
                     task_id=task_id, required_outputs=required)
    manifest = json.loads(raw) if isinstance(raw, str) else raw

    artifact_score = manifest.get("artifact_score", 0.0)
    for message in manifest.get("issues", []):
        issues.append(Issue(severity="high", type="missing_output", message=message))

    # ---------- Check 3: is each file correct inside? ----------
    requirements = spec.get("requirements", [])
    passed = 0
    for req in requirements:
        result = await _check_one_file(task_id, req)
        if result.get("valid"):
            passed += 1
        else:
            for message in result.get("issues", []):
                issues.append(Issue(severity="high", type="bad_artifact", message=message))

    requirement_score = passed / len(requirements) if requirements else artifact_score

    # ---------- Check 4: did it follow the rules? (model, last resort) ----------
    semantic_score = 1.0
    constraints = spec.get("constraints", [])
    # Only worth asking if everything else already looks fine
    if constraints and execution_score == 1.0 and artifact_score >= 0.99:
        llm = get_llm("validator")
        response = await llm.ainvoke(RULES_PROMPT.format(
            constraints=json.dumps(constraints, indent=2),
            code=state.get("code", "")[:12000],
            stdout=(run.get("stdout") or "")[-2000:],
        ))
        unmet = _read_unmet(response.content)
        if unmet:
            semantic_score = max(0.0, 1 - len(unmet) / len(constraints))
            for item in unmet:
                issues.append(Issue(
                    severity="high",
                    type="missing_requirement",
                    message=f"{item.get('constraint')}: {item.get('reason')}",
                ))

    # ---------- Add it all up ----------
    final_score = (0.25 * execution_score
                   + 0.30 * artifact_score
                   + 0.35 * requirement_score
                   + 0.10 * semantic_score)

    # Any 'high' problem means fail
    serious = [i for i in issues if i.severity == "high"]
    status = "PASS" if not serious else "FAIL"

    report = ValidationReport(
        status=status,
        execution_score=execution_score,
        artifact_score=round(artifact_score, 3),
        requirement_score=round(requirement_score, 3),
        semantic_score=round(semantic_score, 3),
        final_score=round(final_score, 3),
        issues=issues,
        repair_instruction=_write_repair_note(issues),
    )

    return {
        "validation": report.model_dump(),
        "status": "reporting" if status == "PASS" else "repairing",
        "logs": [f"validator: {status}  score={report.final_score}  "
                 f"problems={len(issues)}"],
    }


async def _check_one_file(task_id: str, req: dict) -> dict:
    """Send each required file to the right checking tool."""
    kind = req.get("kind")
    name = req.get("name")

    if kind == "csv":
        raw = await call("validation", "validate_csv",
                         task_id=task_id, name=name,
                         expected_columns=req.get("expected_columns"),
                         expected_rows=req.get("expected_rows"))
    elif kind == "image":
        raw = await call("validation", "validate_image", task_id=task_id, name=name)
    elif kind == "model":
        raw = await call("validation", "validate_model", task_id=task_id, name=name)
    elif kind == "text":
        raw = await call("validation", "validate_text",
                         task_id=task_id, name=name,
                         required_keywords=req.get("required_keywords"),
                         numeric_only=req.get("numeric_only", False))
    else:
        raw = await call("validation", "validate_file", task_id=task_id, name=name)

    return json.loads(raw) if isinstance(raw, str) else raw


def _read_unmet(text: str) -> list[dict]:
    """Pull the JSON out of the model's reply. If it's malformed, assume no problems."""
    try:
        cleaned = text.strip().strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        return json.loads(cleaned).get("unmet", [])
    except Exception:
        return []


def _write_repair_note(issues: list[Issue]) -> str:
    """Turn the problems into short instructions for the coder."""
    if not issues:
        return ""
    lines = ["Fix the following. Change as little else as possible:"]
    for issue in issues:
        if issue.severity == "high":
            lines.append(f"- [{issue.type}] {issue.message}")
    return "\n".join(lines)