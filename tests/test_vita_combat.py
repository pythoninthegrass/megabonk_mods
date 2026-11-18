import os
import subprocess
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "vita" / "combat"


def test_vita_combat_simulation(tmp_path):
    binary = tmp_path / "test_combat"
    subprocess.run(
        [
            os.environ.get("CC", "cc"),
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(SOURCE / "test_combat.c"),
            str(SOURCE / "combat.c"),
            "-lm",
            "-o",
            str(binary),
        ],
        check=True,
    )
    subprocess.run([binary], check=True)
