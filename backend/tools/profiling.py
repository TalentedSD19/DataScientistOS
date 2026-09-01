from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from backend.tools.registry import get_dataset


def _sqlite_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def _profile_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> dict[str, Any]:
    dataframe = pd.read_sql_query(
        f'SELECT * FROM "{table_name}"',
        connection,
    )

    columns = []

    for column in dataframe.columns:
        series = dataframe[column]

        sample_values = (
            series.dropna()
            .head(5)
            .tolist()
        )

        columns.append(
            {
                "name": str(column),
                "dtype": str(series.dtype),
                "missing_count": int(series.isna().sum()),
                "missing_fraction": float(series.isna().mean()),
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": sample_values,
            }
        )

    possible_ids = []

    for column in dataframe.columns:
        name = str(column).lower()

        if (
            name == "id"
            or name.endswith("_id")
            or name == "customer_id"
        ):
            possible_ids.append(str(column))

    possible_targets = []

    for column in dataframe.columns:
        name = str(column).lower()

        if name in {
            "target",
            "label",
            "churn",
            "y",
            "outcome",
            "response",
        }:
            possible_targets.append(str(column))

    warnings = []

    duplicate_count = int(dataframe.duplicated().sum())

    if duplicate_count > 0:
        warnings.append(
            f"{duplicate_count} duplicate rows detected"
        )

    high_missing = [
        item["name"]
        for item in columns
        if item["missing_fraction"] > 0.5
    ]

    if high_missing:
        warnings.append(
            "Columns with >50% missing values: "
            + ", ".join(high_missing)
        )

    return {
        "name": table_name,
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": columns,
        "possible_ids": possible_ids,
        "possible_targets": possible_targets,
        "duplicate_rows": duplicate_count,
        "warnings": warnings,
    }


def inspect_dataset(dataset: str) -> dict[str, Any]:
    dataset_info = get_dataset(dataset)

    if dataset_info["type"] != "sqlite":
        raise ValueError(
            f"Unsupported dataset type: {dataset_info['type']}"
        )

    path = Path(dataset_info["path"])

    connection = sqlite3.connect(path)

    try:
        table_names = _sqlite_tables(connection)

        tables = [
            _profile_table(connection, table_name)
            for table_name in table_names
        ]

        return {
            "dataset": dataset_info["id"],
            "name": dataset_info["name"],
            "type": dataset_info["type"],
            "tables": tables,
        }
    finally:
        connection.close()