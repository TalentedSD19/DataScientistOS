"""CLI entry point: run one DS-STAR task from the command line, or run the
5-task benchmark suite that progressively exercises EDA, ML, forecasting,
hypothesis testing, and multi-file reasoning end to end.

Usage:
    python scripts/run_task.py "your question about the data" input/data.csv [more files...]
    python scripts/run_task.py --benchmark [task_number]   # e.g. --benchmark 2

Run scripts/make_sample.py first to generate the CSVs the benchmark tasks use.
All progress is printed live by backend.runner.run as the agent works.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.runner import run_new_task

# Five tasks, in increasing order of difficulty: EDA, ML classification,
# forecasting, hypothesis testing, then multi-file root-cause analysis. #2 and
# #5 are the most likely to trigger the debugger and the planner/router loop
# rather than succeeding on the first script.
BENCHMARK_TASKS = [
    (
        "Sales EDA + business insight",
        "Analyze the sales dataset. Find the top 5 products by total sales, the "
        "most profitable region, the relationship between discount and profit, "
        "and the month with the highest sales. Create one suitable visualization "
        "for the discount-profit relationship and save it to the outputs/figures "
        "folder.",
        ["samples/sales.csv"],
    ),
    (
        "Customer churn prediction",
        "Build a machine-learning model to predict customer churn. Clean the "
        "data, handle missing values and categorical variables, split the data "
        "into train and test sets, compare Logistic Regression and Random "
        "Forest, and report accuracy, precision, recall, F1-score, and the "
        "confusion matrix. Identify the most important predictors of churn.",
        ["samples/customer_churn.csv"],
    ),
    (
        "Time-series forecasting",
        "Analyze the sales time series, identify the trend and seasonality, "
        "calculate monthly growth rates, and forecast sales for the next 6 "
        "months using an appropriate forecasting method. Plot historical versus "
        "forecasted sales and save the figure.",
        ["samples/time_series_sales.csv"],
    ),
    (
        "Statistical hypothesis testing",
        "Compare the control and treatment groups. Determine whether the "
        "treatment significantly improves conversion rate and average revenue. "
        "Perform appropriate statistical hypothesis tests, report the test "
        "statistics and p-values, calculate confidence intervals, and state "
        "whether the null hypothesis should be rejected at the 5% significance "
        "level.",
        ["samples/ab_test.csv"],
    ),
    (
        "Multi-file root-cause analysis",
        "Determine why profit declined in 2025 compared with 2024. Join the "
        "relevant datasets, identify the products, regions, and customer "
        "segments contributing most to the decline, quantify the contribution "
        "of each factor, and provide the top 5 actionable findings. Create "
        "supporting charts and save the final analysis outputs.",
        ["samples/customers.csv", "samples/orders.csv", "samples/products.csv",
         "samples/returns.csv", "samples/regions.csv"],
    ),
]


async def run_benchmark(only: int | None = None) -> None:
    """Run the benchmark tasks in order (or just one, 1-indexed, if given).
    One task failing doesn't stop the rest -- the point is to see how each
    stage of the architecture behaves, not to halt on the first bad run."""
    tasks = BENCHMARK_TASKS if only is None else [BENCHMARK_TASKS[only - 1]]

    for name, prompt, files in tasks:
        print(f"\n{'#' * 70}\n# {name}\n{'#' * 70}")
        try:
            await run_new_task(prompt, files)
        except Exception as e:
            print(f"  BENCHMARK TASK FAILED: {name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/run_task.py \"<prompt>\" [file ...]")
        print("       python scripts/run_task.py --benchmark [task_number]")
        sys.exit(1)

    if sys.argv[1] == "--benchmark":
        task_number = int(sys.argv[2]) if len(sys.argv) > 2 else None
        asyncio.run(run_benchmark(task_number))
    else:
        prompt = sys.argv[1]
        files = sys.argv[2:]
        asyncio.run(run_new_task(prompt, files))
