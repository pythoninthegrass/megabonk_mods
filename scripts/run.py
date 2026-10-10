#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#     "python-decouple>=3.8",
# ]
# [tool.uv]
# exclude-newer = "2026-10-31T00:00:00Z"
# ///

# pyright: reportMissingImports=false

"""
Drives the MegabonkLevels dev harness (see docs/development.md) by dropping JSON command files into
<game dir>/harness/commands, which the running mod polls.

Usage:
    run.py enable                  Create the harness marker; takes effect on the next game launch
    run.py disable                 Remove the harness marker
    run.py load <level>            Load a level file and start it
    run.py screenshot <out.png>    Save the game's rendered frame
    run.py freeze                  Pause gameplay through MyTime.Pause
    run.py resume                  Unpause gameplay through MyTime.Unpause
    run.py invulnerable            Make the player survive enemy damage
    run.py vulnerable              Restore normal player damage
    run.py heartbeat <on|off>      Start or stop the kill-floor heartbeat (actor counts and lowest heights every 5 seconds)
    run.py cells <on|off>          Start or stop logging the player's and boss-tier actors' grid cell on change
    run.py editor <on|off>         Enter or leave editor mode (frozen run, free-fly camera), like pressing F8
    run.py camera X Y Z --rot RX RY RZ  Hold the camera at a world pose (euler degrees)
    run.py camera --clear          Return the camera to the game
    run.py quit                    Quit the game and wait for the process to exit
    run.py cycle <level> <out.png> Load, wait --settle seconds, screenshot, quit
                                   [--invulnerable] applies before the settle wait
                                   [--freeze] [--camera X Y Z RX RY RZ] apply before the screenshot

Game directory resolution: process environment, then the nearest .env walking up from the current
directory or this script, then the macOS CrossOver / Windows Steam default. Keys: MEGABONK_GAME_DIR,
MEGABONK_BOTTLE.
"""

import argparse
import csv
import json
import os
import platform
import re
import subprocess
import sys
import time
from collections.abc import Callable
from decouple import Config, RepositoryEmpty, RepositoryEnv
from pathlib import Path

DEFAULT_BOTTLE_MACOS = "~/Library/Application Support/CrossOver/Bottles/Steam/drive_c"
DEFAULT_GAME_SUBPATH = "Program Files (x86)/Steam/steamapps/common/Megabonk"
DEFAULT_GAME_DIR_WINDOWS = r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
POLL_SECONDS = 0.1
# Anchored to the start of the command so wrappers, shells and helpers that merely mention the executable
# (winewrapper, `bash -c ... Megabonk.exe`, UnityCrashHandler64.exe) never match.
GAME_COMMAND = re.compile(r"^(?:[A-Za-z]:\\(?:.*\\)?Megabonk\.exe|(?:\S*/)?Megabonk\.x86_64)(?:\s|$)")
GAME_IMAGE_WINDOWS = "Megabonk.exe"

Lookup = Callable[[str], str | None]


