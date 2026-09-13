import json
from pathlib import Path

import pandas as pd
from PIL import Image
from mcp.server.fastmcp import FastMCP

from backend.config import workspace_dir

mcp = FastMCP("validation", host="127.0.0.1", port=8013)


def _find(task_id: str, name: str):
    """Find a required output file anywhere in the workspace.
    The prompt may say 'output.csv' while the code saved it in outputs/."""
    ws = workspace_dir(task_id)
    direct = ws / name
    if direct.exists():
        return direct
    matches = [p for p in ws.rglob(Path(name).name) if p.is_file()]
    return matches[0] if matches else None


@mcp.tool()
def validate_file(task_id: str, name: str) -> str:
    """Does this file exist and is it non-empty?"""
    p = _find(task_id, name)
    if p is None:
        return json.dumps({"valid": False, "issues": [f"{name} was not created"]})
    if p.stat().st_size == 0:
        return json.dumps({"valid": False, "issues": [f"{name} is empty"]})
    return json.dumps({"valid": True, "size": p.stat().st_size})


@mcp.tool()
def validate_csv(task_id: str, name: str,
                 expected_columns: list[str] | None = None,
                 expected_rows: int | None = None,
                 no_nulls: bool = False) -> str:
    """Check a CSV opens and has the columns / row count that were asked for."""
    p = _find(task_id, name)
    if p is None:
        return json.dumps({"valid": False, "issues": [f"{name} was not created"]})

    try:
        df = pd.read_csv(p)
    except Exception as e:
        return json.dumps({"valid": False, "issues": [f"{name} could not be read: {e}"]})

    issues = []
    if expected_columns:
        missing = [c for c in expected_columns if c not in df.columns]
        if missing:
            issues.append(f"{name} is missing columns: {missing}")
    if expected_rows is not None and len(df) != expected_rows:
        issues.append(f"{name} should have {expected_rows} rows but has {len(df)}")
    if no_nulls and df.isna().any().any():
        issues.append(f"{name} still has empty cells")

    return json.dumps({
        "valid": not issues, "issues": issues,
        "rows": int(len(df)), "columns": list(df.columns)[:50],
    })


@mcp.tool()
def validate_image(task_id: str, name: str, min_width: int = 100) -> str:
    """Check a chart exists, opens, and isn't a blank picture."""
    p = _find(task_id, name)
    if p is None:
        return json.dumps({"valid": False, "issues": [f"{name} was not created"]})

    try:
        img = Image.open(p)
        img.load()
    except Exception as e:
        return json.dumps({"valid": False, "issues": [f"{name} is not a valid image: {e}"]})

    issues = []
    if img.width < min_width:
        issues.append(f"{name} is far too small ({img.width}px wide)")

    # If the darkest and lightest pixel are the same, the image is one flat colour
    low, high = img.convert("L").getextrema()
    if low == high:
        issues.append(f"{name} looks blank")

    return json.dumps({"valid": not issues, "issues": issues,
                       "width": img.width, "height": img.height})


@mcp.tool()
def validate_model(task_id: str, name: str) -> str:
    """Check a saved model file loads and can actually predict."""
    p = _find(task_id, name)
    if p is None:
        return json.dumps({"valid": False, "issues": [f"{name} was not created"]})

    if p.suffix.lower() in (".pkl", ".joblib"):
        try:
            import joblib
            model = joblib.load(p)
        except Exception as e:
            return json.dumps({"valid": False, "issues": [f"{name} would not load: {e}"]})

        if not hasattr(model, "predict"):
            return json.dumps({
                "valid": False,
                "issues": [f"{name} has no predict() method"],
                "model_type": type(model).__name__,
            })

        from sklearn.exceptions import NotFittedError
        from sklearn.utils.validation import check_is_fitted
        try:
            check_is_fitted(model)
        except NotFittedError:
            return json.dumps({
                "valid": False,
                "issues": [f"{name} was saved before being fit on the full data "
                           f"(cross_val_score does not fit the original estimator)"],
                "model_type": type(model).__name__,
            })
        except TypeError:
            pass  # not a plain sklearn estimator; skip the fitted check

        return json.dumps({
            "valid": True,
            "issues": [],
            "model_type": type(model).__name__,
        })

    # .h5 / .pt files: just check it isn't empty
    return json.dumps({"valid": p.stat().st_size > 0, "issues": []})


@mcp.tool()
def validate_text(task_id: str, name: str,
                  required_keywords: list[str] | None = None,
                  numeric_only: bool = False) -> str:
    """Check a txt/md file exists and contains what the prompt asked for."""
    p = _find(task_id, name)
    if p is None:
        return json.dumps({"valid": False, "issues": [f"{name} was not created"]})

    text = p.read_text(errors="replace")
    issues = []
    for word in (required_keywords or []):
        if word.lower() not in text.lower():
            issues.append(f"{name} does not mention '{word}'")
    if numeric_only:
        try:
            float(text.strip())
        except ValueError:
            issues.append(f"{name} should contain just one number")

    return json.dumps({"valid": not issues, "issues": issues, "preview": text[:500]})


@mcp.tool()
def validate_manifest(task_id: str, required_outputs: list[str]) -> str:
    """One call that checks every required file at once and saves a summary
    to state/manifest.json."""
    ws = workspace_dir(task_id)
    artifacts, issues = {}, []

    for name in required_outputs:
        p = _find(task_id, name)
        if p is None:
            artifacts[name] = {"exists": False}
            issues.append(f"{name} was not created")
            continue

        info = {"exists": True, "size": p.stat().st_size,
                "path": str(p.relative_to(ws))}
        try:
            if p.suffix.lower() == ".csv":
                df = pd.read_csv(p)
                info["rows"] = int(len(df))
                info["columns"] = list(df.columns)[:50]
            elif p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                img = Image.open(p); img.load()
                info["width"], info["height"] = img.width, img.height
        except Exception as e:
            info["error"] = str(e)
            issues.append(f"{name} exists but could not be opened: {e}")

        artifacts[name] = info

    manifest = {"required_outputs": required_outputs, "artifacts": artifacts}
    (ws / "state").mkdir(parents=True, exist_ok=True)
    (ws / "state" / "manifest.json").write_text(json.dumps(manifest, indent=2))

    produced = sum(1 for a in artifacts.values() if a.get("exists"))
    return json.dumps({
        "valid": not issues,
        "issues": issues,
        "artifact_score": produced / max(len(required_outputs), 1),
        "manifest": manifest,
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")