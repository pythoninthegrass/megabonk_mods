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
    run.py load <level> [--map N] [--stage N] [--tier N] [--seed N]
                                   Load a level file and start it, optionally replacing those fields for this load
    run.py screenshot <out.png>    Save the game's rendered frame
    run.py freeze                  Pause gameplay through MyTime.Pause
    run.py resume                  Unpause gameplay through MyTime.Unpause
    run.py invulnerable            Make the player survive enemy damage
    run.py vulnerable              Restore normal player damage
    run.py kill                    End the run at once by killing the player, even when invulnerable
    run.py damage <1-99>           Apply integer damage bypassing shield; preserves 1 HP unless --no-nonlethal
    run.py steam-ready             Check whether the in-game Steamworks client is ready
    run.py state                   Print the game's current state as JSON (level, editor, player, tool, selection)
    run.py shader-report           Print which candidate shaders Shader.Find resolves and the shaders and properties of the scene's materials
    run.py material-dump [object]  Print the shader, keywords and textures of every material under the objects whose name contains [object] (default Warehouse)
    run.py character-screen <on|off>  Restrict the game's character screen to Calcium and Tony McZoom (a custom run is being set up) or restore the stock grid
    run.py spawns <on|off>         Allow or stop new enemy spawns (off leaves enemies already alive; resets on level load)
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
    run.py ui-tree [X Y]           Print the editor widgets and their rects in screenshot pixels, and the widget at X Y when given
    run.py save-level [name]       Save the editor's level, as <name> when given, and print the file written
    run.py list-levels             Print the saved custom-level files and their directory
    run.py click-widget <name>     Click an editor widget by name (names come from ui-tree), without pixel coordinates
    run.py type <text>             Type text into the focused field (\\b is backspace, \\n is return), at most 200 characters
    run.py teleport X Y Z          Move the player's feet to a world position and print the position reached
    run.py teleport --cell CX CY   Move the player to a grid cell's centre, on the tile surface there
    run.py item NAME [AMOUNT]      Print the player's amount of an item; with AMOUNT set it exactly (0 removes it), printing before and after
    run.py grind-slide <on|off|auto>  Hold the slide button down, release it, or read the real device again, for the grind gate on a grindRequiresSlide level
    run.py dismiss-levelup [--choice N]  Pick offer N (default 0) in the open level-up dialog; prints dialogWasOpen and chosen
    run.py quit                    Quit the game, wait for the process to exit, and stop leftover Wine processes (macOS)
    run.py relaunch [level] [--no-level] [--map N] [--stage N] [--tier N] [--seed N] [--character NAME]
                                   Quit and relaunch the game, load a level (default: the test forest) and enter editor; --no-level stops at the main menu
    run.py cycle <level> <out.png> Load, wait --settle seconds, screenshot, quit
                                   [--invulnerable] applies before the settle wait
                                   [--freeze] [--camera X Y Z RX RY RZ] apply before the screenshot

