from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.server import MCPServer


# ============================================================
# Project paths
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
ARTIFACT_DIR = ROOT / "artifacts"

DEFAULT_DB = DATA_DIR / "demo.db"

ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# MCP server
# ============================================================

mcp = MCPServer("DataScientistOS")


# ============================================================
# Helpers
# ============================================================

def resolve_dataset(dataset: str) -> Path:
    """
    Resolve a dataset identifier to a local SQLite database.

    For now, the Day 3 development server uses demo.db.
    """

    if dataset in {"demo", "demo.db", "dataset_001"}:
        path = DEFAULT_DB
    else:
        candidate = DATA_DIR / dataset

        if candidate.suffix != ".db":
            candidate = candidate.with_suffix(".db")

        path = candidate

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {dataset}"
        )

    return path


def get_connection(dataset: str) -> sqlite3.Connection:
    db_path = resolve_dataset(dataset)

    connection = sqlite3.connect(
        str(db_path)
    )

    connection.row_factory = sqlite3.Row

    return connection


def json_safe(value: Any) -> Any:
    """
    Convert SQLite/Python values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def rows_to_dicts(
    rows: list[sqlite3.Row],
) -> list[dict[str, Any]]:
    return [
        {
            key: json_safe(row[key])
            for key in row.keys()
        }
        for row in rows
    ]


def find_table_for_columns(
    connection: sqlite3.Connection,
    columns: list[str],
) -> str:
    """
    Find the table that contains every requested column.

    Raises ValueError when no table contains all columns, or when
    more than one table matches and the choice would be ambiguous.
    """

    cursor = connection.cursor()

    table_rows = cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    required = set(columns)
    matches: list[str] = []

    for table_row in table_rows:
        table_name = table_row["name"]

        table_columns = {
            column["name"]
            for column in cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }

        if required.issubset(table_columns):
            matches.append(table_name)

    if not matches:
        raise ValueError(
            "No table contains all requested columns: "
            + ", ".join(sorted(required))
        )

    if len(matches) > 1:
        raise ValueError(
            "Column set is ambiguous across multiple tables: "
            + ", ".join(matches)
            + ". Qualify the dataset/table explicitly."
        )

    return matches[0]


def validate_read_only_sql(query: str) -> None:
    """
    Basic protection against write operations.

    This is intentionally simple for the portfolio MVP.
    """

    normalized = query.strip().lower()

    forbidden = [
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "create ",
        "attach ",
        "detach ",
        "replace ",
        "vacuum ",
        "pragma ",
    ]

    for keyword in forbidden:
        if normalized.startswith(keyword):
            raise ValueError(
                f"Read-only SQL only. "
                f"Forbidden operation: {keyword.strip()}"
            )

    if ";" in normalized.rstrip(";"):
        raise ValueError(
            "Multiple SQL statements are not allowed."
        )


# ============================================================
# Tool 1 — list_datasets
# ============================================================

@mcp.tool()
def list_datasets() -> dict[str, Any]:
    """
    List datasets available to DataScientistOS.
    """

    datasets: list[dict[str, Any]] = []

    if DATA_DIR.exists():
        for path in DATA_DIR.glob("*.db"):
            datasets.append(
                {
                    "id": path.stem,
                    "name": path.name,
                    "type": "sqlite",
                }
            )

    if not datasets and DEFAULT_DB.exists():
        datasets.append(
            {
                "id": "demo",
                "name": "demo.db",
                "type": "sqlite",
            }
        )

    return {
        "datasets": datasets
    }


# ============================================================
# Tool 2 — inspect_dataset
# ============================================================

@mcp.tool()
def inspect_dataset(
    dataset: str,
) -> dict[str, Any]:
    """
    Inspect SQLite tables, columns, row counts,
    missing values, unique values and likely IDs/targets.
    """

    connection = get_connection(dataset)

    try:
        cursor = connection.cursor()

        tables_rows = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        tables: list[dict[str, Any]] = []

        for table_row in tables_rows:
            table_name = table_row["name"]

            columns = cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            row_count = cursor.execute(
                f'SELECT COUNT(*) AS count '
                f'FROM "{table_name}"'
            ).fetchone()["count"]

            column_info: list[dict[str, Any]] = []

            for column in columns:
                column_name = column["name"]
                column_type = column["type"]

                quoted_table = table_name.replace(
                    '"',
                    '""',
                )

                quoted_column = column_name.replace(
                    '"',
                    '""',
                )

                missing_count = cursor.execute(
                    f'''
                    SELECT COUNT(*) AS count
                    FROM "{quoted_table}"
                    WHERE "{quoted_column}" IS NULL
                    '''
                ).fetchone()["count"]

                unique_count = cursor.execute(
                    f'''
                    SELECT COUNT(DISTINCT "{quoted_column}") AS count
                    FROM "{quoted_table}"
                    '''
                ).fetchone()["count"]

                sample_rows = cursor.execute(
                    f'''
                    SELECT "{quoted_column}"
                    FROM "{quoted_table}"
                    LIMIT 5
                    '''
                ).fetchall()

                samples = [
                    json_safe(row[0])
                    for row in sample_rows
                ]

                possible_id = (
                    column_name.lower() == "id"
                    or column_name.lower().endswith("_id")
                    or bool(column["pk"])
                )

                possible_target = (
                    column_name.lower()
                    in {
                        "target",
                        "label",
                        "class",
                        "churn",
                        "outcome",
                        "y",
                    }
                    or "target" in column_name.lower()
                    or "churn" in column_name.lower()
                )

                column_info.append(
                    {
                        "name": column_name,
                        "type": column_type,
                        "missing_count": missing_count,
                        "unique_count": unique_count,
                        "sample_values": samples,
                        "possible_id": possible_id,
                        "possible_target": possible_target,
                    }
                )

            tables.append(
                {
                    "name": table_name,
                    "columns": column_info,
                    "row_count": row_count,
                }
            )

        return {
            "success": True,
            "dataset": dataset,
            "tables": tables,
            "warnings": [],
        }

    finally:
        connection.close()


# ============================================================
# Tool 3 — run_sql
# ============================================================

@mcp.tool()
def run_sql(
    dataset: str,
    query: str,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query.
    """

    validate_read_only_sql(query)

    start = time.perf_counter()

    connection = get_connection(dataset)

    try:
        cursor = connection.cursor()

        cursor.execute(query)

        rows = cursor.fetchmany(100)

        columns = [
            description[0]
            for description in cursor.description
        ]

        result_rows = rows_to_dicts(rows)

        runtime_ms = int(
            (time.perf_counter() - start) * 1000
        )

        return {
            "success": True,
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "runtime_ms": runtime_ms,
            "warnings": [],
        }

    except Exception as exc:
        runtime_ms = int(
            (time.perf_counter() - start) * 1000
        )

        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "runtime_ms": runtime_ms,
            "error": str(exc),
            "error_type": "sql",
        }

    finally:
        connection.close()


