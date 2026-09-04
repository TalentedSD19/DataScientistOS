from __future__ import annotations

from backend.sandbox.runner import run_python_in_sandbox


def test_normal_python() -> None:
    result = run_python_in_sandbox(
        "print(2 + 3)"
    )

    assert result["success"] is True
    assert "5" in result["stdout"]


def test_no_network() -> None:
    result = run_python_in_sandbox(
        """
import urllib.request
urllib.request.urlopen(
    "http://example.com",
    timeout=3
)
"""
    )

    assert result["success"] is False


def test_no_host_file_access() -> None:
    result = run_python_in_sandbox(
        """
print(open("/etc/shadow").read())
"""
    )

    assert result["success"] is False


def test_timeout() -> None:
    result = run_python_in_sandbox(
        "while True: pass",
        timeout_seconds=5,
    )

    assert result["success"] is False
    assert result["error_type"] == "timeout"


def test_memory_limit() -> None:
    result = run_python_in_sandbox(
        "x = bytearray(10 ** 10)",
        timeout_seconds=30,
    )

    assert result["success"] is False


def test_input_is_read_only() -> None:
    result = run_python_in_sandbox(
        """
try:
    open("/workspace/input/blocked.txt", "w").write("nope")
    print("WROTE")
except OSError:
    print("BLOCKED")
""",
        dataset_path=None,
    )

    assert result["success"] is True
    assert "BLOCKED" in result["stdout"]
    assert "WROTE" not in result["stdout"]


def test_matplotlib_import() -> None:
    result = run_python_in_sandbox(
        """
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
plt.savefig("/workspace/output/test.png")
"""
    )

    assert result["success"] is True
    assert "test.png" in result["artifacts"]


def test_xgboost_import() -> None:
    result = run_python_in_sandbox(
        """
import xgboost
print(xgboost.__version__)
"""
    )

    assert result["success"] is True
    assert result["stdout"].strip() != ""
