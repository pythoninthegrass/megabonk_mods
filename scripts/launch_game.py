#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Starts Megabonk or the Steam client under plain Wine on macOS, detached from the caller.
Steam must be running and logged on before the game starts; see docs/development.md.

Usage:
    uv run scripts/launch_game.py steam   Start the Steam client with -silent
    uv run scripts/launch_game.py game    Start Megabonk.exe
"""

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import game_paths as gp

WINDOWS_USER = "crossover"
APP_ID = "3405340"
STEAM_DIR_WINDOWS = r"C:\Program Files (x86)\Steam"
GAME_EXE_WINDOWS = STEAM_DIR_WINDOWS + r"\steamapps\common\Megabonk\Megabonk.exe"
STEAM_ARGS = ["-silent", "-no-cef-sandbox", "-cef-disable-gpu", "-cef-disable-gpu-compositing"]
GAME_DLL_OVERRIDES = "version=n,b;d3d11,d3d10core=n,b"


@dataclass(frozen=True)
class Launch:
    argv: list[str]
    env: dict[str, str]
    cwd: Path | None


def _wine_env(prefix: Path) -> dict[str, str]:
    return {"WINEPREFIX": str(prefix), "WINEMSYNC": "1", "USER": WINDOWS_USER, "LOGNAME": WINDOWS_USER}


def build_game_launch(wine: Path, prefix: Path, game: Path) -> Launch:
    env = {
        **_wine_env(prefix),
        "SteamAppId": APP_ID,
        "SteamGameId": APP_ID,
        "WINEDLLOVERRIDES": GAME_DLL_OVERRIDES,
        "WINEDEBUG": "-all",
    }
    return Launch([str(wine), GAME_EXE_WINDOWS], env, game)


def build_steam_launch(wine: Path, prefix: Path) -> Launch:
    return Launch([str(wine), STEAM_DIR_WINDOWS + r"\steam.exe", *STEAM_ARGS], _wine_env(prefix), None)


def prefix_for(game: Path) -> Path:
    prefix = gp.wine_prefix(game)
    if prefix is None:
        raise SystemExit(f"{game} is not inside a Wine prefix (no drive_c ancestor); set MEGABONK_WINE_PREFIX")
    return prefix


def spawn(launch: Launch) -> None:
    subprocess.Popen(
        launch.argv,
        env={**os.environ, **launch.env},
        cwd=launch.cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["steam", "game"])
    args = parser.parse_args(argv)

    game = gp.game_dir()
    wine = gp.wine_bin()
    if not wine.is_file():
        print(f"wine binary not found at {wine}; run 'task wine:install' or set MEGABONK_WINE", file=sys.stderr)
        return 1
    prefix = prefix_for(game)
    spawn(build_steam_launch(wine, prefix) if args.target == "steam" else build_game_launch(wine, prefix, game))
    return 0


if __name__ == "__main__":
    sys.exit(main())