Game directory resolution: process environment, then the nearest .env walking up from the current
directory or this script, then the per-runtime default (see game_paths.py). Keys: MEGABONK_GAME_DIR,
MEGABONK_WINE_PREFIX, MEGABONK_BOTTLE, MEGABONK_MACOS_RUNTIME (wine or crossover; selects the task relaunch
starts the game with), MEGABONK_RELAUNCH_SPAWNS (default true; false stops enemy spawns after relaunch),
MEGABONK_RELAUNCH_INVULNERABLE (default false; true makes the player invulnerable after relaunch),
MEGABONK_RELAUNCH_FEATHERS (default 2; the Feathers amount set after relaunch, 0 leaves it alone).
"""

import argparse
import csv
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from decouple import Config, RepositoryEmpty, RepositoryEnv
from game_paths import latest_log_path, resolve_game_dir as _resolve_game_dir
from pathlib import Path

MACOS_RUNTIMES = ("wine", "crossover")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
POLL_SECONDS = 0.1
RELAUNCH_READY_TIMEOUT = 60.0
KILL_FLOOR_ARMED_LINE = "KillFloor: armed"
EDITOR_UNSUPPORTED_LINE = "EditorMode: unsupported map"
LOAD_FAILED_LINE = "LevelLoader: load failed"
HARNESS_ENABLED_LINE = "DevHarness: enabled"
RELAUNCH_STOP_ERRORS = {
    EDITOR_UNSUPPORTED_LINE: ("the editor does not support this map", "see the EditorMode warning in the game log"),
    LOAD_FAILED_LINE: ("the level failed to load", "see the LevelLoader line in the game log"),
}
STEAM_READY_POLL_SECONDS = 1.0
GAME_COMMAND = re.compile(r"^(?:[A-Za-z]:\\(?:.*\\)?Megabonk\.exe|(?:\S*/)?Megabonk\.x86_64)(?:\s|$)")
GAME_IMAGE_WINDOWS = "Megabonk.exe"
WINDOWS_COMMAND = re.compile(r"^[A-Za-z]:\\")
WINE_SYSTEM_COMMAND = re.compile(
    r"^[A-Za-z]:\\windows\\system32\\(?:services|plugplay|conhost|explorer|rpcss|svchost|lsass|winedevice)\.exe(?:\s|$)",
    re.IGNORECASE,
)
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


def resolve_flag(lookup: Lookup, key: str, default: bool) -> bool:
    value = (lookup(key) or "").strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return default


def resolve_relaunch_spawns(lookup: Lookup) -> bool:
    return resolve_flag(lookup, "MEGABONK_RELAUNCH_SPAWNS", True)


def resolve_relaunch_feathers(lookup: Lookup) -> int:
    raw = lookup("MEGABONK_RELAUNCH_FEATHERS")
    if raw is None or not raw.strip():
        return 2
    try:
        amount = int(raw)
    except ValueError:
        amount = -1
    if not 0 <= amount <= 999:
        raise SystemExit(f"MEGABONK_RELAUNCH_FEATHERS must be an integer from 0 to 999, got {raw!r}")
    return amount


def resolve_relaunch_invulnerable(lookup: Lookup) -> bool:
    return resolve_flag(lookup, "MEGABONK_RELAUNCH_INVULNERABLE", False)


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


def build_load_level_command(
    path: str,
    map: int | None = None,
    stage: int | None = None,
    tier: int | None = None,
    seed: int | None = None,
    character: str | None = None,
) -> dict[str, object]:
    """A load-level command whose supplied overrides replace those fields of the level file for this load only; character names the dev-flag character (calcium or tonymczoom)."""
    payload: dict[str, object] = dict(build_command("load-level", path))
    for field, value in (("map", map), ("stageIndex", stage), ("tier", tier), ("seed", seed)):
        if value is not None:
            payload[field] = value
    if character is not None:
        payload["character"] = character
    return payload


def add_load_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--map", type=int, help="replace the level's map (eMap value, e.g. 64 for Hell)")
    parser.add_argument("--stage", type=int, help="replace the level's stage index")
    parser.add_argument("--tier", type=int, help="replace the level's tier")
    parser.add_argument("--seed", type=int, help="replace the level's debug seed")
    parser.add_argument("--character", help="character for the run when MEGABONK_DEV is on: calcium or tonymczoom (default tonymczoom)")


def load_overrides(args: argparse.Namespace) -> dict[str, int | str]:
    return {k: v for k in ("map", "stage", "tier", "seed", "character") if (v := getattr(args, k)) is not None}


def build_character_screen_command(enabled: bool) -> dict[str, object]:
    return {"command": "character-screen", "enabled": enabled}


def build_spawns_command(enabled: bool) -> dict[str, object]:
    return {"command": "spawns", "enabled": enabled}


def build_damage_command(amount: int, nonlethal: bool = True) -> dict[str, object]:
    if type(amount) is not int or not 1 <= amount <= 99:
        raise ValueError("damage amount must be an integer from 1 to 99")
    if type(nonlethal) is not bool:
        raise ValueError("nonlethal must be a boolean")
    return {"command": "damage", "amount": amount, "nonlethal": nonlethal}


def damage_amount(value: str) -> int:
    try:
        amount = int(value)
        build_damage_command(amount)
        return amount
    except ValueError as error:
        raise argparse.ArgumentTypeError("damage amount must be an integer from 1 to 99") from error


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


def build_mouse_command(action: str, position: tuple[float, float] | None = None, button: int | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "mouse", "action": action}
    if position is not None:
        payload["x"], payload["y"] = position
    if button is not None:
        payload["button"] = button
    return payload


def build_click_widget_command(name: str) -> dict[str, object]:
    return {"command": "click-widget", "name": name}


def build_material_dump_command(object_name: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "material-dump"}
    if object_name is not None:
        payload["object"] = object_name
    return payload


def build_save_level_command(level: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "save-level"}
    if level is not None:
        payload["level"] = level
    return payload


def build_ui_tree_command(position: tuple[float, float] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "ui-tree"}
    if position is not None:
        payload["x"], payload["y"] = position
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


def build_item_command(name: str, amount: int | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"command": "item", "name": name}
    if amount is not None:
        payload["amount"] = amount
    return payload


def build_grind_slide_command(held: bool | None = None) -> dict[str, object]:
    """Hold the slide button down (True), release it (False), or hand the read back to the real device (None)."""
    payload: dict[str, object] = {"command": "grind-slide"}
    if held is not None:
        payload["held"] = held
    return payload


def build_query_objects_command(type_name: str, fields: list[str] | None = None) -> dict[str, object]:
    return {"command": "query-objects", "type": type_name, "fields": list(fields or [])}


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


def wait_for_any_log_line(log: Path, lines: list[str], newer_than: float, timeout: float) -> str | None:
    """The first of `lines` found in the log once it is newer than `newer_than`, or None on timeout."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            if log.stat().st_mtime > newer_than:
                text = log.read_text(errors="ignore")
                for line in lines:
                    if line in text:
                        return line
        except OSError:
            pass
        if time.monotonic() >= deadline:
            return None
        time.sleep(POLL_SECONDS)