def find_env_file(start: Path, stop_at: Path | None = None) -> Path | None:
    for directory in [start, *start.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        if directory == stop_at:
            break
    return None


def load_lookup(search_from: list[Path] | None = None) -> Lookup:
    starts = search_from or [Path.cwd(), Path(__file__).resolve().parent]
    env_file = next((f for f in map(find_env_file, starts) if f), None)
    config = Config(RepositoryEnv(str(env_file)) if env_file else RepositoryEmpty())
    return lambda key: config(key, default=None)


def resolve_game_dir(lookup: Lookup, system: str | None = None) -> Path:
    system = system or platform.system()

    override = lookup("MEGABONK_GAME_DIR")
    if override:
        return Path(override).expanduser()

    bottle = lookup("MEGABONK_BOTTLE")
    if bottle:
        return Path(bottle).expanduser() / DEFAULT_GAME_SUBPATH

    if system == "Windows":
        return Path(DEFAULT_GAME_DIR_WINDOWS)

    return Path(DEFAULT_BOTTLE_MACOS).expanduser() / DEFAULT_GAME_SUBPATH


def to_game_path(path: Path, system: str | None = None) -> str:
    """Path as the game process sees it; CrossOver's Wine exposes the host filesystem as Z:."""
    system = system or platform.system()
    if system == "Darwin":
        return "Z:" + str(path).replace("/", "\\")
    return str(path)


def build_command(command: str, path: str | None = None) -> dict[str, str]:
    payload = {"command": command}
    if path is not None:
        payload["path"] = path
    return payload


def build_heartbeat_command(enabled: bool) -> dict[str, object]:
    return {"command": "heartbeat", "enabled": enabled}


def build_cells_command(enabled: bool) -> dict[str, object]:
    return {"command": "cells", "enabled": enabled}


def build_editor_command(enabled: bool) -> dict[str, object]:
    return {"command": "editor", "enabled": enabled}


def build_camera_command(position: tuple[float, ...], rotation: tuple[float, ...]) -> dict[str, object]:
    return {"command": "camera", "position": list(position), "rotation": list(rotation)}


def write_command(commands_dir: Path, payload: dict[str, object]) -> Path:
    name = f"{time.time_ns()}-{payload['command']}.json"
    target = commands_dir / name
    staging = target.with_suffix(".tmp")
    staging.write_text(json.dumps(payload))
    staging.rename(target)
    return target


def set_enabled(game_dir: Path, enabled: bool) -> None:
    harness = game_dir / "harness"
    marker = harness / "enabled"
    if enabled:
        (harness / "commands").mkdir(parents=True, exist_ok=True)
        marker.touch()
    else:
        marker.unlink(missing_ok=True)


def wait_for_outcome(harness: Path, name: str, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    while True:
        for outcome in ("done", "rejected"):
            if (harness / outcome / name).exists():
                return outcome
        if time.monotonic() >= deadline:
            return "timeout"
        time.sleep(POLL_SECONDS)


def is_png(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(PNG_SIGNATURE)) == PNG_SIGNATURE
    except OSError:
        return False


def wait_for_png(path: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while not is_png(path):
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL_SECONDS)
    return True


def find_game_pids(ps_listing: str) -> list[int]:
    """Pids whose command is the game executable, from `ps -axo pid=,command=` output."""
    pids = []
    for line in ps_listing.splitlines():
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit() and GAME_COMMAND.match(command.strip()):
            pids.append(int(pid))
    return pids


def find_game_pids_tasklist(tasklist_csv: str) -> list[int]:
    """Pids from `tasklist /FO CSV /NH` output; non-CSV status lines are ignored."""
    return [
        int(row[1])
        for row in csv.reader(tasklist_csv.splitlines())
        if len(row) > 1 and row[0].lower() == GAME_IMAGE_WINDOWS.lower() and row[1].isdigit()
    ]


def running_game_pids(system: str | None = None) -> list[int]:
    system = system or platform.system()
    if system == "Windows":
        cmd = ["tasklist", "/FI", f"IMAGENAME eq {GAME_IMAGE_WINDOWS}", "/NH", "/FO", "CSV"]
        return find_game_pids_tasklist(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    cmd = ["ps", "-axo", "pid=,command="]
    return find_game_pids(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)


def wait_for_exit(
    probe: Callable[[], list[int]] = running_game_pids,
    timeout: float = 15.0,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> bool:
    deadline = now() + timeout
    while probe():
        if now() >= deadline:
            return False
        sleep(POLL_SECONDS)
    return True


def quit_game(harness: Path, timeout: float) -> bool:
    """Ask the game to quit and block until its process is gone; a game that is not running counts as quit."""
    if not running_game_pids():
        print("quit: game not running")
        return True
    if not send(harness, build_command("quit"), timeout):
        return False
    if not wait_for_exit(timeout=timeout):
        print(f"quit: game still running after {timeout}s (pids {running_game_pids()})", file=sys.stderr)
        return False
    print("quit: game exited")
    return True


def send(harness: Path, payload: dict[str, object], timeout: float) -> bool:
    sent = write_command(harness / "commands", payload)
    outcome = wait_for_outcome(harness, sent.name, timeout)
    print(f"{payload['command']}: {outcome}")
    return outcome == "done"


def send_screenshot(harness: Path, out: Path, timeout: float) -> bool:
    out = out.resolve()
    out.unlink(missing_ok=True)
    if not send(harness, build_command("screenshot", to_game_path(out)), timeout):
        return False
    if not wait_for_png(out, timeout):
        print(f"screenshot: no valid PNG at {out} after {timeout}s", file=sys.stderr)
        return False
    print(f"screenshot: wrote {out}")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drive the MegabonkLevels dev harness.")
    parser.add_argument("--timeout", type=float, default=15.0, help="seconds to wait for each command")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("enable")
    sub.add_parser("disable")
    sub.add_parser("quit")
    sub.add_parser("freeze")
    sub.add_parser("resume")
    sub.add_parser("invulnerable")
    sub.add_parser("vulnerable")
    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("state", choices=["on", "off"])
    cells = sub.add_parser("cells")
    cells.add_argument("state", choices=["on", "off"])
    editor = sub.add_parser("editor")
    editor.add_argument("state", choices=["on", "off"])
    camera = sub.add_parser("camera")
    camera.add_argument("position", type=float, nargs="*", help="X Y Z in world units")
    camera.add_argument("--rot", type=float, nargs=3, metavar=("RX", "RY", "RZ"), help="euler degrees")
    camera.add_argument("--clear", action="store_true", help="return the camera to the game")
    load = sub.add_parser("load")
    load.add_argument("level", type=Path)
    shot = sub.add_parser("screenshot")
    shot.add_argument("out", type=Path)
    cycle = sub.add_parser("cycle")
    cycle.add_argument("level", type=Path)
    cycle.add_argument("out", type=Path)
    cycle.add_argument("--invulnerable", action="store_true", help="make the player invulnerable before the settle wait")
    cycle.add_argument("--freeze", action="store_true", help="freeze gameplay before the screenshot")
    cycle.add_argument(
        "--camera",
        type=float,
        nargs=6,
        metavar=("X", "Y", "Z", "RX", "RY", "RZ"),
        help="hold the camera at this pose for the screenshot",
    )
    cycle.add_argument("--settle", type=float, default=5.0, help="seconds between load and screenshot")
    return parser.parse_args(argv)


def camera_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.clear:
        return build_command("camera-clear")
    if len(args.position) != 3 or args.rot is None:
        raise SystemExit("camera: give X Y Z and --rot RX RY RZ, or --clear")
    return build_camera_command(tuple(args.position), tuple(args.rot))


def heartbeat_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_heartbeat_command(args.state == "on")


def cells_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_cells_command(args.state == "on")


def editor_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_editor_command(args.state == "on")


def prepare_frame(harness: Path, args: argparse.Namespace) -> bool:
    """Apply the cycle's --freeze and --camera flags before the screenshot."""
    if args.freeze and not send(harness, build_command("freeze"), args.timeout):
        return False
    if args.camera:
        payload = build_camera_command(tuple(args.camera[:3]), tuple(args.camera[3:]))
        return send(harness, payload, args.timeout)
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    game_dir = resolve_game_dir(load_lookup())
    harness = game_dir / "harness"

    if args.action in ("enable", "disable"):
        set_enabled(game_dir, args.action == "enable")
        print(f"harness {args.action}d at {harness}")
        return 0

    if not (harness / "enabled").is_file():
        print(f"harness not enabled at {harness}; run 'run.py enable' and relaunch the game", file=sys.stderr)
        return 2

    match args.action:
        case "load":
            ok = send(harness, build_command("load-level", to_game_path(args.level.resolve())), args.timeout)
        case "screenshot":
            ok = send_screenshot(harness, args.out, args.timeout)
        case "quit":
            ok = quit_game(harness, args.timeout)
        case "freeze" | "resume" | "invulnerable" | "vulnerable":
            ok = send(harness, build_command(args.action), args.timeout)
        case "heartbeat":
            ok = send(harness, heartbeat_payload(args), args.timeout)
        case "cells":
            ok = send(harness, cells_payload(args), args.timeout)
        case "editor":
            ok = send(harness, editor_payload(args), args.timeout)
        case "camera":
            ok = send(harness, camera_payload(args), args.timeout)
        case "cycle":
            ok = send(harness, build_command("load-level", to_game_path(args.level.resolve())), args.timeout)
            if ok and args.invulnerable:
                ok = send(harness, build_command("invulnerable"), args.timeout)
            if ok:
                time.sleep(args.settle)
                ok = prepare_frame(harness, args)
            if ok:
                ok = send_screenshot(harness, args.out, args.timeout)
            if ok:
                ok = quit_game(harness, args.timeout)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
