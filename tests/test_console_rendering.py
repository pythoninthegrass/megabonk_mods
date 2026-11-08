"""Guard TMP wiring that the Unity-free C# tests cannot execute."""

import pytest
from pathlib import Path


@pytest.mark.parametrize("label", ["_scrollLabels[i]", "label"])
def test_console_disables_tmp_backslash_control_parsing(label: str) -> None:
    source = (Path(__file__).resolve().parents[1] / "src/MegabonkLevels.Mod/console_overlay.cs").read_text()
    build = source.split("private static void Build()", 1)[1].split("private static void RestorePersistedLog()", 1)[0]

    assert f"{label}.parseCtrlCharacters = false;" in build, (
        r"TMP defaults to interpreting \t and \n, corrupting Windows paths in console replies"
    )