def log_line_containing(log: Path, marker: str) -> str | None:
    """The first full log line containing `marker` after the last harness-enabled line, or None."""
    try:
        lines = log.read_text(errors="ignore").splitlines()
    except OSError:
        return None
    starts = [i for i, line in enumerate(lines) if HARNESS_ENABLED_LINE in line]
    if starts:
        lines = lines[starts[-1] :]
    return next((line for line in lines if marker in line), None)


def wait_for_log_line(log: Path, line: str, newer_than: float, timeout: float) -> bool:
    return wait_for_any_log_line(log, [line], newer_than, timeout) is not None


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


def find_wine_leftovers(ps_listing: str) -> tuple[list[int], list[int]]:
    """Pids of Wine's idle system processes and of any other Windows process, from `ps -axo pid=,command=` output."""
    stubs, others = [], []
    for line in ps_listing.splitlines():
        pid, _, command = line.strip().partition(" ")
        command = command.strip()
        if not pid.isdigit() or not WINDOWS_COMMAND.match(command):
            continue
        (stubs if WINE_SYSTEM_COMMAND.match(command) else others).append(int(pid))
    return stubs, others


def reap_wine_leftovers(ps_listing: str, kill: Callable[[int], None]) -> int:
    """Kill the Wine system processes (and their console windows) that outlive a game, unless a real Windows process such as Steam is running."""
    stubs, others = find_wine_leftovers(ps_listing)
    if others:
        print(f"quit: Windows processes still running (pids {others}), skipping Wine cleanup")
        return 0
    for pid in stubs:
        kill(pid)
    if stubs:
        print(f"quit: stopped {len(stubs)} leftover Wine processes")
    return len(stubs)


def reap_wine_leftovers_on_host(system: str | None = None) -> None:
    if (system or platform.system()) != "Darwin":
        return

    def kill(pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    listing = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True, check=True).stdout
    reap_wine_leftovers(listing, kill)


