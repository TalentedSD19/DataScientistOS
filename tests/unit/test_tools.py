import pytest

from backend.tools.charts import save_chart
from backend.tools.profiling import inspect_dataset
from backend.tools.sql import run_sql
from backend.tools.statistics import run_statistics


def test_inspect_dataset():
    result = inspect_dataset("dataset_001")

    assert result["dataset"] == "dataset_001"
    assert len(result["tables"]) == 1
    assert result["tables"][0]["name"] == "customers"


def test_run_sql():
    result = run_sql(
        "dataset_001",
        """
        SELECT segment, COUNT(*) AS count
        FROM customers
        GROUP BY segment
        ORDER BY segment
        """,
    )

    assert result["success"] is True
    assert "segment" in result["columns"]
    assert result["row_count"] == 3


def test_sql_rejects_write():
    with pytest.raises(ValueError):
        run_sql(
            "dataset_001",
            "DROP TABLE customers",
        )


def test_chi_square():
    result = run_statistics(
        "chi_square",
        {
            "observed": [
                [10, 5],
                [3, 12],
            ]
        },
    )

    assert result["test"] == "chi_square"
    assert "statistic" in result
    assert "p_value" in result


def test_save_chart():
    result = save_chart(
        chart_type="bar",
        title="Test",
        labels=["A", "B"],
        values=[1.0, 2.0],
        filename="unit_test.png",
    )

    assert result["success"] is True