"""
Self-test for scripts/launch_game.py.
"""

import launch_game as lg
from pathlib import Path

WINE = Path("/w/Wine Devel.app/Contents/Resources/wine/bin/wine")
PREFIX = Path("/b/Steam")
GAME = PREFIX / "drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk"


def test_game_launch_argv_and_cwd() -> None:
    launch = lg.build_game_launch(WINE, PREFIX, GAME)
    assert launch.argv == [
        str(WINE),
        r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk\Megabonk.exe",
        "--melonloader.agfoffline",
    ]
    assert launch.cwd == GAME


def test_game_launch_env_is_exact() -> None:
    assert lg.build_game_launch(WINE, PREFIX, GAME).env == {
        "WINEPREFIX": "/b/Steam",
        "WINEMSYNC": "1",
        "USER": "crossover",
        "LOGNAME": "crossover",
        "SteamAppId": "3405340",
        "SteamGameId": "3405340",
        "WINEDLLOVERRIDES": "version=n,b;d3d11,d3d10core=n,b",
        "WINEDEBUG": "-all,err+seh,warn+seh,err+module,trace+loaddll",
        "MVK_CONFIG_LOG_LEVEL": "1",
        "DXVK_LOG_LEVEL": "error",
    }


def test_game_launch_logs_under_melonloader_and_steam_does_not() -> None:
    assert lg.build_game_launch(WINE, PREFIX, GAME).log == GAME / "MelonLoader" / "wine-latest.log"
    assert lg.build_steam_launch(WINE, PREFIX).log is None


def test_steam_launch_argv_starts_silent() -> None:
    launch = lg.build_steam_launch(WINE, PREFIX)
    assert launch.argv == [
        str(WINE),
        r"C:\Program Files (x86)\Steam\steam.exe",
        "-silent",
        "-no-cef-sandbox",
        "-cef-disable-gpu",
        "-cef-disable-gpu-compositing",
    ]
    assert launch.cwd is None


def test_steam_launch_env_is_exact() -> None:
    assert lg.build_steam_launch(WINE, PREFIX).env == {
        "WINEPREFIX": "/b/Steam",
        "WINEMSYNC": "1",
        "USER": "crossover",
        "LOGNAME": "crossover",
    }


def test_prefix_for_requires_a_bottle_game_dir() -> None:
    assert lg.prefix_for(GAME) == PREFIX
    try:
        lg.prefix_for(Path("/tmp/fake_game"))
    except SystemExit:
        return
    raise AssertionError("expected SystemExit")


def test_spawn_detaches_into_its_own_session() -> None:
    import subprocess

    calls = []
    original = subprocess.Popen
    subprocess.Popen = lambda *a, **k: calls.append((a, k))
    try:
        lg.spawn(lg.build_steam_launch(WINE, PREFIX))
    finally:
        subprocess.Popen = original
    ((args, kwargs),) = calls
    assert kwargs["start_new_session"] is True
    assert kwargs["stdout"] is subprocess.DEVNULL and kwargs["stderr"] is subprocess.DEVNULL
    assert kwargs["env"]["WINEPREFIX"] == "/b/Steam"
    assert "PATH" in kwargs["env"]


def test_spawn_with_a_log_starts_a_detached_watcher(tmp_path) -> None:
    import subprocess
    import sys

    log = tmp_path / "MelonLoader" / "wine-latest.log"
    log.parent.mkdir(parents=True)
    log.write_text("previous launch\n", encoding="utf-8")
    launch = lg.Launch(["wine", "Megabonk.exe"], {"WINEPREFIX": "/b/Steam"}, None, log)
    calls = []
    original = subprocess.Popen
    subprocess.Popen = lambda *a, **k: calls.append((a, k))
    try:
        lg.spawn(launch)
    finally:
        subprocess.Popen = original
    ((args, kwargs),) = calls
    assert args[0][0] == sys.executable
    assert args[0][2:] == ["watch", "--log", str(log), "--", "wine", "Megabonk.exe"]
    assert kwargs["start_new_session"] is True
    assert kwargs["env"]["WINEPREFIX"] == "/b/Steam"
    assert kwargs["stdout"] is subprocess.DEVNULL and kwargs["stderr"] is subprocess.DEVNULL
    assert (log.parent / "wine-latest.prev.log").read_text(encoding="utf-8") == "previous launch\n"


def test_watch_launch_reaps_the_game_and_appends_its_status(tmp_path) -> None:
    import subprocess

    log = tmp_path / "wine-latest.log"
    calls = []

    class FakeProc:
        def wait(self) -> int:
            return 7

    original = subprocess.Popen
    subprocess.Popen = lambda *a, **k: calls.append((a, k)) or FakeProc()
    try:
        status = lg.watch_launch(log, ["wine", "Megabonk.exe"])
    finally:
        subprocess.Popen = original
    assert status == 7
    ((args, kwargs),) = calls
    assert args[0] == ["wine", "Megabonk.exe"]
    assert kwargs["stdout"] is kwargs["stderr"]
    assert log.read_text(encoding="utf-8").endswith("wine: game process exited with status 7\n")


def test_main_watch_strips_the_separator_and_watches(tmp_path) -> None:
    log = tmp_path / "wine-latest.log"
    seen = []
    original = lg.watch_launch
    lg.watch_launch = lambda path, argv: seen.append((path, argv)) or 0
    try:
        assert lg.main(["watch", "--log", str(log), "--", "wine", "Megabonk.exe"]) == 0
    finally:
        lg.watch_launch = original
    assert seen == [(log, ["wine", "Megabonk.exe"])]


def test_main_watch_requires_a_log() -> None:
    assert lg.main(["watch", "--", "wine"]) == 2