def quit_game(harness: Path, timeout: float) -> bool:
    """Ask the game to quit and block until its process is gone; a game that is not running counts as quit."""
    if not running_game_pids():
        print("quit: game not running")
    elif not send(harness, build_command("quit"), timeout):
        return False
    elif not wait_for_exit(timeout=timeout):
        print(f"quit: game still running after {timeout}s (pids {running_game_pids()})", file=sys.stderr)
        return False
    else:
        print("quit: game exited")
    reap_wine_leftovers_on_host()
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
    sub.add_parser("kill")
    damage = sub.add_parser("damage", help="apply 1–99 damage through the game, bypassing shield; nonlethal by default")
    damage.add_argument("amount", type=damage_amount)
    damage.add_argument("--nonlethal", action=argparse.BooleanOptionalAction, default=True, help="preserve at least 1 HP; --no-nonlethal can end the run")
    sub.add_parser("steam-ready")
    sub.add_parser("state")
    sub.add_parser("shader-report")
    character_screen = sub.add_parser("character-screen")
    character_screen.add_argument("state", choices=["on", "off"])
    spawns = sub.add_parser("spawns")
    spawns.add_argument("state", choices=["on", "off"])
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
    ui_tree = sub.add_parser("ui-tree")
    ui_tree.add_argument("position", type=float, nargs="*", metavar="X Y", help="screenshot pixels, origin top left")
    material_dump = sub.add_parser("material-dump")
    material_dump.add_argument("object", nargs="?", help="substring of an object or ancestor name; defaults to Warehouse")
    save_level = sub.add_parser("save-level")
    save_level.add_argument("level", nargs="?", help="level name to save as; defaults to the editor's save field")
    sub.add_parser("list-levels")
    click_widget = sub.add_parser("click-widget")
    click_widget.add_argument("name")
    teleport = sub.add_parser("teleport")
    teleport.add_argument("position", type=float, nargs="*", metavar="X Y Z", help="world units, the player's feet point")
    teleport.add_argument("--cell", type=int, nargs=2, metavar=("CX", "CY"), help="grid cell to stand at the centre of")
    item = sub.add_parser("item")
    item.add_argument("name", help="EItem member, case-sensitive, e.g. Mirror")
    item.add_argument("amount", type=int, nargs="?", help="set the amount to this exact number; omit to read it")
    grind_slide = sub.add_parser("grind-slide")
    grind_slide.add_argument("state", choices=["on", "off", "auto"], help="hold the slide button, release it, or read the real device again")
    dismiss = sub.add_parser("dismiss-levelup")
    dismiss.add_argument("--choice", type=int, default=0, help="zero-based index of the offered upgrade")
    music_probe = sub.add_parser("music-probe")
    music_probe.add_argument(
        "probe_action",
        choices=[
            "decode",
            "play",
            "stop",
            "status",
            "restart",
            "duck",
            "unduck",
            "pause",
            "unpause",
            "mute",
            "unmute",
            "clip-null",
            "pitch",
            "lowpass",
            "native-info",
            "native-tone",
            "native-play",
            "radio-next",
            "seek",
            "menu-music",
            "stage-music",
            "detach",
        ],
    )
    music_probe.add_argument("path", nargs="?", help="mp3 file name or path, for decode and play")
    music_probe.add_argument(
        "--variant",
        choices=["il2cpp", "managed"],
        help="filter signature to attach; il2cpp (default) is the only one Unity dispatches",
    )
    music_probe.add_argument(
        "--value",
        type=float,
        help="number for duck, pitch, or lowpass cutoff frequency in Hz",
    )
    type_ = sub.add_parser("type")
    type_.add_argument("text")
    load = sub.add_parser("load")
    load.add_argument("level", type=Path)
    add_load_overrides(load)
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
    relaunch.add_argument("--no-level", action="store_true", help="stop at the main menu without loading a level")
    add_load_overrides(relaunch)
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


def ui_tree_payload(args: argparse.Namespace) -> dict[str, object]:
    if len(args.position) not in (0, 2):
        raise SystemExit("ui-tree: give both X and Y, or neither")
    return build_ui_tree_command((args.position[0], args.position[1]) if args.position else None)


def material_dump_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_material_dump_command(args.object)


def save_level_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_save_level_command(args.level)


def click_widget_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_click_widget_command(args.name)


def item_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_item_command(args.name, args.amount)


def grind_slide_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_grind_slide_command({"on": True, "off": False, "auto": None}[args.state])


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


def music_probe_payload(args: argparse.Namespace) -> dict[str, object]:
    payload: dict[str, object] = {"command": "music-probe", "action": args.probe_action}
    if args.path:
        payload["path"] = args.path
    if args.variant:
        payload["variant"] = args.variant
    if args.value is not None:
        payload["value"] = args.value
    return payload


def type_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_type_command(args.text)


def character_screen_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_character_screen_command(args.state == "on")


