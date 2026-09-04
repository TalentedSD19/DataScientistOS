from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SANDBOX_IMAGE = "datascientistos-sandbox:day2"


def run_python_in_sandbox(
    code: str,
    dataset_path: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """
    Execute generated Python inside a disposable, locked-down
    Docker container.

    No network, limited CPU/RAM/PIDs, read-only root filesystem
    and read-only input data. Only /workspace/output is writable,
    and it is deleted along with the rest of the job directory
    once artifacts have been collected.
    """

    run_id = uuid.uuid4().hex[:12]

    job_dir = Path(
        tempfile.mkdtemp(
            prefix=f"dsos_{run_id}_"
        )
    )

    output_dir = job_dir / "output"
    input_dir = job_dir / "input"

    output_dir.mkdir()
    input_dir.mkdir()

    code_path = job_dir / "main.py"
    code_path.write_text(
        code,
        encoding="utf-8",
    )

    try:
        if dataset_path is not None:
            source = Path(dataset_path)

            if not source.exists():
                raise FileNotFoundError(
                    f"Dataset does not exist: {source}"
                )

            shutil.copy2(
                source,
                input_dir / source.name,
            )

        container_name = (
            f"dsos-sandbox-{run_id}"
        )

        command = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            "2g",
            "--memory-swap",
            "2g",
            "--cpus",
            "1.5",
            "--pids-limit",
            "128",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=512m",
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "ALL",
            "--env",
            "MPLCONFIGDIR=/tmp/mpl",
            "-v",
            f"{code_path.resolve()}:/workspace/main.py:ro",
            "-v",
            f"{input_dir.resolve()}:/workspace/input:ro",
            "-v",
            f"{output_dir.resolve()}:/workspace/output:rw",
            "-w",
            "/workspace",
            SANDBOX_IMAGE,
            "python",
            "/workspace/main.py",
        ]

        started = time.perf_counter()

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        runtime_ms = round(
            (time.perf_counter() - started)
            * 1000,
            2,
        )

        artifacts = [
            str(path.relative_to(output_dir))
            for path in output_dir.rglob("*")
            if path.is_file()
        ]

        return {
            "success": completed.returncode == 0,
            "run_id": run_id,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "artifacts": artifacts,
            "runtime_ms": runtime_ms,
            "return_code": completed.returncode,
        }

    except subprocess.TimeoutExpired as exc:
        subprocess.run(
            [
                "docker",
                "rm",
                "-f",
                f"dsos-sandbox-{run_id}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        return {
            "success": False,
            "run_id": run_id,
            "stdout": (
                exc.stdout
                if isinstance(exc.stdout, str)
                else ""
            ),
            "stderr": (
                exc.stderr
                if isinstance(exc.stderr, str)
                else ""
            ),
            "artifacts": [],
            "runtime_ms": (
                timeout_seconds * 1000
            ),
            "return_code": None,
            "error_type": "timeout",
        }

    finally:
        shutil.rmtree(
            job_dir,
            ignore_errors=True,
        )
