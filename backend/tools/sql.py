from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from backend.tools.registry import get_dataset


FORBIDDEN_SQL = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "ATTACH",
    "DETACH",
    "REPLACE",
    "VACUUM",
    "PRAGMA",
}


def _validate_read_only_sql(query: str) -> None:
    query = query.strip()

    if not query:
        raise ValueError("SQL query cannot be empty")

    normalized = re.sub(r"\s+", " ", query.upper()).strip()

    if not (
        normalized.startswith("SELECT ")
        or normalized.startswith("WITH ")
    ):
        raise ValueError(
            "Only SELECT and WITH queries are allowed"
        )

    for keyword in FORBIDDEN_SQL:
        pattern = rf"\b{keyword}\b"

        if re.search(pattern, normalized):
            raise ValueError(
                f"Forbidden SQL keyword detected: {keyword}"
            )


def run_sql(dataset: str, query: str) -> dict[str, Any]:
    dataset_info = get_dataset(dataset)

    _validate_read_only_sql(query)

    if dataset_info["type"] != "sqlite":
        raise ValueError(
            f"Unsupported dataset type: {dataset_info['type']}"
        )

    path = Path(dataset_info["path"])

    started = time.perf_counter()

    connection = sqlite3.connect(
        f"file:{path.resolve()}?mode=ro",
        uri=True,
    )

    try:
        cursor = connection.execute(query)

        columns = [
            description[0]
            for description in cursor.description or []
        ]

        rows = cursor.fetchmany(1000)

        return {
            "success": True,
            "dataset": dataset,
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
            "runtime_ms": round(
                (time.perf_counter() - started) * 1000,
                2,
            ),
        }

    except sqlite3.Error as exc:
        return {
            "success": False,
            "dataset": dataset,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "runtime_ms": round(
                (time.perf_counter() - started) * 1000,
                2,
            ),
            "error": str(exc),
            "error_type": "sql",
        }

    finally:
        connection.close()