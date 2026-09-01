from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_project_imports() -> None:
    import fastapi
    import langgraph
    import langchain
    import mcp
    import pandas
    import numpy
    import pytest

    assert fastapi is not None
    assert langgraph is not None
    assert langchain is not None
    assert mcp is not None
    assert pandas is not None
    assert numpy is not None
    assert pytest is not None


def test_dsbench_manifest() -> None:
    path = ROOT / "benchmarks" / "dsbench" / "selected_tasks.json"

    payload = load_json(path)

    assert payload["benchmark"] == "dsbench"
    assert isinstance(payload["tasks"], list)


def test_datascibench_manifest() -> None:
    path = (
        ROOT
        / "benchmarks"
        / "datascibench"
        / "selected_tasks.json"
    )

    payload = load_json(path)

    assert payload["benchmark"] == "datascibench"
    assert isinstance(payload["tasks"], list)