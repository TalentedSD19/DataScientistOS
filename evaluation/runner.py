from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DSBENCH_MANIFEST = (
    ROOT / "benchmarks" / "dsbench" / "selected_tasks.json"
)

DATASCI_BENCH_MANIFEST = (
    ROOT / "benchmarks" / "datascibench" / "selected_tasks.json"
)


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_benchmark(name: str, manifest: dict, sample: int) -> None:
    tasks = manifest.get("tasks", [])

    selected = tasks[:sample] if sample > 0 else []

    print(name)
    print(f"Tasks: {len(selected)}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DataScientistOS evaluation runner"
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Number of tasks to load. Day 1 uses 0.",
    )

    args = parser.parse_args()

    if args.sample < 0:
        raise ValueError("--sample must be >= 0")

    dsbench = load_manifest(DSBENCH_MANIFEST)
    datascibench = load_manifest(DATASCI_BENCH_MANIFEST)

    print_benchmark("DSBench", dsbench, args.sample)
    print_benchmark("DataSciBench", datascibench, args.sample)


if __name__ == "__main__":
    main()