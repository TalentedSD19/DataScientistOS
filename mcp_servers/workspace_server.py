import json
from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP

from backend.config import workspace_dir

mcp = FastMCP("workspace", host="127.0.0.1", port=8011)


def _resolve(task_id: str, rel_path: str) -> Path:
    """Turn 'input/data.csv' into a real path, and refuse to go outside the workspace."""
    ws = workspace_dir(task_id).resolve()
    full = (ws / rel_path.lstrip("/\\")).resolve()
    if not str(full).startswith(str(ws)):
        raise ValueError("that path is outside the workspace")
    return full


@mcp.tool()
def list_files(task_id: str, subdir: str = "") -> str:
    """List every file in the task workspace."""
    base = _resolve(task_id, subdir)
    if not base.exists():
        return json.dumps({"files": []})
    ws = workspace_dir(task_id).resolve()
    files = [str(p.relative_to(ws)) for p in base.rglob("*") if p.is_file()]
    return json.dumps({"files": sorted(files)})


@mcp.tool()
def read_file(task_id: str, path: str, max_chars: int = 8000) -> str:
    """Read a text file from the workspace."""
    p = _resolve(task_id, path)
    if not p.exists():
        return json.dumps({"error": "file not found", "path": path})
    text = p.read_text(errors="replace")
    return json.dumps({
        "path": path,
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
    })


@mcp.tool()
def write_file(task_id: str, path: str, content: str) -> str:
    """Write a text file into the workspace. Creates folders if needed."""
    p = _resolve(task_id, path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return json.dumps({"ok": True, "path": path, "bytes": len(content)})


@mcp.tool()
def file_exists(task_id: str, path: str) -> str:
    """Check whether a file is there."""
    return json.dumps({"exists": _resolve(task_id, path).exists()})


@mcp.tool()
def file_info(task_id: str, path: str) -> str:
    """Size and extension of a file."""
    p = _resolve(task_id, path)
    if not p.exists():
        return json.dumps({"exists": False})
    return json.dumps({"exists": True, "size": p.stat().st_size, "type": p.suffix})


def _inspect_dataset(task_id: str, path: str) -> dict:
    p = _resolve(task_id, path)
    if not p.exists():
        return {"error": "file not found", "path": path}

    kind = p.suffix.lower()

    # ---- Excel ----
    if kind in (".xlsx", ".xls"):
        book = pd.ExcelFile(p)
        return {
            "type": "excel",
            "sheets": book.sheet_names,
            "preview": {
                s: book.parse(s, nrows=5).to_dict(orient="records")
                for s in book.sheet_names[:5]
            },
        }

    # ---- JSON ----
    if kind == ".json":
        return {"type": "json", "content": p.read_text()[:4000]}

    # ---- CSV / TSV ----
    if kind in (".csv", ".tsv"):
        separator = "\t" if kind == ".tsv" else ","
        try:
            df = pd.read_csv(p, sep=separator)
        except UnicodeDecodeError:
            # Chinese CSVs often need this encoding
            df = pd.read_csv(p, sep=separator, encoding="gbk")

        columns = list(df.columns)[:60]
        return {
            "type": "csv",
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": columns,
            "dtypes": {c: str(df[c].dtype) for c in columns},
            "missing": {c: int(df[c].isna().sum()) for c in columns},
            "unique": {c: int(df[c].nunique()) for c in columns},
            "head": df.head(5).to_dict(orient="records"),
            "duplicate_rows": int(df.duplicated().sum()),
        }

    # ---- Plain text (.txt and anything else readable) ----
    # Not every .txt is tabular -- Kaggle-style data dictionaries, READMEs, etc.
    # are prose, so just preview the raw text instead of forcing it through
    # a CSV parser.
    if kind == ".txt":
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = p.read_text(encoding="gbk")
        return {"type": "text", "content": text[:4000]}

    return {"type": "unknown", "size": p.stat().st_size}


@mcp.tool()
def inspect_dataset(task_id: str, path: str) -> str:
    """Look at a data file before writing any code: shape, column names, types,
    missing values, first few rows. This is what stops the model from inventing
    column names that don't exist."""
    try:
        return json.dumps(_inspect_dataset(task_id, path), default=str)
    except Exception as e:
        # Never let a single unreadable/malformed file kill the whole planning
        # step -- surface the failure as data instead of an empty/crashed call.
        return json.dumps({"error": f"{type(e).__name__}: {e}", "path": path})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")