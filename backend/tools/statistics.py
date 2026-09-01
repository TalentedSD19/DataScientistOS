from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats


def _cohens_d(
    group_a: np.ndarray,
    group_b: np.ndarray,
) -> float:
    n1 = len(group_a)
    n2 = len(group_b)

    if n1 < 2 or n2 < 2:
        return float("nan")

    var1 = np.var(group_a, ddof=1)
    var2 = np.var(group_b, ddof=1)

    pooled_variance = (
        ((n1 - 1) * var1) +
        ((n2 - 1) * var2)
    ) / (n1 + n2 - 2)

    if pooled_variance <= 0:
        return 0.0

    pooled_std = np.sqrt(pooled_variance)

    return float(
        (np.mean(group_a) - np.mean(group_b))
        / pooled_std
    )


def run_statistics(
    test: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []

    if test == "chi_square":
        observed = np.asarray(
            data["observed"],
            dtype=float,
        )

        if observed.ndim != 2:
            raise ValueError(
                "chi_square requires a 2D observed table"
            )

        statistic, p_value, dof, expected = (
            stats.chi2_contingency(observed)
        )

        n = observed.sum()

        if n <= 0:
            effect_size = float("nan")
        else:
            effect_size = float(
                np.sqrt(statistic / n)
            )

        return {
            "test": "chi_square",
            "statistic": float(statistic),
            "p_value": float(p_value),
            "effect_size": effect_size,
            "sample_sizes": {
                "total": int(n)
            },
            "warnings": warnings,
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

        if len(group_a) < 2 or len(group_b) < 2:
            warnings.append(
                "One or both groups have fewer than 2 observations"
            )

        statistic, p_value = stats.ttest_ind(
            group_a,
            group_b,
            equal_var=False,
            nan_policy="omit",
        )

        return {
            "test": "independent_t_test",
            "statistic": float(statistic),
            "p_value": float(p_value),
            "effect_size": _cohens_d(
                group_a,
                group_b,
            ),
            "sample_sizes": {
                "group_a": int(len(group_a)),
                "group_b": int(len(group_b)),
            },
            "warnings": warnings,
        }

    if test in {"pearson", "spearman"}:
        x = np.asarray(
            data["x"],
            dtype=float,
        )

        y = np.asarray(
            data["y"],
            dtype=float,
        )

        if len(x) != len(y):
            raise ValueError(
                "x and y must have the same length"
            )

        if test == "pearson":
            result = stats.pearsonr(x, y)
        else:
            result = stats.spearmanr(x, y)

        return {
            "test": test,
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": float(result.statistic),
            "sample_sizes": {
                "n": int(len(x))
            },
            "warnings": warnings,
        }

    raise ValueError(
        f"Unsupported statistical test: {test}"
    )