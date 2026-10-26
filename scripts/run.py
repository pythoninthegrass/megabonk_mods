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
    run.py steam-ready             Check whether the in-game Steamworks client is ready
    run.py state                   Print the game's current state as JSON (level, editor, player, tool, selection)
    run.py heartbeat <on|off>      Start or stop the kill-floor heartbeat (actor counts and lowest heights every 5 seconds)
    run.py cells <on|off>          Start or stop logging the player's and boss-tier actors' grid cell on change
    run.py editor <on|off>         Enter or leave editor mode (frozen run, free-fly camera), like pressing F8
    run.py camera X Y Z --rot RX RY RZ  Hold the camera at a world pose (euler degrees)
    run.py camera --clear          Return the camera to the game
    run.py key <name> [--mod NAME ...]  Tap a key (UnityEngine.KeyCode name), optionally with modifier keys held
    run.py key --down|--up <name>  Press or release a key and leave it held or released
    run.py mouse move X Y          Move the injected mouse to screenshot pixels (origin top left)
    run.py mouse click|down|up [--button N] [X Y]  Click or press/release a button (0 left, 1 right, 2 middle), moving first when X Y is given
    run.py mouse clear             Return the mouse to the real pointer
    run.py type <text>             Type text into the focused field (\\b is backspace, \\n is return), at most 200 characters
    run.py teleport X Y Z          Move the player's feet to a world position and print the position reached
    run.py teleport --cell CX CY   Move the player to a grid cell's centre, on the tile surface there
    run.py dismiss-levelup [--choice N]  Pick offer N (default 0) in the open level-up dialog; prints dialogWasOpen and chosen
    run.py quit                    Quit the game and wait for the process to exit
    run.py cycle <level> <out.png> Load, wait --settle seconds, screenshot, quit
                                   [--invulnerable] applies before the settle wait
                                   [--freeze] [--camera X Y Z RX RY RZ] apply before the screenshot

Game directory resolution: process environment, then the nearest .env walking up from the current
directory or this script, then the per-runtime default (see game_paths.py). Keys: MEGABONK_GAME_DIR,
MEGABONK_WINE_PREFIX, MEGABONK_BOTTLE, MEGABONK_MACOS_RUNTIME (wine or crossover; selects the task relaunch
starts the game with).
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
from game_paths import latest_log_path, resolve_game_dir as _resolve_game_dir
from pathlib import Path

MACOS_RUNTIMES = ("wine", "crossover")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
POLL_SECONDS = 0.1
RELAUNCH_READY_TIMEOUT = 60.0
STEAM_READY_POLL_SECONDS = 1.0
GAME_COMMAND = re.compile(r"^(?:[A-Za-z]:\\(?:.*\\)?Megabonk\.exe|(?:\S*/)?Megabonk\.x86_64)(?:\s|$)")
GAME_IMAGE_WINDOWS = "Megabonk.exe"
TEST_FOREST_LEVEL = Path(__file__).resolve().parents[1] / "levels" / "example-forest.mblevel.json"

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
    return _resolve_game_dir(lookup, system)


def resolve_macos_runtime(lookup: Lookup) -> str:
    runtime = lookup("MEGABONK_MACOS_RUNTIME") or "wine"
    if runtime not in MACOS_RUNTIMES:
        raise SystemExit(f"MEGABONK_MACOS_RUNTIME must be one of {MACOS_RUNTIMES}, got {runtime!r}")
    return runtime


def launch_task(runtime: str, system: str | None = None) -> str:
    system = system or platform.system()
    return "crossover:run" if system == "Darwin" and runtime == "crossover" else "game:run"


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


def build_key_command(action: str, key: str, modifiers: list[str] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "key", "action": action, "key": key}
    if modifiers:
        payload["modifiers"] = modifiers
    return payload


