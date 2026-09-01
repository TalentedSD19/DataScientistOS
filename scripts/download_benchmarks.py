from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external"


REPOSITORIES = {
    "dsbench": "https://github.com/LiqiangJing/DSBench.git",
    "datascibench": "https://github.com/THUDM/DataSciBench.git",
}


def run_command(command: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def clone_repo(name: str, url: str) -> None:
    destination = EXTERNAL / name

    if destination.exists():
        print(f"{name}: already exists at {destination}")
        return

    EXTERNAL.mkdir(parents=True, exist_ok=True)

    run_command(
        [
            "git",
            "clone",
            url,
            str(destination),
        ]
    )


def validate_manifest(path: Path) -> None:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    required_fields = {"benchmark", "tasks"}

    missing = required_fields - payload.keys()

    if missing:
        raise ValueError(
            f"{path} is missing required fields: {sorted(missing)}"
        )

    if not isinstance(payload["tasks"], list):
        raise ValueError(f"{path}: 'tasks' must be a list")

    print(
        f"Validated {path}: "
        f"benchmark={payload['benchmark']}, "
        f"tasks={len(payload['tasks'])}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare DataScientistOS benchmark repositories."
    )

    parser.add_argument(
        "--clone",
        action="store_true",
        help="Clone the official DSBench and DataSciBench repositories.",
    )

    args = parser.parse_args()

    dsbench_manifest = (
        ROOT / "benchmarks" / "dsbench" / "selected_tasks.json"
    )

    datascibench_manifest = (
        ROOT / "benchmarks" / "datascibench" / "selected_tasks.json"
    )

    validate_manifest(dsbench_manifest)
    validate_manifest(datascibench_manifest)

    if args.clone:
        for name, url in REPOSITORIES.items():
            clone_repo(name, url)

        print()
        print("Benchmark repositories cloned.")
        print()
        print(
            "Next step: follow each benchmark's official "
            "data/evaluation instructions before selecting tasks."
        )
    else:
        print()
        print("No repositories cloned.")
        print("Run with --clone when ready.")


if __name__ == "__main__":
    main()