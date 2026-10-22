"""
Self-test for scripts/game_paths.py.
"""

import game_paths as gp
from pathlib import Path


def test_default_macos_bottle_path_when_nothing_set() -> None:
    game = gp.game_dir(env_file_values={})
    assert str(game).endswith("CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")


def test_env_file_bottle_override() -> None:
    game = gp.game_dir(env_file_values={"MEGABONK_BOTTLE": "/tmp/fake_bottle"})
    assert str(game) == "/tmp/fake_bottle/Program Files (x86)/Steam/steamapps/common/Megabonk"


def test_env_file_game_dir_override() -> None:
    game = gp.game_dir(env_file_values={"MEGABONK_GAME_DIR": "/tmp/fake_game"})
    assert str(game) == "/tmp/fake_game"


def test_process_env_takes_precedence_over_env_file(monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_GAME_DIR", "/tmp/from_process_env")
    game = gp.game_dir(env_file_values={"MEGABONK_GAME_DIR": "/tmp/from_env_file"})
    assert str(game) == "/tmp/from_process_env"


def test_macos_runtime_defaults_to_wine() -> None:
    assert gp.macos_runtime(env_file_values={}) == "wine"


def test_macos_runtime_reads_env_file_and_process_env() -> None:
    import os

    assert gp.macos_runtime(env_file_values={"MEGABONK_MACOS_RUNTIME": "crossover"}) == "crossover"
    os.environ["MEGABONK_MACOS_RUNTIME"] = "wine"
    try:
        assert gp.macos_runtime(env_file_values={"MEGABONK_MACOS_RUNTIME": "crossover"}) == "wine"
    finally:
        del os.environ["MEGABONK_MACOS_RUNTIME"]


def test_macos_runtime_rejects_unknown_value() -> None:
    try:
        gp.macos_runtime(env_file_values={"MEGABONK_MACOS_RUNTIME": "proton"})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_wine_bin_default_and_override() -> None:
    default = gp.wine_bin(env_file_values={})
    assert str(default).endswith("Applications/wine11/Wine Devel.app/Contents/Resources/wine/bin/wine")
    assert gp.wine_bin(env_file_values={"MEGABONK_WINE": "/opt/wine/bin/wine"}) == Path("/opt/wine/bin/wine")


def test_wine_prefix_is_parent_of_drive_c() -> None:
    game = Path("/b/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    assert gp.wine_prefix(game) == Path("/b/Steam")


def test_wine_prefix_none_without_drive_c() -> None:
    assert gp.wine_prefix(Path("/tmp/fake_game")) is None


def test_derived_paths() -> None:
    game = Path("/tmp/fake_game")
    assert gp.melonloader_dir(game) == game / "MelonLoader"
    assert gp.mods_dir(game) == game / "Mods"
    assert gp.userlibs_dir(game) == game / "UserLibs"
    assert gp.latest_log_path(game) == game / "MelonLoader" / "Latest.log"


def test_parse_env_file_skips_comments_and_blanks() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"
        env_path.write_text("# a comment\n\nMEGABONK_GAME_DIR=/tmp/parsed\n")
        values = gp._parse_env_file(env_path)
        assert values == {"MEGABONK_GAME_DIR": "/tmp/parsed"}