def build_mouse_command(
    action: str, position: tuple[float, float] | None = None, button: int | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {"command": "mouse", "action": action}
    if position is not None:
        payload["x"], payload["y"] = position
    if button is not None:
        payload["button"] = button
    return payload


def build_type_command(text: str) -> dict[str, object]:
    return {"command": "type", "text": text}


def build_teleport_command(position: tuple[float, ...] | None = None, cell: tuple[int, int] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "teleport"}
    if position is not None:
        payload["position"] = list(position)
    if cell is not None:
        payload["cell"] = list(cell)
    return payload


def build_dismiss_levelup_command(choice: int) -> dict[str, object]:
    return {"command": "dismiss-levelup", "choice": choice}


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


def read_result(harness: Path, name: str) -> dict | None:
    try:
        return json.loads((harness / "results" / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


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


def wait_for_log_line(log: Path, line: str, newer_than: float, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if log.stat().st_mtime > newer_than and line in log.read_text(errors="ignore"):
                return True
        except OSError:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL_SECONDS)


def launch_game(task: str = "game:run") -> bool:
    return subprocess.run(["task", task], check=False).returncode == 0


def relaunch_timeout(timeout: float) -> float:
    return max(timeout, RELAUNCH_READY_TIMEOUT)


def wait_for_steamworks_ready(
    probe: Callable[[], bool],
    timeout: float,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> bool:
    deadline = now() + timeout
    while True:
        if probe():
            return True
        if now() >= deadline:
            return False
        sleep(STEAM_READY_POLL_SECONDS)


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


def request_result(harness: Path, payload: dict[str, object], timeout: float) -> tuple[str, dict | None]:
    """Send a command and wait; returns the outcome ('done', 'rejected' or 'timeout') and the parsed result."""
    sent = write_command(harness / "commands", payload)
    outcome = wait_for_outcome(harness, sent.name, timeout)
    return outcome, read_result(harness, sent.name)


def send_for_result(harness: Path, payload: dict[str, object], timeout: float) -> tuple[bool, dict | None]:
    """Send a command; ok is false on a rejected or timed-out command or a result with ok:false."""
    outcome, result = request_result(harness, payload, timeout)
    print(f"{payload['command']}: {outcome}")
    if result is not None and result.get("ok") is False:
        print(f"{payload['command']}: {result.get('error')}", file=sys.stderr)
        return False, result
    return outcome == "done", result


def send(harness: Path, payload: dict[str, object], timeout: float) -> bool:
    return send_for_result(harness, payload, timeout)[0]


def send_steam_ready(harness: Path, timeout: float) -> bool:
    """True when the game's Steamworks client is up; a mod that returns no result counts as ready."""
    ok, result = send_for_result(harness, build_command("steam-ready"), timeout)
    payload = (result or {}).get("result")
    return ok and not (isinstance(payload, dict) and payload.get("ready") is False)


def send_printing_result(harness: Path, payload: dict[str, object], timeout: float) -> bool:
    ok, result = send_for_result(harness, payload, timeout)
    if ok and result is not None:
        print(json.dumps(result.get("result")))
    elif ok:
        print(f"{payload['command']}: no result file written", file=sys.stderr)
    return ok and result is not None


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
    sub.add_parser("steam-ready")
    sub.add_parser("state")
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
    key = sub.add_parser("key")
    key.add_argument("name", help="UnityEngine.KeyCode member name, e.g. R, Escape, LeftShift")
    key_action = key.add_mutually_exclusive_group()
    key_action.add_argument("--down", action="store_true", help="press the key and leave it held")
    key_action.add_argument("--up", action="store_true", help="release a held key")
    key.add_argument("--mod", action="append", default=[], metavar="NAME", help="modifier key held during a tap; repeatable")
    mouse = sub.add_parser("mouse")
    mouse.add_argument("verb", choices=["move", "click", "down", "up", "clear"])
    mouse.add_argument("position", type=float, nargs="*", metavar="X Y", help="screenshot pixels, origin top left")
    mouse.add_argument("--button", type=int, choices=[0, 1, 2], help="0 left (default), 1 right, 2 middle")
    teleport = sub.add_parser("teleport")
    teleport.add_argument("position", type=float, nargs="*", metavar="X Y Z", help="world units, the player's feet point")
    teleport.add_argument("--cell", type=int, nargs=2, metavar=("CX", "CY"), help="grid cell to stand at the centre of")
    dismiss = sub.add_parser("dismiss-levelup")
    dismiss.add_argument("--choice", type=int, default=0, help="zero-based index of the offered upgrade")
    type_ = sub.add_parser("type")
    type_.add_argument("text")
    load = sub.add_parser("load")
    load.add_argument("level", type=Path)
    bundle = sub.add_parser("bundle")
    bundle.add_argument("bundle", type=Path)
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
    relaunch = sub.add_parser("relaunch")
    relaunch.add_argument("level", type=Path, nargs="?", default=TEST_FOREST_LEVEL)
    return parser.parse_args(argv)


def camera_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.clear:
        return build_command("camera-clear")
    if len(args.position) != 3 or args.rot is None:
        raise SystemExit("camera: give X Y Z and --rot RX RY RZ, or --clear")
    return build_camera_command(tuple(args.position), tuple(args.rot))


def key_payload(args: argparse.Namespace) -> dict[str, object]:
    action = "down" if args.down else "up" if args.up else "tap"
    if args.mod and action != "tap":
        raise SystemExit("key: --mod only applies to a tap")
    return build_key_command(action, args.name, args.mod)


def mouse_payload(args: argparse.Namespace) -> dict[str, object]:
    if len(args.position) not in (0, 2):
        raise SystemExit("mouse: give both X and Y, or neither")
    if args.verb == "move" and not args.position:
        raise SystemExit("mouse move: give X Y")
    if args.verb == "clear" and (args.position or args.button is not None):
        raise SystemExit("mouse clear takes no coordinates or button")
    position = (args.position[0], args.position[1]) if args.position else None
    return build_mouse_command(args.verb, position, args.button)


def teleport_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.cell is not None and args.position:
        raise SystemExit("teleport: give X Y Z or --cell CX CY, not both")
    if args.cell is not None:
        return build_teleport_command(cell=tuple(args.cell))
    if len(args.position) != 3:
        raise SystemExit("teleport: give X Y Z or --cell CX CY")
    return build_teleport_command(position=tuple(args.position))


def dismiss_levelup_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_dismiss_levelup_command(args.choice)


def type_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_type_command(args.text)


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


def relaunch(
    harness: Path,
    game_dir: Path,
    level: Path,
    timeout: float,
    task: str,
    on_step: Callable[[str], None],
    on_error: Callable[[str], None],
) -> bool:
    """Quit, relaunch, wait for the harness and Steamworks, then load the level, go invulnerable and enter editor."""
    ok = quit_game(harness, timeout)
    started = time.time()
    if ok:
        on_step("relaunch: starting game")
        ok = launch_game(task)
    if ok:
        on_step("relaunch: waiting for harness")
        ok = wait_for_log_line(latest_log_path(game_dir), "DevHarness: enabled", started, relaunch_timeout(timeout))
    if not ok:
        on_error("relaunch: harness did not become ready")
    if ok:
        on_step("relaunch: waiting for Steamworks")
        ok = wait_for_steamworks_ready(
            lambda: send_steam_ready(harness, min(timeout, 2.0)),
            relaunch_timeout(timeout),
        )
    if not ok:
        on_error("relaunch: Steamworks did not become ready")
    for attempt in range(1, 6):
        if not ok:
            break
        on_step(f"relaunch: loading {level} (attempt {attempt}/5)")
        ok = send(harness, build_command("load-level", to_game_path(level.resolve())), timeout)
        if ok and wait_for_log_line(latest_log_path(game_dir), "KillFloor: armed", started, relaunch_timeout(timeout)):
            break
        ok = True
    else:
        ok = False
    if ok:
        ok = send(harness, build_command("invulnerable"), timeout)
    if ok:
        ok = send(harness, build_editor_command(True), timeout)
    return ok


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
        case "bundle":
            ok = send_printing_result(harness, build_command("load-bundle", to_game_path(args.bundle.resolve())), args.timeout)
        case "screenshot":
            ok = send_screenshot(harness, args.out, args.timeout)
        case "quit":
            ok = quit_game(harness, args.timeout)
        case "steam-ready":
            ok = send_steam_ready(harness, args.timeout)
        case "freeze" | "resume" | "invulnerable" | "vulnerable":
            ok = send(harness, build_command(args.action), args.timeout)
        case "state":
            ok = send_printing_result(harness, build_command("state"), args.timeout)
        case "teleport":
            ok = send_printing_result(harness, teleport_payload(args), args.timeout)
        case "dismiss-levelup":
            ok = send_printing_result(harness, dismiss_levelup_payload(args), args.timeout)
        case "heartbeat":
            ok = send(harness, heartbeat_payload(args), args.timeout)
        case "cells":
            ok = send(harness, cells_payload(args), args.timeout)
        case "editor":
            ok = send(harness, editor_payload(args), args.timeout)
        case "key":
            ok = send(harness, key_payload(args), args.timeout)
        case "mouse":
            ok = send(harness, mouse_payload(args), args.timeout)
        case "type":
            ok = send(harness, type_payload(args), args.timeout)
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
        case "relaunch":
            ok = relaunch(
                harness,
                game_dir,
                args.level,
                args.timeout,
                launch_task(resolve_macos_runtime(load_lookup())),
                on_step=print,
                on_error=lambda m: print(m, file=sys.stderr),
            )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