# ============================================================
# Tool 4 — run_python
# ============================================================

@mcp.tool()
def run_python(
    dataset: str,
    code: str,
) -> dict[str, Any]:
    """
    Execute generated Python through the existing
    DataScientistOS sandbox runner when available.

    Falls back to a clear error instead of executing
    arbitrary Python inside the MCP server.
    """

    start = time.perf_counter()

    try:
        from backend.sandbox.runner import (
            run_python_in_sandbox,
        )

    except ImportError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "artifacts": [],
            "runtime_ms": 0,
            "error": (
                "backend.sandbox.runner is not available. "
                "Connect this tool to the Day 2 sandbox runner."
            ),
        }

    try:
        result = run_python_in_sandbox(
            code=code,
            dataset_path=str(
                resolve_dataset(dataset)
            ),
        )

        runtime_ms = int(
            (time.perf_counter() - start) * 1000
        )

        if not isinstance(result, dict):
            result = {
                "result": result
            }

        result.setdefault(
            "success",
            True,
        )
        result.setdefault(
            "stdout",
            "",
        )
        result.setdefault(
            "stderr",
            "",
        )
        result.setdefault(
            "artifacts",
            [],
        )
        result["runtime_ms"] = runtime_ms

        return result

    except Exception as exc:
        runtime_ms = int(
            (time.perf_counter() - start) * 1000
        )

        return {
            "success": False,
            "stdout": "",
            "stderr": str(exc),
            "artifacts": [],
            "runtime_ms": runtime_ms,
            "error": str(exc),
        }


