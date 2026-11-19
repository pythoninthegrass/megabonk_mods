import os
import subprocess
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "vita" / "combat"


def test_benchmark_summary(tmp_path):
    executable = tmp_path / "test_benchmark"
    subprocess.run(
        [
            os.environ.get("CC", "cc"),
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(SOURCE / "test_benchmark.c"),
            str(SOURCE / "benchmark.c"),
            "-o",
            str(executable),
        ],
        check=True,
    )
    subprocess.run([executable], check=True)
