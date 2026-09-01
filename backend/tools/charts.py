from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"


def save_chart(
    chart_type: str,
    title: str,
    labels: list[str],
    values: list[float],
    filename: str,
) -> dict[str, Any]:
    ARTIFACT_DIR.mkdir(exist_ok=True)

    if Path(filename).name != filename:
        raise ValueError(
            "filename must be a simple filename"
        )

    output_path = ARTIFACT_DIR / filename

    if chart_type == "bar":
        plt.figure(figsize=(8, 5))
        plt.bar(labels, values)
        plt.title(title)
        plt.tight_layout()

    elif chart_type == "line":
        plt.figure(figsize=(8, 5))
        plt.plot(labels, values)
        plt.title(title)
        plt.tight_layout()

    else:
        raise ValueError(
            "Supported chart types: bar, line"
        )

    plt.savefig(output_path, dpi=150)
    plt.close()

    return {
        "success": True,
        "artifact_path": str(output_path),
        "chart_type": chart_type,
    }