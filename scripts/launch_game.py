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
    uv run scripts/launch_game.py watch --log FILE -- argv...   internal: run the game and append its exit status to FILE
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
# MelonLoader 0.7.3 crashes (silent exit 1) when the RemoteAPI update-check returns a non-semver dumper version; the check only matters for games registered on api.melonloader.com.
GAME_ARGS = ["--melonloader.agfoffline"]
GAME_WINEDEBUG = "-all,err+seh,warn+seh,err+module,trace+loaddll"


@dataclass(frozen=True)
class Launch:
    argv: list[str]
    env: dict[str, str]
    cwd: Path | None
    log: Path | None = None


def _wine_env(prefix: Path) -> dict[str, str]:
    return {"WINEPREFIX": str(prefix), "WINEMSYNC": "1", "USER": WINDOWS_USER, "LOGNAME": WINDOWS_USER}


def game_winedebug(lookup=os.environ.get) -> str:
    """The Wine debug channels for a game launch; MEGABONK_WINEDEBUG_EXTRA appends channels (e.g. +seh) for a diagnostic run."""
    debug = GAME_WINEDEBUG
    extra = (lookup("MEGABONK_WINEDEBUG_EXTRA") or "").strip()
    return f"{debug},{extra}" if extra else debug


def build_game_launch(wine: Path, prefix: Path, game: Path) -> Launch:
    env = {
        **_wine_env(prefix),
        "SteamAppId": APP_ID,
        "SteamGameId": APP_ID,
        "WINEDLLOVERRIDES": GAME_DLL_OVERRIDES,
        "WINEDEBUG": game_winedebug(),
        "MVK_CONFIG_LOG_LEVEL": "1",
        "DXVK_LOG_LEVEL": "error",
    }
    return Launch([str(wine), GAME_EXE_WINDOWS, *GAME_ARGS], env, game, game / "MelonLoader" / "wine-latest.log")


def build_steam_launch(wine: Path, prefix: Path) -> Launch:
    return Launch([str(wine), STEAM_DIR_WINDOWS + r"\steam.exe", *STEAM_ARGS], _wine_env(prefix), None)


def prefix_for(game: Path) -> Path:
    prefix = gp.wine_prefix(game)
    if prefix is None:
        raise SystemExit(f"{game} is not inside a Wine prefix (no drive_c ancestor); set MEGABONK_WINE_PREFIX")
    return prefix


def rotate_launch_log(log: Path) -> None:
    """Move the previous launch's log aside so each launch gets a fresh file, the way Unity rotates Player.log."""
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.exists():
        log.replace(log.with_name(f"{log.stem}.prev{log.suffix}"))


def watcher_argv(launch: Launch) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "watch", "--log", str(launch.log), "--", *launch.argv]


WATCH_ENV_PREFIXES = ("WINE", "DOTNET_", "DYLD_", "MVK_", "DXVK_", "MEGABONK_", "Steam")


def launch_context_header(argv: list[str], env: dict[str, str]) -> str:
    """A header naming the launching context (process ids, cwd, tty, and the env that could poison a boot), written before the game starts so a dead log can be compared against a known-good launch after the parent shell is gone."""
    try:
        tty = os.ttyname(0)
    except OSError:
        tty = "none"
    interesting = sorted(name for name in env if name.startswith(WATCH_ENV_PREFIXES))
    pairs = " ".join(f"{name}={env[name]!r}" for name in interesting) or "(none)"
    return (f"watch: launched pid={os.getpid()} ppid={os.getppid()} session={os.getsid(0)} cwd={os.getcwd()} tty={tty}\n"
            f"watch: argv={' '.join(argv)}\nwatch: env {pairs}\n")


def watch_launch(log: Path, argv: list[str]) -> int:
    """Run the game to completion from the detached watcher and append its exit status to the log; only the game's parent can wait on it, which is why spawn() detaches this process instead of the game."""
    with log.open("ab") as stream:
        stream.write(launch_context_header(argv, dict(os.environ)).encode())
        stream.flush()
        proc = subprocess.Popen(argv, stdout=stream, stderr=stream)
        status = proc.wait()
        stream.write(f"\nwine: game process exited with status {status}\n".encode())
    return status


def spawn(launch: Launch) -> None:
    """Start the target detached; a logged game launch runs through a watcher process that can reap it and record its exit status."""
    env = {**os.environ, **launch.env}
    if launch.log is not None:
        rotate_launch_log(launch.log)
        subprocess.Popen(
            watcher_argv(launch),
            env=env,
            cwd=launch.cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return
    subprocess.Popen(
        launch.argv,
        env=env,
        cwd=launch.cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["watch"]:
        if argv[1:2] != ["--log"] or len(argv) < 4:
            print("usage: launch_game.py watch --log FILE -- argv...", file=sys.stderr)
            return 2
        game_argv = argv[3:]
        if game_argv[:1] == ["--"]:
            game_argv = game_argv[1:]
        return watch_launch(Path(argv[2]), game_argv)

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
