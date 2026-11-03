"""
Self-test for scripts/player_installer/cli.py.

Covers the exit codes and reporting a player sees: a clean install, a no-op
re-run, a repair, the native-build steering, a missing install, level and pack
inputs, uninstall, and headless versus desktop progress.
"""

import hashlib
import json
import player_installer.cli as cli
import player_installer.content as content
import player_installer.plan as plan
import player_installer.proton as proton
import pytest
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

APP_ID = "3405340"


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    (package / "vendor").mkdir(parents=True)
    (package / "mod").mkdir(parents=True)
    with zipfile.ZipFile(package / "vendor" / "MelonLoader.x64.zip", "w") as zf:
        zf.writestr("version.dll", "MZ")
        zf.writestr("MelonLoader/net6/MelonLoader.dll", "MZ")
    with zipfile.ZipFile(package / "vendor" / "dotnet-runtime-6.0.36-win-x64.zip", "w") as zf:
        zf.writestr("dotnet.exe", "MZ")
        zf.writestr("host/fxr/6.0.36/hostfxr.dll", "MZ")
        zf.writestr("shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "MZ")
    (package / "mod" / "MegabonkLevels.Mod.dll").write_bytes(b"dll")
    (package / "mod" / "MegabonkLevels.Mod.pdb").write_bytes(b"pdb")
    (package / "mod" / "NLayer.dll").write_bytes(b"nl")
    loader_bytes = (package / "vendor" / "MelonLoader.x64.zip").read_bytes()
    runtime_bytes = (package / "vendor" / "dotnet-runtime-6.0.36-win-x64.zip").read_bytes()
    digest = lambda data: hashlib.sha256(data).hexdigest()  # noqa: E731
    doc = {
        "schema": "megabonk-player-package/1",
        "platform": "linux",
        "package_id": "megabonk-levels-0.0.1-ml0.7.3-linux",
        "mod_version": "0.0.1",
        "melonloader_version": "0.7.3",
        "game_buildid": "21750826",
        "generated": "2026-10-31T03:30:00Z",
        "verified_on": [],
        "vendors": [
            {"name": "MelonLoader.x64.zip", "url": "u", "sha256": digest(loader_bytes), "kind": "melonloader", "version": "0.7.3"},
            {"name": "dotnet-runtime-6.0.36-win-x64.zip", "url": "u", "sha256": digest(runtime_bytes), "kind": "dotnet", "version": "6.0.36"},
        ],
        "files": [
            {"path": "mod/MegabonkLevels.Mod.dll", "sha256": digest(b"dll"), "dest": "Mods/MegabonkLevels.Mod.dll"},
            {"path": "mod/MegabonkLevels.Mod.pdb", "sha256": digest(b"pdb"), "dest": "Mods/MegabonkLevels.Mod.pdb"},
            {"path": "mod/NLayer.dll", "sha256": digest(b"nl"), "dest": "Mods/NLayer.dll"},
            {"path": "mod/NLayer.dll", "sha256": digest(b"nl"), "dest": "UserLibs/NLayer.dll"},
        ],
    }
    (package / "manifest.json").write_text(json.dumps(doc))
    return package


def _install_tree(tmp_path: Path, *, windows_build: bool = True) -> tuple[Path, Path]:
    home = tmp_path / "home"
    client = home / ".local" / "share" / "Steam"
    (client / "steamapps").mkdir(parents=True)
    (client / "config").mkdir(parents=True)
    library = tmp_path / "media" / "sdcard" / "SteamLibrary"
    game = library / "steamapps" / "common" / "Megabonk"
    (game / "Megabonk_Data").mkdir(parents=True)
    if windows_build:
        (game / "Megabonk.exe").write_bytes(b"MZ")
    else:
        (game / "Megabonk.x86_64").write_bytes(b"\x7fELF")
    (library / "steamapps" / "compatdata" / APP_ID / "pfx" / "drive_c").mkdir(parents=True)
    body = '\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % library
    (client / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body)
    return home, game


@pytest.fixture
def package(tmp_path: Path) -> Path:
    return _package(tmp_path)


@pytest.fixture(autouse=True)
def no_host_steam_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keeps discovery away from the real machine's /media mounts and Flatpak grants."""
    monkeypatch.setattr(cli, "MOUNT_ROOTS", ())
    monkeypatch.setattr(cli.steam, "flatpak_probe", lambda home_value: cli.steam.FlatpakProbe((), "file", True))


def _run(argv: list[str]):
    return cli.main(argv)


def test_install_from_a_wiped_install_leaves_the_mod_in_place(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"])
    assert code == cli.EXIT_OK
    assert (game / "MelonLoader" / "net6" / "MelonLoader.dll").is_file()
    assert (game / "Mods" / "MegabonkLevels.Mod.dll").read_bytes() == b"dll"
    assert (game / "UserData" / "Levels").is_dir()
    out = capsys.readouterr().out
    assert "MegabonkLevels.Mod.dll" in out and "Latest.log" in out


def test_a_second_run_reports_nothing_to_do(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    argv = ["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"]
    assert _run(argv) == cli.EXIT_OK
    capsys.readouterr()
    assert _run(argv) == cli.EXIT_OK
    assert "already" in capsys.readouterr().out.lower()


def test_check_reports_drift_without_changing_anything(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    argv = ["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"]
    assert _run(argv) == cli.EXIT_OK
    (game / "Mods" / "NLayer.dll").unlink()
    capsys.readouterr()
    assert _run([*argv, "--check"]) == cli.EXIT_OUT_OF_DATE
    assert "NLayer.dll" in capsys.readouterr().out
    assert _run([*argv, "--check", "--json"]) == cli.EXIT_OUT_OF_DATE


def test_check_on_a_complete_install_is_zero(tmp_path: Path, package: Path) -> None:
    home, game = _install_tree(tmp_path)
    argv = ["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"]
    assert _run(argv) == cli.EXIT_OK
    assert _run([*argv, "--check"]) == cli.EXIT_OK


def test_repair_restores_only_what_is_missing(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    argv = ["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"]
    _run(argv)
    (game / "MelonLoader" / "net6" / "MelonLoader.dll").write_bytes(b"keep me")
    (game / "Mods" / "MegabonkLevels.Mod.dll").unlink()
    capsys.readouterr()
    assert _run(argv) == cli.EXIT_OK
    assert (game / "MelonLoader" / "net6" / "MelonLoader.dll").read_bytes() == b"keep me"
    assert (game / "Mods" / "MegabonkLevels.Mod.dll").read_bytes() == b"dll"


def test_dry_run_writes_nothing(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--dry-run"])
    assert code == cli.EXIT_OK
    assert not (game / "MelonLoader").exists()
    assert "MelonLoader" in capsys.readouterr().out


def test_the_native_build_is_refused_with_an_explanation(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path, windows_build=False)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui"])
    assert code == cli.EXIT_UNSUPPORTED_BUILD
    err = capsys.readouterr().err
    assert "Megabonk.x86_64" in err and "Steam Play" in err
    assert not (game / "MelonLoader").exists()


def test_a_missing_install_exits_with_a_tell_what_to_do(tmp_path: Path, package: Path, capsys) -> None:
    home = tmp_path / "home"
    (home / ".local" / "share" / "Steam" / "steamapps").mkdir(parents=True)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui"])
    assert code == cli.EXIT_NOT_FOUND
    assert "--game-dir" in capsys.readouterr().err


def _library_home(
    tmp_path: Path,
    *,
    libraries: int = 2,
    decoy: str | None = "1000xRESIST",
    megabonk: bool = True,
) -> SimpleNamespace:
    """A native client whose first library holds only an unrelated Il2Cpp game, the next one Megabonk.

    The last library is removable media: the layout where Steam's active prefix lives in a
    different library from the game files.
    """
    home = tmp_path / "home"
    client = home / ".local" / "share" / "Steam"
    (client / "steamapps").mkdir(parents=True)
    (client / "config").mkdir(parents=True)
    roots = [tmp_path / f"library-{index}" for index in range(libraries)]
    roots[-1] = tmp_path / "media" / "sdcard" / "SteamLibrary"
    for library in roots:
        (library / "steamapps" / "common").mkdir(parents=True)
    for name in filter(None, [decoy, None if megabonk else "SuperTune"]):
        other = roots[0] / "steamapps" / "common" / name
        (other / f"{name}_Data").mkdir(parents=True)
        (other / "GameAssembly.dll").write_bytes(b"MZ")
        (other / "UnityPlayer.dll").write_bytes(b"MZ")
    game = roots[-1] / "steamapps" / "common" / "Megabonk"
    if megabonk:
        (game / "Megabonk_Data").mkdir(parents=True)
        (game / "Megabonk.exe").write_bytes(b"MZ")
    body = "".join('\t"%d"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % (i, path) for i, path in enumerate(roots))
    (client / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body)
    return SimpleNamespace(home=home, game=game, decoy_library=roots[0], libraries=roots)


def _prefix_in(library: Path) -> Path:
    prefix = library / "steamapps" / "compatdata" / APP_ID / "pfx"
    (prefix / "drive_c").mkdir(parents=True)
    return prefix


def test_discovery_ignores_an_unrelated_il2cpp_game_in_an_earlier_library(tmp_path: Path, package: Path) -> None:
    found = _library_home(tmp_path)
    code = _run(["--home", str(found.home), "--package", str(package), "--no-gui", "--wine-override", "off"])
    assert code == cli.EXIT_OK
    assert (found.game / "Mods" / "MegabonkLevels.Mod.dll").read_bytes() == b"dll"
    assert not (found.decoy_library / "steamapps" / "common" / "1000xRESIST" / "Mods").exists()


def test_a_library_with_only_another_il2cpp_game_names_the_decoy_it_rejected(tmp_path: Path, package: Path, capsys) -> None:
    found = _library_home(tmp_path, megabonk=False)
    code = _run(["--home", str(found.home), "--package", str(package), "--no-gui"])
    assert code == cli.EXIT_NOT_FOUND
    err = capsys.readouterr().err
    decoy = found.decoy_library / "steamapps" / "common" / "1000xRESIST"
    assert str(decoy) in err
    assert "GameAssembly.dll" in err and "Megabonk_Data" in err
    assert "--game-dir" in err


def test_the_prefix_from_another_library_is_reported(tmp_path: Path, capsys) -> None:
    """The SD-card layout: the game is on removable media, Steam's active prefix is in the home library."""
    found = _library_home(tmp_path)
    active = _prefix_in(found.libraries[0])
    game_dir, prefix, _searched = cli.find_install(found.home, [], cli.Reporter())
    assert game_dir == found.game
    assert prefix == active
    out = capsys.readouterr().out
    assert f"Proton prefix: {active}" in out
    assert "not beside the game" in out


def test_two_usable_prefixes_in_other_libraries_are_listed_rather_than_guessed(tmp_path: Path, capsys) -> None:
    found = _library_home(tmp_path, libraries=3)
    first = _prefix_in(found.libraries[0])
    third = _prefix_in(found.libraries[1])
    _game_dir, prefix, _searched = cli.find_install(found.home, [], cli.Reporter())
    assert prefix is None
    err = capsys.readouterr().err
    assert "pass --prefix" in err
    assert str(first) in err and str(third) in err


def test_an_explicit_prefix_makes_the_ambiguity_warning_go_away(tmp_path: Path, package: Path, capsys) -> None:
    found = _library_home(tmp_path, libraries=3)
    _prefix_in(found.libraries[0])
    chosen = _prefix_in(found.libraries[1])
    code = _run(
        ["--home", str(found.home), "--package", str(package), "--prefix", str(chosen), "--dry-run", "--no-gui"]
    )
    assert code == cli.EXIT_OK
    err = capsys.readouterr().err
    assert "more than one usable Proton prefix" not in err
    assert "not beside the game" not in capsys.readouterr().out


def test_a_granted_flatpak_library_is_searched_without_a_client_at_a_default_path(tmp_path: Path, monkeypatch, capsys) -> None:
    home = tmp_path / "home"
    home.mkdir()
    library = tmp_path / "media" / "steam"
    game = library / "steamapps" / "common" / "Megabonk"
    game.mkdir(parents=True)
    (game / "Megabonk.exe").write_bytes(b"MZ")
    (library / "config").mkdir()
    monkeypatch.setattr(cli, "MOUNT_ROOTS", ())
    monkeypatch.setattr(cli.steam, "flatpak_probe", lambda home_value: cli.steam.FlatpakProbe((library,), "file", True))
    game_dir, prefix, searched = cli.find_install(home, [], cli.Reporter())
    assert game_dir == game
    assert searched == [str(library)]
    assert "Flatpak Steam may only read" in capsys.readouterr().out


def test_an_explicit_game_dir_bypasses_discovery(tmp_path: Path, package: Path) -> None:
    game = tmp_path / "somewhere" / "Megabonk"
    game.mkdir(parents=True)
    (game / "Megabonk.exe").write_bytes(b"MZ")
    code = _run(["--game-dir", str(game), "--package", str(package), "--no-gui", "--wine-override", "off"])
    assert code == cli.EXIT_OK
    assert (game / "Mods" / "NLayer.dll").read_bytes() == b"nl"


def test_the_game_dir_runtime_mode_prints_the_launch_option_to_paste(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off", "--dotnet-in", "gamedir"])
    assert code == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "DOTNET_ROOT=Z:\\" in out and "%command%" in out
    assert (game / content.RUNTIME_SUBDIR / "host" / "fxr" / "6.0.36" / "hostfxr.dll").is_file()


def test_the_dll_override_is_applied_into_the_prefix(tmp_path: Path, package: Path) -> None:
    home, game = _install_tree(tmp_path)
    prefix = game.parents[1] / "compatdata" / APP_ID / "pfx"
    code = _run(["--home", str(home), "--package", str(package), "--no-gui"])
    assert code == cli.EXIT_OK
    assert proton.read_dll_override(prefix, "version") == "native,builtin"


def test_a_level_file_lands_in_user_data_levels(tmp_path: Path, package: Path) -> None:
    home, game = _install_tree(tmp_path)
    level = tmp_path / "warehouse.mblevel.json"
    level.write_text('{"schema":2}')
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off", "--level", str(level)])
    assert code == cli.EXIT_OK
    assert (game / "UserData" / "Levels" / "warehouse.mblevel.json").read_text() == '{"schema":2}'


def test_a_missing_level_file_is_an_actionable_error(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--level", str(tmp_path / "gone.mblevel.json")])
    assert code == cli.EXIT_ERROR
    assert "gone.mblevel.json" in capsys.readouterr().err


def test_a_pack_lands_in_level_packs(tmp_path: Path, package: Path) -> None:
    home, game = _install_tree(tmp_path)
    source = tmp_path / "thps"
    source.mkdir()
    (source / "thps").write_bytes(b"bundle")
    (source / "manifest.json").write_text(json.dumps({"id": "thps", "name": "THPS", "author": "l", "version": "1", "assets": ["a"]}))
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off", "--pack", str(source)])
    assert code == cli.EXIT_OK
    assert (game / "UserData" / "LevelPacks" / "thps" / "thps").read_bytes() == b"bundle"


def test_an_invalid_pack_is_an_actionable_error(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    source = tmp_path / "broken"
    source.mkdir()
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--pack", str(source)])
    assert code == cli.EXIT_ERROR
    assert "manifest.json" in capsys.readouterr().err


def test_uninstall_restores_a_vanilla_game(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    prefix = game.parents[1] / "compatdata" / APP_ID / "pfx"
    argv = ["--home", str(home), "--package", str(package), "--no-gui"]
    _run(argv)
    assert (game / "MelonLoader").is_dir()
    capsys.readouterr()
    assert _run([*argv, "--uninstall"]) == cli.EXIT_OK
    assert not (game / "MelonLoader").exists()
    assert not (game / "version.dll").exists()
    assert not (game / "Mods").exists()
    assert not proton.runtime_installed(proton.runtime_target(prefix), "6.0.36")
    assert proton.read_dll_override(prefix, "version") is None
    assert (game / "Megabonk.exe").is_file() and (game / "Megabonk_Data").is_dir()


def test_a_corrupt_package_fails_before_touching_the_game(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    (package / "mod" / "MegabonkLevels.Mod.dll").write_bytes(b"corrupted")
    code = _run(["--home", str(home), "--package", str(package), "--no-gui"])
    assert code == cli.EXIT_ERROR
    assert "checksum" in capsys.readouterr().err.lower() or "MegabonkLevels.Mod.dll" in capsys.readouterr().err
    assert not (game / "Mods").exists()


def test_a_package_without_a_manifest_is_reported(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    (package / "manifest.json").unlink()
    assert _run(["--home", str(home), "--package", str(package), "--no-gui"]) == cli.EXIT_ERROR
    assert "manifest.json" in capsys.readouterr().err


def test_json_output_describes_the_plan(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree(tmp_path)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--dry-run", "--json"])
    assert code == cli.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["game_dir"] == str(game)
    assert payload["build"] == "windows"
    assert any(a["kind"] == "install-loader" for a in payload["actions"])


def test_progress_goes_to_the_gui_in_a_desktop_session(tmp_path: Path, package: Path, monkeypatch) -> None:
    home, game = _install_tree(tmp_path)
    started: list[int] = []

    class Recording:
        binary = "/usr/bin/zenity"

        def start(self, total, label):
            started.append(total)

        def step(self, label):
            pass

        def finish(self, message, ok=True):
            pass

    monkeypatch.setattr(cli.ui, "pick_progress", lambda env, **kw: Recording())
    monkeypatch.setenv("DISPLAY", ":0")
    assert cli.main(["--home", str(home), "--package", str(package)]) == cli.EXIT_OK
    assert started and started[0] > 0


@pytest.mark.parametrize("flag", ["--non-interactive", "--no-gui", "--json"])
def test_plain_text_flags_cover_install_and_uninstall(tmp_path: Path, package: Path, monkeypatch, flag) -> None:
    home, game = _install_tree(tmp_path)
    forced = []

    def pick(env, **kwargs):
        forced.append(kwargs.get("force_text", False))
        return cli.ui.TextProgress(writer=lambda line: None)

    monkeypatch.setattr(cli.ui, "pick_progress", pick)
    argv = ["--home", str(home), "--package", str(package), "--wine-override", "off", flag]
    assert cli.main(argv) == cli.EXIT_OK
    assert cli.main([*argv, "--uninstall"]) == cli.EXIT_OK
    assert forced == [True, True]


def test_non_interactive_environment_covers_install_and_uninstall(tmp_path: Path, package: Path, monkeypatch, capsys) -> None:
    home, game = _install_tree(tmp_path)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("MEGABONK_NON_INTERACTIVE", "1")
    monkeypatch.setattr(cli.ui, "has_tty", lambda: True)

    def no_dialog(*args, **kwargs):
        pytest.fail("non-interactive run looked for a dialog")

    monkeypatch.setattr(cli.ui, "find_dialog_binary", no_dialog)
    argv = ["--home", str(home), "--package", str(package), "--wine-override", "off"]
    assert cli.main(argv) == cli.EXIT_OK
    assert "1/" in capsys.readouterr().out
    assert cli.main([*argv, "--uninstall"]) == cli.EXIT_OK
    assert "removed" in capsys.readouterr().out


def _install_tree_without_prefix(tmp_path: Path) -> tuple[Path, Path]:
    home, game = _install_tree(tmp_path)
    shutil.rmtree(game.parents[1] / "compatdata")
    return home, game


def test_a_missing_install_names_every_candidate_and_the_retry_flag(tmp_path: Path, package: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(cli, "MOUNT_ROOTS", ())
    home = tmp_path / "home"
    client = home / ".local" / "share" / "Steam"
    (client / "steamapps").mkdir(parents=True)
    (client / "config").mkdir(parents=True)
    searched = tmp_path / "lib-empty"
    (searched / "steamapps" / "common").mkdir(parents=True)
    stale = tmp_path / "mnt" / "games" / "SteamLibrary"
    body = "".join('\t"%d"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % (i, p) for i, p in enumerate([searched, stale]))
    (client / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui"])
    assert code == cli.EXIT_NOT_FOUND
    err = capsys.readouterr().err
    assert str(client) in err and "found" in err
    assert str(home / ".steam" / "root") in err and "does not exist" in err
    assert "Libraries searched:" in err and str(searched) in err
    assert "Libraries skipped:" in err and str(stale) in err
    assert "drive not attached" in err
    assert f"--library {stale}" in err
    assert "--game-dir" in err


def test_a_missing_prefix_names_the_prefix_flag_and_how_to_create_one(tmp_path: Path, package: Path, capsys) -> None:
    home, game = _install_tree_without_prefix(tmp_path)
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"])
    assert code == cli.EXIT_OK
    err = capsys.readouterr().err
    assert "--prefix" in err
    assert "launch Megabonk once in Steam under Proton" in err
    assert (game / content.RUNTIME_SUBDIR / "host" / "fxr" / "6.0.36" / "hostfxr.dll").is_file()


def test_a_desktop_without_a_dialog_backend_prints_how_to_get_one(tmp_path: Path, package: Path, monkeypatch, capsys) -> None:
    home, game = _install_tree(tmp_path)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(cli.ui, "has_tty", lambda: True)
    monkeypatch.setattr(cli.ui, "find_dialog_binary", lambda *args, **kwargs: None)
    code = _run(["--home", str(home), "--package", str(package), "--wine-override", "off"])
    assert code == cli.EXIT_OK
    err = capsys.readouterr().err
    assert "zenity" in err and "--no-gui" in err


def test_a_flatpak_client_without_the_flatpak_cli_prints_the_library_hint(tmp_path: Path, package: Path, monkeypatch, capsys) -> None:
    home = tmp_path / "home"
    flatpak = home / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam"
    library = tmp_path / "media" / "steam"
    game = library / "steamapps" / "common" / "Megabonk"
    (game / "Megabonk_Data").mkdir(parents=True)
    (game / "Megabonk.exe").write_bytes(b"MZ")
    (flatpak / "steamapps").mkdir(parents=True)
    (flatpak / "config").mkdir(parents=True)
    body = '\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % library
    (flatpak / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body)
    monkeypatch.setattr(cli.steam, "flatpak_probe", lambda home_value: cli.steam.FlatpakProbe((), "none", False))
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"])
    assert code == cli.EXIT_OK
    err = capsys.readouterr().err
    assert "flatpak" in err.lower() and "--library" in err


def test_a_flatpak_library_the_sandbox_cannot_read_names_the_grant_command(tmp_path: Path, package: Path, monkeypatch, capsys) -> None:
    home = tmp_path / "home"
    flatpak = home / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam"
    library = tmp_path / "media" / "steam"
    game = library / "steamapps" / "common" / "Megabonk"
    (game / "Megabonk_Data").mkdir(parents=True)
    (game / "Megabonk.exe").write_bytes(b"MZ")
    (flatpak / "steamapps").mkdir(parents=True)
    (flatpak / "config").mkdir(parents=True)
    body = '\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % library
    (flatpak / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body)
    monkeypatch.setattr(cli.steam, "flatpak_probe", lambda home_value: cli.steam.FlatpakProbe((), "none", True))
    code = _run(["--home", str(home), "--package", str(package), "--no-gui", "--wine-override", "off"])
    assert code == cli.EXIT_OK
    err = capsys.readouterr().err
    assert f"flatpak override --user --filesystem={library} com.valvesoftware.Steam" in err
