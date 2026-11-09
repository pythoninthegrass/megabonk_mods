"""
Self-test for scripts/game_paths.py.
"""

import game_paths as gp
import os
from pathlib import Path


def test_default_wine_runtime_game_dir_is_in_the_megabonk_prefix_not_crossover() -> None:
    game = gp.game_dir(env_file_values={})
    assert str(game).endswith(".local/share/megabonk/wine/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    assert "CrossOver" not in str(game)


def test_default_crossover_runtime_game_dir_is_in_the_crossover_bottle() -> None:
    game = gp.game_dir(env_file_values={"MEGABONK_MACOS_RUNTIME": "crossover"})
    assert str(game).endswith("CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")


def test_wine_prefix_setting_derives_the_game_dir() -> None:
    game = gp.game_dir(env_file_values={"MEGABONK_WINE_PREFIX": "/tmp/my prefix"})
    assert str(game) == "/tmp/my prefix/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk"


def test_game_dir_override_beats_the_wine_prefix_setting() -> None:
    values = {"MEGABONK_GAME_DIR": "/tmp/fake_game", "MEGABONK_WINE_PREFIX": "/tmp/my_prefix"}
    assert str(gp.game_dir(env_file_values=values)) == "/tmp/fake_game"


def test_wine_prefix_setting_beats_the_legacy_bottle_setting() -> None:
    values = {"MEGABONK_WINE_PREFIX": "/tmp/new_prefix", "MEGABONK_BOTTLE": "/tmp/old_bottle/drive_c"}
    assert str(gp.game_dir(env_file_values=values)).startswith("/tmp/new_prefix/drive_c/")


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
    assert gp.wine_prefix(game, env_file_values={}) == Path("/b/Steam")


def test_wine_prefix_none_without_drive_c_or_setting() -> None:
    assert gp.wine_prefix(Path("/tmp/fake_game"), env_file_values={}) is None


def test_wine_prefix_setting_applies_to_a_game_dir_outside_any_prefix() -> None:
    values = {"MEGABONK_WINE_PREFIX": "/tmp/my_prefix"}
    assert gp.wine_prefix(Path("/tmp/fake_game"), env_file_values=values) == Path("/tmp/my_prefix")


def test_wine_prefix_setting_beats_a_drive_c_ancestor() -> None:
    game = Path("/b/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    values = {"MEGABONK_WINE_PREFIX": "/tmp/my_prefix"}
    assert gp.wine_prefix(game, env_file_values=values) == Path("/tmp/my_prefix")


def test_resolved_paths_report_the_wine_prefix() -> None:

    os.environ["MEGABONK_WINE_PREFIX"] = "/tmp/reported_prefix"
    try:
        assert gp.resolved_paths()["wine_prefix"] == "/tmp/reported_prefix"
    finally:
        del os.environ["MEGABONK_WINE_PREFIX"]


def test_derived_paths() -> None:
    game = Path("/tmp/fake_game")
    assert gp.bepinex_dir(game) == game / "BepInEx"
    assert gp.plugins_dir(game) == game / "BepInEx" / "plugins"
    assert gp.plugin_dir(game) == game / "BepInEx" / "plugins" / "MegabonkLevels"
    assert gp.wine_log_path(game) == game / "BepInEx" / "wine-latest.log"
    assert gp.melonloader_dir(game) == game / "MelonLoader"
    assert gp.mods_dir(game) == game / "Mods"
    assert gp.userlibs_dir(game) == game / "UserLibs"
    assert gp.latest_log_path(game) == game / "BepInEx" / "LogOutput.log"


def test_resolved_paths_report_bepinex_layout(monkeypatch) -> None:
    game = Path("/tmp/fake_game")
    monkeypatch.setenv("MEGABONK_GAME_DIR", str(game))
    paths = gp.resolved_paths()
    assert paths["bepinex_dir"] == str(game / "BepInEx")
    assert paths["plugins_dir"] == str(game / "BepInEx/plugins")
    assert paths["plugin_dir"] == str(game / "BepInEx/plugins/MegabonkLevels")
    assert paths["latest_log_path"] == str(game / "BepInEx/LogOutput.log")
    assert paths["wine_log_path"] == str(game / "BepInEx/wine-latest.log")
    assert "melonloader_dir" not in paths
    assert "mods_dir" not in paths
    assert "userlibs_dir" not in paths


def test_parse_env_file_skips_comments_and_blanks() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"
        env_path.write_text("# a comment\n\nMEGABONK_GAME_DIR=/tmp/parsed\n")
        values = gp._parse_env_file(env_path)
        assert values == {"MEGABONK_GAME_DIR": "/tmp/parsed"}