def spawns_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_spawns_command(args.state == "on")


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
    level: Path | None,
    timeout: float,
    task: str,
    on_step: Callable[[str], None],
    on_error: Callable[[str], None],
    overrides: Mapping[str, int | str] | None = None,
    spawns: bool = True,
    invulnerable: bool = False,
    feathers: int = 2,
) -> bool:
    """Quit, relaunch, wait for the harness and Steamworks, then load the level, go invulnerable if asked, set the Feathers amount unless it is 0, stop enemy spawns unless spawns is set, and enter editor. A level of None stops at the main menu once Steamworks is ready."""
    started = time.time()

    def prepare_harness() -> str | None:
        """Quit, relaunch, and wait for the harness to enable; any step failing reports the same error."""
        if not quit_game(harness, timeout):
            return "relaunch: harness did not become ready"
        on_step("relaunch: starting game")
        if not launch_game(task):
            return "relaunch: harness did not become ready"
        on_step("relaunch: waiting for harness")
        return (
            None
            if wait_for_log_line(latest_log_path(game_dir), HARNESS_ENABLED_LINE, started, relaunch_timeout(timeout))
            else "relaunch: harness did not become ready"
        )

    def wait_for_steamworks() -> str | None:
        on_step("relaunch: waiting for Steamworks")
        return (
            None
            if wait_for_steamworks_ready(lambda: send_steam_ready(harness, min(timeout, 2.0)), relaunch_timeout(timeout))
            else "relaunch: Steamworks did not become ready"
        )

    for step in (prepare_harness, wait_for_steamworks):
        match step():
            case str() as error:
                on_error(error)
                return False

    if level is None:
        return True

    loaded = False
    for attempt in range(1, 6):
        on_step(f"relaunch: loading {level} (attempt {attempt}/5)")
        if send(harness, build_load_level_command(to_game_path(level.resolve()), **(overrides or {})), timeout):
            seen = wait_for_any_log_line(
                latest_log_path(game_dir),
                [KILL_FLOOR_ARMED_LINE, EDITOR_UNSUPPORTED_LINE, LOAD_FAILED_LINE],
                started,
                relaunch_timeout(timeout),
            )
            match seen:
                case _ if seen in RELAUNCH_STOP_ERRORS:
                    reason, hint = RELAUNCH_STOP_ERRORS[seen]
                    detail = log_line_containing(latest_log_path(game_dir), seen)
                    on_error(f"relaunch: {reason}: {detail}" if detail else f"relaunch: {reason}; {hint}")
                    return False
                case str():
                    loaded = True
                    break

    if not loaded:
        return False

    if invulnerable:
        send(harness, build_command("invulnerable"), timeout)
    if feathers:
        send(harness, build_item_command("Feathers", feathers), timeout)
    if not spawns:
        send(harness, build_spawns_command(False), timeout)
    send(harness, build_editor_command(True), timeout)
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
            payload = build_load_level_command(to_game_path(args.level.resolve()), **load_overrides(args))
            ok = send(harness, payload, args.timeout)
        case "bundle":
            ok = send_printing_result(harness, build_command("load-bundle", to_game_path(args.bundle.resolve())), args.timeout)
        case "screenshot":
            ok = send_screenshot(harness, args.out, args.timeout)
        case "quit":
            ok = quit_game(harness, args.timeout)
        case "steam-ready":
            ok = send_steam_ready(harness, args.timeout)
        case "freeze" | "resume" | "invulnerable" | "vulnerable" | "kill":
            ok = send(harness, build_command(args.action), args.timeout)
        case "state":
            ok = send_printing_result(harness, build_command("state"), args.timeout)
        case "damage":
            ok = send_printing_result(harness, build_damage_command(args.amount, args.nonlethal), args.timeout)
        case "shader-report":
            ok = send_printing_result(harness, build_command("shader-report"), args.timeout)
        case "ui-tree":
            ok = send_printing_result(harness, ui_tree_payload(args), args.timeout)
        case "material-dump":
            ok = send_printing_result(harness, material_dump_payload(args), args.timeout)
        case "save-level":
            ok = send_printing_result(harness, save_level_payload(args), args.timeout)
        case "list-levels":
            ok = send_printing_result(harness, build_command("list-levels"), args.timeout)
        case "click-widget":
            ok = send_printing_result(harness, click_widget_payload(args), args.timeout)
        case "teleport":
            ok = send_printing_result(harness, teleport_payload(args), args.timeout)
        case "item":
            ok = send_printing_result(harness, item_payload(args), args.timeout)
        case "grind-slide":
            ok = send_printing_result(harness, grind_slide_payload(args), args.timeout)
        case "dismiss-levelup":
            ok = send_printing_result(harness, dismiss_levelup_payload(args), args.timeout)
        case "music-probe":
            ok = send_printing_result(harness, music_probe_payload(args), args.timeout)
        case "character-screen":
            ok = send(harness, character_screen_payload(args), args.timeout)
        case "spawns":
            ok = send(harness, spawns_payload(args), args.timeout)
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
                None if args.no_level else args.level,
                args.timeout,
                launch_task(resolve_macos_runtime(load_lookup())),
                on_step=print,
                on_error=lambda m: print(m, file=sys.stderr),
                overrides=load_overrides(args),
                spawns=resolve_relaunch_spawns(load_lookup()),
                invulnerable=resolve_relaunch_invulnerable(load_lookup()),
                feathers=resolve_relaunch_feathers(load_lookup()),
            )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