# ============================================================
# Tool 5 — run_statistics
# ============================================================

@mcp.tool()
def run_statistics(
    test: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Run a basic statistical test.

    Expected data formats:

    chi_square:
        {
            "observed": [
                [10, 20],
                [15, 25]
            ]
        }

    t_test:
        {
            "group_a": [...],
            "group_b": [...]
        }

    pearson/spearman:
        {
            "x": [...],
            "y": [...]
        }
    """

    import numpy as np
    from scipy import stats

    start = time.perf_counter()

    try:
        if test == "chi_square":

            observed = np.asarray(
                data["observed"]
            )

            statistic, p_value, _, _ = (
                stats.chi2_contingency(
                    observed
                )
            )

            return {
                "success": True,
                "test": test,
                "statistic": float(statistic),
                "p_value": float(p_value),
                "effect_size": None,
                "warnings": [],
                "runtime_ms": int(
                    (time.perf_counter() - start)
                    * 1000
                ),
            }

        if test == "t_test":

            group_a = np.asarray(
                data["group_a"],
                dtype=float,
            )

            group_b = np.asarray(
                data["group_b"],
                dtype=float,
            )

            statistic, p_value = (
                stats.ttest_ind(
                    group_a,
                    group_b,
                    equal_var=False,
                    nan_policy="omit",
                )
            )

            return {
                "success": True,
                "test": test,
                "statistic": float(statistic),
                "p_value": float(p_value),
                "effect_size": None,
                "sample_sizes": [
                    len(group_a),
                    len(group_b),
                ],
                "warnings": [],
                "runtime_ms": int(
                    (time.perf_counter() - start)
                    * 1000
                ),
            }

        if test == "pearson":

            x = np.asarray(
                data["x"],
                dtype=float,
            )

            y = np.asarray(
                data["y"],
                dtype=float,
            )

            statistic, p_value = (
                stats.pearsonr(x, y)
            )

            return {
                "success": True,
                "test": test,
                "statistic": float(statistic),
                "p_value": float(p_value),
                "effect_size": float(statistic),
                "warnings": [],
                "runtime_ms": int(
                    (time.perf_counter() - start)
                    * 1000
                ),
            }

        if test == "spearman":

            x = np.asarray(
                data["x"],
                dtype=float,
            )

            y = np.asarray(
                data["y"],
                dtype=float,
            )

            statistic, p_value = (
                stats.spearmanr(x, y)
            )

            return {
                "success": True,
                "test": test,
                "statistic": float(statistic),
                "p_value": float(p_value),
                "effect_size": float(statistic),
                "warnings": [],
                "runtime_ms": int(
                    (time.perf_counter() - start)
                    * 1000
                ),
            }

        raise ValueError(
            f"Unsupported statistical test: {test}"
        )

    except Exception as exc:
        return {
            "success": False,
            "test": test,
            "error": str(exc),
            "warnings": [],
            "runtime_ms": int(
                (time.perf_counter() - start)
                * 1000
            ),
        }


# ============================================================
# Tool 6 — train_model
# ============================================================

@mcp.tool()
def train_model(
    dataset: str,
    target: str,
    features: list[str],
    model_type: str,
) -> dict[str, Any]:
    """
    Train a simple classification model.

    The actual implementation is intentionally small for
    the Day 3 agent milestone.
    """

    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.dummy import DummyClassifier

    start = time.perf_counter()

    connection = get_connection(dataset)

    try:
        columns = [
            target,
            *features,
        ]

        # Prevent duplicate column names.
        columns = list(dict.fromkeys(columns))

        table_name = find_table_for_columns(
            connection,
            columns,
        )

        query_columns = ", ".join(
            f'"{column.replace(chr(34), chr(34) * 2)}"'
            for column in columns
        )

        quoted_table = table_name.replace(
            '"',
            '""',
        )

        df = pd.read_sql_query(
            f'SELECT {query_columns} FROM "{quoted_table}"',
            connection,
        )

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "warnings": [],
            "runtime_ms": int(
                (time.perf_counter() - start)
                * 1000
            ),
        }

    finally:
        connection.close()

    try:
        if target not in df.columns:
            raise ValueError(
                f"Target column not found: {target}"
            )

        missing_features = [
            feature
            for feature in features
            if feature not in df.columns
        ]

        if missing_features:
            raise ValueError(
                "Features not found: "
                + ", ".join(missing_features)
            )

        if target in features:
            raise ValueError(
                "Target column cannot also be "
                "used as a feature."
            )

        df = df.dropna(
            subset=[target]
        )

        X = df[features]
        y = df[target]

        if y.nunique() < 2:
            raise ValueError(
                "Target must contain at least two classes."
            )

        # pandas >= 3.0 infers plain text columns as a dedicated
        # "str" dtype rather than "object", so checking for
        # dtype == "object" silently misses them and lets raw
        # text reach the model as if it were numeric.
        numeric_features = [
            column
            for column in features
            if pd.api.types.is_numeric_dtype(X[column])
        ]

        categorical_features = [
            column
            for column in features
            if column not in numeric_features
        ]

        preprocess = ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    "passthrough",
                    numeric_features,
                ),
                (
                    "categorical",
                    OneHotEncoder(
                        handle_unknown="ignore"
                    ),
                    categorical_features,
                ),
            ]
        )

        X_train, X_test, y_train, y_test = (
            train_test_split(
                X,
                y,
                test_size=0.25,
                random_state=42,
                stratify=y,
            )
        )

        baseline = Pipeline(
            steps=[
                (
                    "preprocess",
                    preprocess,
                ),
                (
                    "model",
                    DummyClassifier(
                        strategy="most_frequent"
                    ),
                ),
            ]
        )

        baseline.fit(
            X_train,
            y_train,
        )

        baseline_predictions = baseline.predict(
            X_test
        )

        baseline_accuracy = accuracy_score(
            y_test,
            baseline_predictions,
        )

        baseline_f1 = f1_score(
            y_test,
            baseline_predictions,
            average="weighted",
            zero_division=0,
        )

        if model_type == "logistic_regression":

            estimator = LogisticRegression(
                max_iter=1000
            )

        elif model_type == "random_forest":

            estimator = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
            )

        elif model_type == "xgboost":

            from xgboost import XGBClassifier

            estimator = XGBClassifier(
                n_estimators=100,
                random_state=42,
                eval_metric="logloss",
            )

        else:
            raise ValueError(
                f"Unsupported model: {model_type}"
            )

        model = Pipeline(
            steps=[
                (
                    "preprocess",
                    preprocess,
                ),
                (
                    "model",
                    estimator,
                ),
            ]
        )

        model.fit(
            X_train,
            y_train,
        )

        predictions = model.predict(
            X_test
        )

        accuracy = accuracy_score(
            y_test,
            predictions,
        )

        f1 = f1_score(
            y_test,
            predictions,
            average="weighted",
            zero_division=0,
        )

        return {
            "success": True,
            "model": model_type,
            "target": target,
            "features": features,
            "baseline_metrics": {
                "accuracy": float(
                    baseline_accuracy
                ),
                "f1_weighted": float(
                    baseline_f1
                ),
            },
            "model_metrics": {
                "accuracy": float(
                    accuracy
                ),
                "f1_weighted": float(
                    f1
                ),
            },
            "beats_baseline": (
                accuracy > baseline_accuracy
            ),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "leakage_warnings": [],
            "warnings": [],
            "runtime_ms": int(
                (time.perf_counter() - start)
                * 1000
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "model": model_type,
            "target": target,
            "features": features,
            "error": str(exc),
            "warnings": [],
            "runtime_ms": int(
                (time.perf_counter() - start)
                * 1000
            ),
        }


# ============================================================
# Tool 7 — save_chart
# ============================================================

@mcp.tool()
def save_chart(
    filename: str,
    content_base64: str,
) -> dict[str, Any]:
    """
    Save a generated chart artifact.

    The caller supplies base64-encoded image content.
    """

    import base64

    try:
        safe_name = Path(filename).name

        if not safe_name:
            raise ValueError(
                "Invalid chart filename."
            )

        output_path = (
            ARTIFACT_DIR / safe_name
        )

        data = base64.b64decode(
            content_base64
        )

        output_path.write_bytes(data)

        return {
            "success": True,
            "artifact_id": (
                f"chart_{uuid.uuid4().hex[:8]}"
            ),
            "path": str(
                output_path
            ),
            "filename": safe_name,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# Start MCP server
# ============================================================

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
    )