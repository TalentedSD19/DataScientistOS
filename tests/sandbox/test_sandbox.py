from backend.sandbox.runner import run_python_in_sandbox


def test_normal_python():
    result = run_python_in_sandbox(
        "print(2 + 3)"
    )

    assert result["success"] is True
    assert "5" in result["stdout"]


def test_no_network():
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


def test_no_host_file_access():
    result = run_python_in_sandbox(
        """
print(open("/etc/shadow").read())
"""
    )

    assert result["success"] is False


def test_timeout():
    result = run_python_in_sandbox(
        "while True: pass",
        timeout_seconds=3,
    )

    assert result["success"] is False
    assert result["error_type"] == "timeout"


def test_matplotlib_import():
    result = run_python_in_sandbox(
        """
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
plt.savefig("/workspace/output/test.png")
"""
    )

    assert result["success"] is True
    assert "test.png" in result["artifacts"]