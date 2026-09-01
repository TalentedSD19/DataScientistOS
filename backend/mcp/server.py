from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from backend.tools.charts import save_chart as save_chart_impl
from backend.tools.ml import train_model as train_model_impl
from backend.tools.profiling import inspect_dataset as inspect_dataset_impl
from backend.tools.registry import list_datasets as list_datasets_impl
from backend.tools.sql import run_sql as run_sql_impl
from backend.tools.statistics import run_statistics as run_statistics_impl
from backend.sandbox.runner import run_python_in_sandbox


mcp = MCPServer(
    "DataScientistOS",
    instructions=(
        "Data-science analysis tools. "
        "Tools return structured results. "
        "Generated Python executes in a "
        "restricted Docker sandbox."
    ),
)


@mcp.tool()
def list_datasets() -> dict[str, Any]:
    """List datasets available to the analysis system."""
    return {
        "datasets": list_datasets_impl(),
    }


@mcp.tool()
def inspect_dataset(
    dataset: str,
) -> dict[str, Any]:
    """Inspect schema and compact dataset statistics."""
    return inspect_dataset_impl(dataset)


@mcp.tool()
def run_sql(
    dataset: str,
    query: str,
) -> dict[str, Any]:
    """Execute read-only SQL against a trusted dataset."""
    return run_sql_impl(
        dataset,
        query,
    )


@mcp.tool()
def run_statistics(
    test: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Run a supported statistical test."""
    return run_statistics_impl(
        test,
        data,
    )


@mcp.tool()
def train_model(
    dataset: str,
    target: str,
    features: list[str],
    model_type: str,
) -> dict[str, Any]:
    """Train and evaluate a small baseline ML model."""
    return train_model_impl(
        dataset,
        target,
        features,
        model_type,
    )


@mcp.tool()
def run_python(
    dataset: str | None,
    code: str,
) -> dict[str, Any]:
    """
    Execute Python in the Docker sandbox.

    The dataset argument is a trusted dataset ID,
    not an arbitrary filesystem path.
    """

    dataset_path: str | None = None

    if dataset is not None:
        from backend.tools.registry import get_dataset

        dataset_info = get_dataset(dataset)
        dataset_path = str(
            Path(dataset_info["path"]).resolve()
        )

    return run_python_in_sandbox(
        code=code,
        dataset_path=dataset_path,
    )


@mcp.tool()
def save_chart(
    chart_type: str,
    title: str,
    labels: list[str],
    values: list[float],
    filename: str,
) -> dict[str, Any]:
    """Save a simple analysis chart."""
    return save_chart_impl(
        chart_type=chart_type,
        title=title,
        labels=labels,
        values=values,
        filename=filename,
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
    )