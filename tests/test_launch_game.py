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
    assert launch.argv == [str(WINE), r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk\Megabonk.exe"]
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
        "WINEDEBUG": "-all",
    }


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
