# pyright: reportMissingImports=false

"""
Drives the MegabonkLevels dev harness (see docs/development.md) by dropping JSON command files into
<game dir>/harness/commands, which the running mod polls.

Usage:
    run.py enable                  Create the harness marker; takes effect on the next game launch
    run.py disable                 Remove the harness marker
    run.py clear-console-log       Delete the console's persisted history and scrollback
    run.py load <level> [--map N] [--stage N] [--tier N] [--seed N] [--no-seed]
                                   Load a level file and start it, optionally replacing those fields for this load; --no-seed lets the game roll its own
    run.py screenshot <out.png>    Save the game's rendered frame
    run.py freeze                  Pause gameplay through MyTime.Pause
    run.py resume                  Unpause gameplay through MyTime.Unpause
    run.py invulnerable            Make the player survive enemy damage
    run.py vulnerable              Restore normal player damage
    run.py kill                    End the run at once by killing the player, even when invulnerable
    run.py restart-run             Run the game's own restart, the death screen's Retry button
    run.py press-death-confirm     Press Confirm on the death screen, opening the run summary; fails when the death screen is not showing
    run.py press-summary-restart   Press the run summary's Restart button; fails when the summary is not showing
    run.py music <action> [n]      Control level music: play, pause, next, prev, track <n>, list, now
    run.py kill-enemies <target>   Kill the nearest enemy, all enemies or all bosses through the game's damage path
    run.py damage <1-99>           Apply integer damage bypassing shield; preserves 1 HP unless --no-nonlethal
    run.py steam-ready             Check whether the in-game Steamworks client is ready
    run.py state                   Print the game's current state as JSON (level, editor, player, tool, selection)
    run.py console '<line>'        Run a console line and print the overlay's reply without opening it
    run.py shader-report           Print which candidate shaders Shader.Find resolves and the shaders and properties of the scene's materials
    run.py material-dump [object]  Print the shader, keywords and textures of every material under the objects whose name contains [object] (default Warehouse)
    run.py character-screen <on|off>  Restrict the game's character screen to Calcium and Tony McZoom (a custom run is being set up) or restore the stock grid
    run.py hud <on|off>            Show or hide the stock HUD without resetting the coordinate toggle
    run.py coordinates <on|off>    Show or hide coordinates in play or editor mode (also F7)
    run.py spawns <on|off>         Allow or stop new enemy spawns (off leaves enemies already alive; resets on level load)
    run.py heartbeat <on|off>      Start or stop the kill-floor heartbeat (actor counts and lowest heights every 5 seconds)
    run.py perf <verb> [--count N] [--value X] [--target NAME] [--enable|--disable] [--hp N]
                                   Frame-time profiler: start|report|status|reset a measurement window, spawn N enemies (1-300),
                                   hold or release a time scale (0.05-20), toggle one mod tick or stock patch probe off and on,
                                   turn vsync off for an uncapped window, keep the player alive (health: invulnerable
                                   plus hp) so a swarm cannot end the run inside a window
    run.py cells <on|off>          Start or stop logging the player's and boss-tier actors' grid cell on change
    run.py editor <on|off>         Enter or leave editor mode (frozen run, free-fly camera), like pressing F8
    run.py camera X Y Z --rot RX RY RZ  Hold the camera at a world pose (euler degrees)
    run.py camera --clear          Return the camera to the game
    run.py key <name> [--mod NAME ...]  Tap a key (UnityEngine.KeyCode name), optionally with modifier keys held
    run.py key --down|--up <name>  Press or release a key and leave it held or released
    run.py mouse move X Y          Move the injected mouse to screenshot pixels (origin top left)
    run.py mouse click|down|up [--button N] [X Y]  Click or press/release a button (0 left, 1 right, 2 middle), moving first when X Y is given
    run.py mouse clear             Return the mouse to the real pointer
    run.py menu start|status|stop   Manage persistent Linux input devices for stock gamepadui menus
    run.py menu drive '<JSON>' [--out screenshot.png]
                                   Drive OS-level menu input, not editor injection; use @file or - for a batch file/stdin
                                   Each menu command accepts --host HOST --remote-repo PATH for SSH execution
    run.py ui-tree [X Y]           Print the editor widgets and their rects in screenshot pixels, and the widget at X Y when given
    run.py save-level [name]       Save the editor's level, as <name> when given, and print the file written
    run.py new-level [name]        Write a blank from-scratch level and open it in the editor; --map, --stage, --tier, --size
    run.py list-levels             Print the saved custom-level files and their directory
    run.py palette                 Print every palette entry for the loaded map as [id, name, category, map] rows
    run.py query-objects <TYPE>    Print the live assets of a UnityEngine.Object type as JSON; --fields and --depth
    run.py click-widget <name>     Click an editor widget by name (names come from ui-tree), without pixel coordinates
    run.py type <text>             Type text into the focused field (\\b is backspace, \\n is return), at most 200 characters
    run.py teleport X Y Z          Move the player's feet to a world position and print the position reached
    run.py teleport --cell CX CY   Move the player to a grid cell's centre, on the tile surface there
    run.py item NAME [AMOUNT]      Print the player's amount of an item; with AMOUNT set it exactly (0 removes it), printing before and after
    run.py grind-slide <on|off|auto>  Hold the slide button down, release it, or read the real device again, for the grind gate on a grindRequiresSlide level
    run.py dismiss-levelup [--choice N]  Pick offer N (default 0) in the open level-up dialog; prints dialogWasOpen and chosen
    run.py dismiss-offers [--choice N] [--skip]  Close the open reward window (level-up, shrine offers, chest, microwave); --choice N picks offer N, --skip skips a level-up without choosing
    run.py interact [--type SUBSTRING] [--max-distance N] [--force]  Activate the nearest interactable through the game's own Interact, bypassing the hover gate
    run.py quit                    Quit the game, wait for the process to exit, and stop leftover Wine processes
    run.py quit --stop-steam --stop-menu
                                   The same, plus shutting the Steam client and the menu input service down
    run.py teardown [--stop-steam] [--stop-menu]
                                   The quit teardown without the harness marker or a running game
    run.py relaunch [level] [--no-level] [--map N] [--stage N] [--tier N] [--seed N] [--no-seed] [--character NAME]
                                   Quit and relaunch the game, load a level (default: the test forest) and enter editor; --no-level stops at the main menu, --no-seed lets the game roll its own
                                   An offline run (Steam stub, no Steam session) continues once the game reports Steamworks not ready; a game that exits during startup fails fast
    run.py cycle <level> <out.png> Load, wait --settle seconds, screenshot, quit
                                   [--invulnerable] applies before the settle wait
                                   [--freeze] [--camera X Y Z RX RY RZ] apply before the screenshot

Game directory resolution: process environment, then the nearest .env walking up from the current
directory or this script, then the per-runtime default (see game_paths.py). Keys: MEGABONK_GAME_DIR,
MEGABONK_WINE_PREFIX, MEGABONK_BOTTLE, MEGABONK_MACOS_RUNTIME (wine or crossover; selects the task relaunch
starts the game with), MEGABONK_RELAUNCH_SPAWNS (default true; false stops enemy spawns after relaunch),
MEGABONK_RELAUNCH_INVULNERABLE (default false; true makes the player invulnerable after relaunch),
MEGABONK_RELAUNCH_FEATHERS (default 2; the Feathers amount set after relaunch, 0 leaves it alone),
MEGABONK_RELAUNCH_DIAG (default false; true hides UnityCrashHandler64.exe and adds Wine +seh tracing so a
native startup crash reports itself instead of exiting silently; MEGABONK_EVIDENCE_DIR overrides where a
dead boot's logs are copied).
"""

import argparse
import csv
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping
from decouple import Config, RepositoryEmpty, RepositoryEnv
from megabonk_harness.checkout import CheckoutNotFound, repo_root
from megabonk_harness.game_paths import (
    evidence_dir,
    latest_log_path,
    resolve_game_dir as _resolve_game_dir,
    to_game_path,
    wine_bin,
    wine_log_path,
    wine_prefix,
)
from megabonk_harness.menu_input import request as menu_request, serve as serve_menu, validate_batch
from pathlib import Path
from typing import Literal, NamedTuple

MACOS_RUNTIMES = ("wine", "crossover")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_QUERY_DEPTH = 6  # must match AssetDump.MaxDepth in the mod
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
STEAM_OFFLINE_GRACE_SECONDS = 15.0
GAME_STARTUP_GRACE_SECONDS = 5.0
WINESERVER_EXIT_TIMEOUT_SECONDS = 15.0
PRESS_WAIT_SECONDS = 15.0
PRESS_POLL_INTERVAL = 0.5
PRESS_REFUSAL_MARKERS = ("no death screen is showing", "is not showing", "is not active", "is not interactable")
WINE_STUB_KILL_GRACE_SECONDS = 1.5
GAME_COMMAND = re.compile(r"^(?:[A-Za-z]:\\(?:.*\\)?Megabonk\.exe|(?:\S*/)?Megabonk\.x86_64)(?:\s|$)")
GAME_IMAGE_WINDOWS = "Megabonk.exe"
MEGABONK_ORPHAN_COMMAND = re.compile(r"megabonk[/\\]", re.IGNORECASE)
WINESERVER_COMMAND = re.compile(r"(?:^|/)wineserver(?:\s|$)")
STEAM_APP_ID = "3405340"
WINE_STUB_BASENAMES = frozenset(
    f"{name}.exe"
    for name in (
        "conhost",
        "explorer",
        "lsass",
        "plugplay",
        "rpcss",
        "services",
        "svchost",
        "tabtip",
        "winedevice",
        "winemenubuilder",
    )
)
WINDOWS_DRIVE_ROOT = re.compile(r"^[A-Za-z]:[\\/]")
WINE_PREFIX_ROOT = re.compile(r"(.*?)(?:^|/)(?:drive_c|pfx)(?:/|$)", re.IGNORECASE)
# Environment variables naming a prefix, with the path the prefix sits at inside it; Proton sets only the second.
PREFIX_ENV_KEYS = (("WINEPREFIX", ""), ("STEAM_COMPAT_DATA_PATH", "/pfx"))
# Each Wine bottle's wineserver keeps its sockets in one directory that every process of that bottle has open.
WINESERVER_DIR = re.compile(r"^(/private/tmp/\.wine-\d+/server-[^/]+)(?:/|$)")
LSOF_TIMEOUT_SECONDS = 10
LAUNCHER_CHAIN_COMMANDS = (
    re.compile(rf"(?:^|/)reaper\s+SteamLaunch\s+AppId={STEAM_APP_ID}(?=\s|$)"),
    re.compile(rf"(?:^|/)srt-bwrap\b.*(?:\b{STEAM_APP_ID}\b|Megabonk\.exe)", re.IGNORECASE),
    re.compile(r"(?:^|/)pv-adverb\b.*\bMegabonk\.exe\b", re.IGNORECASE),
)
STEAM_CLIENT_BASENAMES = frozenset({"steam", "steam.sh"})
STEAM_FLATPAK_ID = "com.valvesoftware.Steam"
STEAM_SHUTDOWN_REQUEST = "steam://shutdownsteam"
STEAM_EXIT_TIMEOUT_SECONDS = 10.0
def example_forest_level() -> Path:
    return repo_root() / "levels" / "example-forest.mblevel.json"

Lookup = Callable[[str], str | None]


class ProcessInfo(NamedTuple):
    """One live process: its pid, its argv, and its environment when the OS let us read it."""

    pid: int
    argv: tuple[str, ...]
    environ: Mapping[str, str] | None = None
    open_paths: tuple[str, ...] | None = None


TableProvider = Callable[[], list[ProcessInfo]]


def command_text(info: ProcessInfo) -> str:
    return " ".join(info.argv)


def windows_basename(command: str) -> str:
    """Casefolded basename of a drive-rooted Windows command, or empty when the token is not one."""
    token = command.strip().strip("\"'")
    if not WINDOWS_DRIVE_ROOT.match(token):
        return ""
    return token.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].casefold()


def looks_like_windows_process(info: ProcessInfo) -> bool:
    """A drive-rooted Windows command, or any .exe, which is what a Wine process shows as argv[0]."""
    return bool(windows_basename(info.argv[0])) or info.argv[0].casefold().endswith(".exe")


def normalize_path_root(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").casefold()


def read_process_nul_list(path: Path) -> tuple[str, ...]:
    """NUL-separated strings from a /proc file; empty when it cannot be read or holds nothing."""
    try:
        raw = path.read_bytes()
    except OSError:
        return ()
    return tuple(part.decode("utf-8", "replace") for part in raw.split(b"\0") if part)


def read_process_table_proc(proc_root: Path = Path("/proc")) -> list[ProcessInfo]:
    """The Linux process table from /proc, where argv and environ are NUL-separated so backslashes and spaces in a C:\\ path cannot corrupt field splitting."""
    table: list[ProcessInfo] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        argv = read_process_nul_list(entry / "cmdline")
        if not argv:
            continue
        environ: dict[str, str] = {}
        for pair in read_process_nul_list(entry / "environ"):
            key, separator, value = pair.partition("=")
            if separator:
                environ[key] = value
        table.append(ProcessInfo(int(entry.name), argv, environ or None))
    return table


def parse_lsof_names(output: str) -> dict[int, tuple[str, ...]]:
    """Open file names per pid from `lsof -F pn` output, where a p line starts a process and each n line names one of its files."""
    names: dict[int, list[str]] = {}
    pid: int | None = None
    for line in output.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = int(line[1:])
            names.setdefault(pid, [])
        elif line.startswith("n") and pid is not None:
            names[pid].append(line[1:])
    return {pid: tuple(paths) for pid, paths in names.items()}


def read_open_paths(pids: list[int]) -> dict[int, tuple[str, ...]]:
    """Open files of the given pids; empty when lsof is missing or refuses, since it exits non-zero when any pid is unreadable yet still prints the rest."""
    if not pids:
        return {}
    try:
        result = subprocess.run(
            ["lsof", "-n", "-P", "-F", "pn", "-p", ",".join(str(pid) for pid in pids)],
            capture_output=True,
            text=True,
            check=False,
            timeout=LSOF_TIMEOUT_SECONDS,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    return parse_lsof_names(result.stdout)


def read_process_table_ps() -> list[ProcessInfo]:
    """Process table for hosts without /proc; pid=,args= is the one ps form whose keywords the BSD and GNU families both accept, with the header suppressed and the locale pinned. ps carries no environment, so the open files of Windows processes come from one lsof call."""
    output = subprocess.run(
        ["ps", "-axo", "pid=,args="],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "LC_ALL": "C"},
    ).stdout
    table: list[ProcessInfo] = []
    for line in output.splitlines():
        pid, _, command = line.strip().partition(" ")
        if not pid.isdigit():
            continue
        argv = tuple(command.split())
        if argv:
            table.append(ProcessInfo(int(pid), argv, None))
    open_paths = read_open_paths([info.pid for info in table if looks_like_windows_process(info)])
    return [info._replace(open_paths=open_paths.get(info.pid)) for info in table]


def process_table(system: str | None = None, proc_root: Path = Path("/proc")) -> list[ProcessInfo]:
    """Live processes as pid plus argv, from /proc where the kernel offers it and from ps where it does not."""
    if (system or platform.system()) == "Linux" and proc_root.is_dir():
        return read_process_table_proc(proc_root)
    return read_process_table_ps()


def find_env_file(start: Path, stop_at: Path | None = None) -> Path | None:
    for directory in [start, *start.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        if directory == stop_at:
            break
    return None


def load_lookup(search_from: list[Path] | None = None) -> Lookup:
    starts = search_from or [Path.cwd(), repo_root()]
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


def resolve_relaunch_diag(lookup: Lookup) -> bool:
    return resolve_flag(lookup, "MEGABONK_RELAUNCH_DIAG", False)


def launch_task(runtime: str, system: str | None = None) -> str:
    system = system or platform.system()
    return "crossover:run" if system == "Darwin" and runtime == "crossover" else "game:run"


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
    unseeded: bool = False,
) -> dict[str, object]:
    """A load-level command whose supplied overrides replace those fields of the level file for this load only; character names the dev-flag character (calcium or tonymczoom). unseeded sends seed null so the game rolls its own instead of forcing one."""
    if unseeded and seed is not None:
        raise ValueError("build_load_level_command: unseeded and seed cannot both be set")
    payload: dict[str, object] = dict(build_command("load-level", path))
    for field, value in (("map", map), ("stageIndex", stage), ("tier", tier), ("seed", seed)):
        if value is not None:
            payload[field] = value
    if unseeded:
        payload["seed"] = None
    if character is not None:
        payload["character"] = character
    return payload


def add_load_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--map", type=int, help="replace the level's map (eMap value, e.g. 64 for Hell)")
    parser.add_argument("--stage", type=int, help="replace the level's stage index")
    parser.add_argument("--tier", type=int, help="replace the level's tier")
    parser.add_argument("--seed", type=int, help="replace the level's debug seed")
    parser.add_argument("--no-seed", action="store_true", help="let the game roll its own seed instead of forcing the level's")
    parser.add_argument("--character", help="character for the run when MEGABONK_DEV is on: calcium or tonymczoom (default tonymczoom)")


def add_client_flags(parser: argparse.ArgumentParser) -> None:
    """Opt-in teardown of the clients the game depends on, which normally outlive a run on purpose."""
    parser.add_argument("--stop-steam", action="store_true", help="also shut the Steam client down afterwards")
    parser.add_argument("--stop-menu", action="store_true", help="also stop the OS-level menu input service")


def load_overrides(args: argparse.Namespace) -> dict[str, object]:
    overrides: dict[str, object] = {k: v for k in ("map", "stage", "tier", "seed", "character") if (v := getattr(args, k, None)) is not None}
    if getattr(args, "no_seed", False):
        overrides["unseeded"] = True
    return overrides


def load_level_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_load_level_command(to_game_path(Path(args.level).resolve()), **load_overrides(args))


def build_character_screen_command(enabled: bool) -> dict[str, object]:
    return {"command": "character-screen", "enabled": enabled}


def build_hud_command(visible: bool) -> dict[str, object]:
    return {"command": "hud", "enabled": visible}


def build_coordinates_command(visible: bool) -> dict[str, object]:
    return {"command": "coordinates", "enabled": visible}


def build_spawns_command(enabled: bool) -> dict[str, object]:
    return {"command": "spawns", "enabled": enabled}


def build_damage_command(amount: int, nonlethal: bool = True) -> dict[str, object]:
    if type(amount) is not int or not 1 <= amount <= 99:
        raise ValueError("damage amount must be an integer from 1 to 99")
    if type(nonlethal) is not bool:
        raise ValueError("nonlethal must be a boolean")
    return {"command": "damage", "amount": amount, "nonlethal": nonlethal}


KILL_ENEMY_TARGETS = ("nearest", "all", "bosses")


MUSIC_ACTIONS = ("play", "pause", "next", "prev", "track", "list", "now")


def build_music_command(action: str, track: int | None = None) -> dict[str, object]:
    if action not in MUSIC_ACTIONS:
        raise ValueError(f"music action must be one of {', '.join(MUSIC_ACTIONS)}")
    if action == "track":
        if not isinstance(track, int) or isinstance(track, bool) or track < 1:
            raise ValueError("music track needs a track number of at least 1")
        return {"command": "music", "action": action, "track": track}
    if track is not None:
        raise ValueError("music takes a track number only with the track action")
    return {"command": "music", "action": action}


def build_console_command(line: str) -> dict[str, object]:
    if not line.strip():
        raise ValueError("console needs a non-empty line")
    return {"command": "console", "line": line}


def console_log_path(game_dir: Path) -> Path:
    return game_dir / "UserData" / "console_log.jsonl"


def clear_console_log(game_dir: Path) -> bool:
    log = console_log_path(game_dir)
    existed = log.is_file()
    log.unlink(missing_ok=True)
    return existed


def build_kill_enemies_command(target: str) -> dict[str, object]:
    if target not in KILL_ENEMY_TARGETS:
        raise ValueError(f"kill-enemies target must be one of {', '.join(KILL_ENEMY_TARGETS)}")
    return {"command": "kill-enemies", "target": target}


def damage_amount(value: str) -> int:
    try:
        amount = int(value)
        build_damage_command(amount)
        return amount
    except ValueError as error:
        raise argparse.ArgumentTypeError("damage amount must be an integer from 1 to 99") from error


def build_heartbeat_command(enabled: bool) -> dict[str, object]:
    return {"command": "heartbeat", "enabled": enabled}


PERF_ACTIONS = ("report", "status", "start", "reset", "spawn", "timescale", "toggle", "vsync", "health", "census", "render", "physics", "animation")
PERF_MAX_ENEMIES = 300
PERF_MIN_TIME_SCALE = 0.05
PERF_MAX_TIME_SCALE = 20.0
PERF_MAX_PLAYER_HP = 100_000_000


def build_perf_command(
    action: str,
    count: int | None = None,
    value: float | None = None,
    target: str | None = None,
    enabled: bool | None = None,
    hp: int | None = None,
) -> dict[str, object]:
    """One profiler verb: spawn carries a count, timescale an optional value, toggle a target and its new state."""
    payload: dict[str, object] = {"command": "perf", "action": action}
    if count is not None:
        payload["count"] = count
    if value is not None:
        payload["value"] = value
    if target is not None:
        payload["target"] = target
    if enabled is not None:
        payload["enabled"] = enabled
    if hp is not None:
        payload["hp"] = hp
    return payload


def perf_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"count must be an integer from 1 to {PERF_MAX_ENEMIES}") from error
    if not 1 <= count <= PERF_MAX_ENEMIES:
        raise argparse.ArgumentTypeError(f"count must be an integer from 1 to {PERF_MAX_ENEMIES}")
    return count


def perf_hp(value: str) -> int:
    try:
        hp = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"hp must be an integer from 1 to {PERF_MAX_PLAYER_HP}") from error
    if not 1 <= hp <= PERF_MAX_PLAYER_HP:
        raise argparse.ArgumentTypeError(f"hp must be an integer from 1 to {PERF_MAX_PLAYER_HP}")
    return hp


def perf_time_scale(value: str) -> float:
    try:
        scale = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"time scale must be a number from {PERF_MIN_TIME_SCALE} to {PERF_MAX_TIME_SCALE}") from error
    if not PERF_MIN_TIME_SCALE <= scale <= PERF_MAX_TIME_SCALE:
        raise argparse.ArgumentTypeError(f"time scale must be a number from {PERF_MIN_TIME_SCALE} to {PERF_MAX_TIME_SCALE}")
    return scale


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
    action: str,
    position: tuple[float, float] | None = None,
    button: int | None = None,
    delta: float | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"command": "mouse", "action": action}
    if position is not None:
        payload["x"], payload["y"] = position
    if button is not None:
        payload["button"] = button
    if delta is not None:
        payload["delta"] = delta
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


def build_new_level_command(
    level: str | None = None,
    map_id: int | None = None,
    stage: int | None = None,
    tier: int | None = None,
    size: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"command": "new-level"}
    for key, value in (("level", level), ("map", map_id), ("stageIndex", stage), ("tier", tier), ("size", size)):
        if value is not None:
            payload[key] = value
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


def query_depth(value: str) -> int:
    depth = int(value)
    if not 0 <= depth <= MAX_QUERY_DEPTH:
        raise argparse.ArgumentTypeError(f"depth must be an integer from 0 to {MAX_QUERY_DEPTH}")
    return depth


def build_query_objects_command(type_name: str, fields: list[str] | None = None, depth: int = 0) -> dict[str, object]:
    command: dict[str, object] = {"command": "query-objects", "type": type_name, "fields": list(fields or [])}
    if depth:
        command["depth"] = depth
    return command


def query_objects_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_query_objects_command(args.type, args.fields, getattr(args, "depth", 0))


def build_fall_damage_command() -> dict[str, object]:
    """Report the live player's fall-damage inputs, plus both characters' stored values."""
    return {"command": "fall-damage"}


def build_dismiss_levelup_command(choice: int) -> dict[str, object]:
    return {"command": "dismiss-levelup", "choice": choice}


def build_dismiss_offers_command(choice: int | None, skip: bool) -> dict[str, object]:
    payload: dict[str, object] = {"command": "dismiss-offers"}
    if choice is not None:
        payload["choice"] = choice
    if skip:
        payload["skip"] = True
    return payload


def build_interact_command(type_filter: str | None, max_distance: float | None, force: bool) -> dict[str, object]:
    payload: dict[str, object] = {"command": "interact"}
    if type_filter is not None:
        payload["type"] = type_filter
    if max_distance is not None:
        payload["maxDistance"] = max_distance
    if force:
        payload["force"] = True
    return payload


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


def wait_for_any_log_line(
    log: Path,
    lines: list[str],
    newer_than: float,
    timeout: float,
    alive: Callable[[], bool] | None = None,
) -> str | None:
    """The first of `lines` found in the log once it is newer than `newer_than`, or None on timeout; returns None early when `alive` reports the game has exited."""
    deadline = time.monotonic() + timeout
    while True:
        if alive is not None and not alive():
            return None
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


def wait_for_log_line(log: Path, line: str, newer_than: float, timeout: float, alive: Callable[[], bool] | None = None) -> bool:
    return wait_for_any_log_line(log, [line], newer_than, timeout, alive) is not None


def launch_game(task: str = "game:run") -> bool:
    return subprocess.run(["task", task], check=False, cwd=repo_root()).returncode == 0


def relaunch_timeout(timeout: float) -> float:
    return max(timeout, RELAUNCH_READY_TIMEOUT)


def wait_for_steamworks_ready(
    probe: Callable[[], str | None],
    timeout: float,
    alive: Callable[[], bool] = lambda: True,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> str:
    """Poll the steam-ready verdict: 'ready', 'offline' once a definite not-ready has stood for the grace period, 'timeout' without a definite answer, or 'dead' when the game exited."""
    deadline = now() + timeout
    offline_deadline: float | None = None
    while True:
        if not alive():
            return "dead"
        match probe():
            case "ready":
                return "ready"
            case "not-ready":
                if offline_deadline is None:
                    offline_deadline = now() + STEAM_OFFLINE_GRACE_SECONDS
            case _:
                pass
        if offline_deadline is not None and now() >= offline_deadline:
            return "offline"
        if now() >= deadline:
            return "timeout"
        sleep(STEAM_READY_POLL_SECONDS)


def find_game_pids(table: list[ProcessInfo]) -> list[int]:
    """Pids whose command line is the game executable, Windows or native."""
    return [info.pid for info in table if GAME_COMMAND.match(command_text(info))]


def find_game_pids_tasklist(tasklist_csv: str) -> list[int]:
    """Pids from `tasklist /FO CSV /NH` output; non-CSV status lines are ignored."""
    return [
        int(row[1])
        for row in csv.reader(tasklist_csv.splitlines())
        if len(row) > 1 and row[0].lower() == GAME_IMAGE_WINDOWS.lower() and row[1].isdigit()
    ]


def running_game_pids(system: str | None = None, table: TableProvider | None = None) -> list[int]:
    system = system or platform.system()
    if system == "Windows":
        cmd = ["tasklist", "/FI", f"IMAGENAME eq {GAME_IMAGE_WINDOWS}", "/NH", "/FO", "CSV"]
        return find_game_pids_tasklist(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    return find_game_pids(table() if table else process_table(system))


def game_is_running() -> bool:
    return bool(running_game_pids())


def resolve_wine_prefix() -> Path:
    game = resolve_game_dir(load_lookup())
    prefix = wine_prefix(game)
    if prefix is None:
        raise SystemExit(f"{game} is not inside a Wine prefix (no drive_c ancestor); set MEGABONK_WINE_PREFIX")
    return prefix


def wineserver_binary() -> Path:
    wine = wine_bin()
    candidate = wine.parent / "wineserver"
    return candidate if candidate.parent.is_dir() else Path("wineserver")


def find_wineserver_pids(table: list[ProcessInfo]) -> list[int]:
    """Pids running wineserver for any prefix; a native binary, so argv is the only place its name appears."""
    return [info.pid for info in table if WINESERVER_COMMAND.search(command_text(info))]


def running_wineserver_pids(table: TableProvider | None = None) -> list[int]:
    return find_wineserver_pids(table() if table else process_table())


def wait_for_wineserver_to_exit(timeout: float = WINESERVER_EXIT_TIMEOUT_SECONDS) -> bool:
    """Block until no wineserver serves the prefix, so a relaunch never races the previous session's teardown; a game process appearing counts as failure."""
    if not running_wineserver_pids():
        return True
    cmd = [str(wineserver_binary()), "-w"]
    try:
        subprocess.run(cmd, env={**os.environ, "WINEPREFIX": str(resolve_wine_prefix())}, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass
    if not running_wineserver_pids():
        return not running_game_pids()
    leftover_servers = running_wineserver_pids()
    killed: list[int] = []
    refused: list[int] = []
    for pid in leftover_servers:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue
        except PermissionError:
            refused.append(pid)
            continue
        killed.append(pid)
    if killed:
        print(f"relaunch: force-killed {len(killed)} lingering wineserver(s)")
    if refused:
        listed = ", ".join(str(pid) for pid in refused)
        print(f"relaunch: {len(refused)} wineserver(s) could not be killed (not ours): {listed}")
    time.sleep(1.0)
    force_kill_wine_leftovers("relaunch")
    return not running_wineserver_pids() and not running_game_pids()


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


class SparedProcess(NamedTuple):
    """A process the reaper left alone, with the bottle it was attributed to (None when unknown) and why."""

    pid: int
    executable: str
    bottle: str | None
    reason: str


class WineLeftovers(NamedTuple):
    """Pids the reaper may kill, split by role, plus the Windows processes it must spare, the candidates it withheld and a description of each spared process."""

    stubs: list[int]
    orphans: list[int]
    others: list[int]
    withheld: list[int]
    spared: list[SparedProcess] = []


SPARE_REASONS = {
    "ours": "live Windows process in this bottle",
    "foreign": "foreign bottle, never touched",
    "unknown": "no bottle signal while Windows processes run",
}


def is_wine_stub(info: ProcessInfo) -> bool:
    """Wine's own session processes, by exact basename, so a lookalike under another path is not one."""
    return windows_basename(info.argv[0]) in WINE_STUB_BASENAMES


def is_megabonk_helper(info: ProcessInfo) -> bool:
    """A Windows process from the game's own directory, such as Unity's crash handler."""
    return bool(windows_basename(info.argv[0])) and bool(MEGABONK_ORPHAN_COMMAND.search(command_text(info)))


def is_launcher_chain(info: ProcessInfo) -> bool:
    """Steam's own wrappers for this app id, which hold a Proton prefix open after the game dies."""
    text = command_text(info)
    return any(pattern.search(text) for pattern in LAUNCHER_CHAIN_COMMANDS)


def is_steam_client(info: ProcessInfo) -> bool:
    """The Steam client, native or under Flatpak; a steam.exe running inside a prefix is not it."""
    argv0 = info.argv[0]
    if WINDOWS_DRIVE_ROOT.match(argv0):
        return False
    if argv0.replace("\\", "/").rsplit("/", 1)[-1].casefold() in STEAM_CLIENT_BASENAMES:
        return True
    return any(part.casefold() == STEAM_FLATPAK_ID.casefold() for part in info.argv)


def wine_prefix_root(info: ProcessInfo) -> str | None:
    """The prefix a process belongs to, from WINEPREFIX, Proton's STEAM_COMPAT_DATA_PATH, or a drive_c/pfx path in argv."""
    environ = info.environ or {}
    for key, suffix in PREFIX_ENV_KEYS:
        value = environ.get(key)
        if value:
            return normalize_path_root(f"{value.rstrip('/')}{suffix}")
    for argument in (*info.argv, *(info.open_paths or ())):
        match = WINE_PREFIX_ROOT.match(normalize_path_root(argument))
        if match:
            return normalize_path_root(match.group(1))
    return None


def wineserver_dirs(info: ProcessInfo) -> set[str]:
    return {match.group(1) for path in info.open_paths or () if (match := WINESERVER_DIR.match(path))}


def process_prefixes(table: list[ProcessInfo]) -> dict[int, str | None]:
    """Prefix per pid; a process with no prefix signal of its own takes the one prefix every attributed process sharing its wineserver directory agrees on."""
    own = {info.pid: wine_prefix_root(info) for info in table}
    server_owners: dict[str, set[str]] = {}
    for info in table:
        if own[info.pid]:
            for directory in wineserver_dirs(info):
                server_owners.setdefault(directory, set()).add(own[info.pid])
    resolved = dict(own)
    for info in table:
        if own[info.pid]:
            continue
        shared = set().union(*(server_owners.get(directory, set()) for directory in wineserver_dirs(info)))
        if len(shared) == 1:
            resolved[info.pid] = next(iter(shared))
    return resolved


def bottle_name(root: str | None) -> str | None:
    if not root:
        return None
    parts = root.rstrip("/").split("/")
    return parts[-2] if parts[-1] == "pfx" and len(parts) > 1 else parts[-1]


def current_wine_prefix() -> str | None:
    """The prefix the configured game directory lives in, or None when it cannot be resolved."""
    try:
        return str(resolve_wine_prefix())
    except SystemExit:
        return None


def find_wine_leftovers(table: list[ProcessInfo], prefix: str | None = None) -> WineLeftovers:
    """Pids to clean and pids to spare: a candidate attributed elsewhere is never killed, one attributed to us is killed only while no live Windows process shares that prefix, and one nothing attributes only while no Windows process is live at all."""
    prefixes = process_prefixes(table)
    classified: list[tuple[ProcessInfo, bool, str]] = []
    others: list[tuple[ProcessInfo, str]] = []
    ours_busy: list[int] = []
    for info in table:
        if is_steam_client(info):
            continue
        stub = is_wine_stub(info)
        candidate = stub or is_megabonk_helper(info) or is_launcher_chain(info)
        if not candidate and not windows_basename(info.argv[0]):
            continue
        owner = prefixes[info.pid]
        if owner is None or prefix is None:
            attribution = "unknown"
        else:
            attribution = "ours" if owner == normalize_path_root(prefix) else "foreign"
        if candidate and attribution != "foreign":
            classified.append((info, stub, attribution))
        else:
            others.append((info, attribution))
            if attribution == "ours":
                ours_busy.append(info.pid)

    def claimed(attribution: str) -> bool:
        return not (ours_busy if attribution == "ours" else others)

    spared = [(info, attribution, SPARE_REASONS[attribution]) for info, attribution in others]
    spared += [(info, attribution, SPARE_REASONS[attribution]) for info, _, attribution in classified if not claimed(attribution)]
    return WineLeftovers(
        [info.pid for info, stub, attribution in classified if stub and claimed(attribution)],
        [info.pid for info, stub, attribution in classified if not stub and claimed(attribution)],
        [info.pid for info, _ in others],
        [info.pid for info, _, attribution in classified if not claimed(attribution)],
        [
            SparedProcess(info.pid, info.argv[0].replace("\\", "/").rsplit("/", 1)[-1], bottle_name(prefixes[info.pid]), reason)
            for info, _, reason in sorted(spared, key=lambda entry: entry[0].pid)
        ],
    )


def signal_process(pid: int, sig: int, killer: Callable[[int, int], None] | None = None) -> None:
    """Send a signal, tolerating a process that exited first."""
    try:
        (killer or os.kill)(pid, sig)
    except ProcessLookupError:
        pass


def reap_wine_leftovers(table: list[ProcessInfo], kill: Callable[[int], None], prefix: str | None = None) -> int:
    """SIGTERM the Wine stubs and orphaned game helpers that belong to us, including the console windows a dead game leaves behind."""
    leftovers = find_wine_leftovers(table, prefix)
    if leftovers.withheld:
        print("quit: leaving Wine leftovers alone while other Windows processes run")
        for spared in leftovers.spared:
            print(f"quit:   pid {spared.pid} {spared.executable} bottle={spared.bottle or 'unknown'}: {spared.reason}")
    pids = leftovers.stubs + leftovers.orphans
    if not pids:
        return 0
    for pid in pids:
        kill(pid)
    print(f"quit: stopped {len(pids)} leftover Wine processes")
    return len(pids)


def force_kill_wine_leftovers(
    context: str = "quit",
    prefix: str | None | Literal["auto"] = "auto",
    table: TableProvider | None = None,
) -> int:
    """SIGKILL the Wine stubs and game helpers that survived SIGTERM, which is what a stub does once its wineserver is gone."""
    entries = table() if table else process_table()
    resolved = current_wine_prefix() if prefix == "auto" else prefix
    leftovers = find_wine_leftovers(entries, resolved)
    pids = leftovers.stubs + leftovers.orphans
    for pid in pids:
        signal_process(pid, signal.SIGKILL)
    if pids:
        print(f"{context}: force-killed {len(pids)} stubborn Wine processes")
    return len(pids)


def reap_wine_leftovers_on_host(
    system: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
    table: TableProvider | None = None,
    prefix: str | None | Literal["auto"] = "auto",
) -> None:
    """Clear the Wine processes a dead game leaves behind on this host, escalating to SIGKILL after a grace."""
    entries = table() if table else process_table(system)
    resolved = current_wine_prefix() if prefix == "auto" else prefix
    if not reap_wine_leftovers(entries, lambda pid: signal_process(pid, signal.SIGTERM), resolved):
        return
    sleep(WINE_STUB_KILL_GRACE_SECONDS)
    force_kill_wine_leftovers("quit", prefix=resolved, table=table)


def steam_client_pids(table: list[ProcessInfo]) -> list[int]:
    return [info.pid for info in table if is_steam_client(info)]


def steam_shutdown_launcher(lookup: Callable[[str], str | None] = shutil.which) -> list[str] | None:
    """How to ask this host's Steam client down, native binary first and Flatpak second; None when neither is installed."""
    if lookup("steam"):
        return ["steam", STEAM_SHUTDOWN_REQUEST]
    if lookup("flatpak"):
        return ["flatpak", "run", STEAM_FLATPAK_ID, STEAM_SHUTDOWN_REQUEST]
    return None


def request_steam_shutdown(launcher: list[str]) -> None:
    subprocess.run(launcher, capture_output=True, text=True, timeout=10, check=False)


def stop_steam_client(
    timeout: float = STEAM_EXIT_TIMEOUT_SECONDS,
    table: TableProvider | None = None,
    request: Callable[[list[str]], None] = request_steam_shutdown,
    launcher: list[str] | None | Literal["auto"] = "auto",
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    killer: Callable[[int, int], None] | None = None,
) -> bool:
    """Shut the Steam client down: ask it first, then signal only the pids this call listed. Opt-in, because a live client is usually wanted."""
    read = table or process_table
    listed = steam_client_pids(read())
    if not listed:
        print("stop-steam: Steam is not running")
        return True
    command = steam_shutdown_launcher() if launcher == "auto" else launcher
    if command:
        try:
            request(command)
        except (OSError, subprocess.SubprocessError):
            print("stop-steam: the shutdown request did not run; escalating to signals", file=sys.stderr)

    def live() -> list[int]:
        return [pid for pid in steam_client_pids(read()) if pid in listed]

    def settle(deadline: float) -> list[int]:
        while live() and now() < deadline:
            sleep(POLL_SECONDS)
        return live()

    if not settle(now() + timeout):
        print(f"stop-steam: stopped {len(listed)} Steam process(es)")
        return True
    for pid in live():
        signal_process(pid, signal.SIGTERM, killer)
    if not settle(now() + min(timeout, STEAM_EXIT_TIMEOUT_SECONDS)):
        print(f"stop-steam: stopped {len(listed)} Steam process(es) after SIGTERM")
        return True
    stubborn = live()
    for pid in stubborn:
        signal_process(pid, signal.SIGKILL, killer)
    settle(now() + WINE_STUB_KILL_GRACE_SECONDS)
    print(f"stop-steam: force-killed {len(stubborn)} stubborn Steam process(es)")
    return not live()


def find_harness_pids(table: list[ProcessInfo]) -> list[int]:
    """Pids of any Windows process running out of the game directory; the game plus helpers such as its crash handler."""
    return [info.pid for info in table if is_megabonk_helper(info)]


def force_kill_games(context: str = "quit", table: TableProvider | None = None) -> int:
    """SIGKILL every process running out of the game directory; the escalation for a game whose main thread stopped polling the harness."""
    entries = table() if table else process_table()
    pids = find_harness_pids(entries)
    for pid in pids:
        signal_process(pid, signal.SIGKILL)
    if pids:
        print(f"{context}: force-killed {len(pids)} game processes")
    return len(pids)


def clear_harness_queue(harness: Path) -> None:
    """Drop leftover command, outcome and result files so a fresh session never replays a previous one's queue."""
    for folder in ("commands", "processing", "done", "rejected", "results"):
        for entry in (harness / folder).glob("*"):
            entry.unlink(missing_ok=True)


def quit_game(
    harness: Path,
    timeout: float,
    force_kill: Callable[[], int] = force_kill_games,
    stop_steam: bool = False,
    stop_menu: bool = False,
) -> bool:
    """Ask the game to quit and block until its process is gone; a game that is not running counts as quit. A game whose main thread stopped polling (an editor left idle can have its window suspended) never answers, so it is force-killed. The Steam client and the menu input service outlive the game by design, so they are only torn down when asked for."""
    def finish() -> bool:
        reap_wine_leftovers_on_host()
        if stop_menu:
            stop_menu_service(timeout)
        if stop_steam:
            stop_steam_client(timeout)
        return True

    if not running_game_pids():
        print("quit: game not running")
    elif not send(harness, build_command("quit"), timeout):
        if wait_for_exit(timeout=timeout):
            print("quit: game exited")
            return finish()
        force_kill()
        if not wait_for_exit(timeout=timeout):
            print(f"quit: game still running after force kill (pids {running_game_pids()})", file=sys.stderr)
            return False
        print("quit: game exited")
    else:
        print("quit: game exited")
    return finish()


def request_result(harness: Path, payload: dict[str, object], timeout: float) -> tuple[str, dict | None]:
    """Send a command and wait; returns the outcome ('done', 'rejected' or 'timeout') and the parsed result."""
    sent = write_command(harness / "commands", payload)
    outcome = wait_for_outcome(harness, sent.name, timeout)
    return outcome, read_result(harness, sent.name)


def press_refusal_is_transient(result: dict | None) -> bool:
    error = result.get("error") if result is not None and result.get("ok") is False else None
    return isinstance(error, str) and any(marker in error for marker in PRESS_REFUSAL_MARKERS)


def request_press(
    harness: Path,
    payload: dict[str, object],
    timeout: float,
    wait: float | None = None,
    request: Callable[[Path, dict[str, object], float], tuple[str, dict | None]] = request_result,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[str, dict | None]:
    """request_result for the death-screen press verbs: the death screen shows Confirm and then the summary a few seconds after the kill, so a gate refusal is retried until `wait` seconds pass before it is reported."""
    wait = PRESS_WAIT_SECONDS if wait is None else wait
    deadline = clock() + wait
    outcome, result = request(harness, payload, timeout)
    while press_refusal_is_transient(result) and clock() < deadline:
        sleep(PRESS_POLL_INTERVAL)
        outcome, result = request(harness, payload, timeout)
    if press_refusal_is_transient(result):
        result["error"] = f"{result['error']} (still refused after waiting {wait:g}s)"
    return outcome, result


def send_for_result(
    harness: Path,
    payload: dict[str, object],
    timeout: float,
    request: Callable[[Path, dict[str, object], float], tuple[str, dict | None]] = request_result,
) -> tuple[bool, dict | None]:
    """Send a command; ok is false on a rejected or timed-out command or a result with ok:false."""
    outcome, result = request(harness, payload, timeout)
    print(f"{payload['command']}: {outcome}")
    if result is not None and result.get("ok") is False:
        print(f"{payload['command']}: {result.get('error')}", file=sys.stderr)
        return False, result
    return outcome == "done", result


def send(harness: Path, payload: dict[str, object], timeout: float) -> bool:
    return send_for_result(harness, payload, timeout)[0]


def steam_ready_verdict(harness: Path, timeout: float) -> str | None:
    """'ready', 'not-ready', or None when the game gave no definite answer; a mod that returns no result counts as ready."""
    ok, result = send_for_result(harness, build_command("steam-ready"), timeout)
    payload = (result or {}).get("result")
    if not ok:
        return None
    if isinstance(payload, dict) and payload.get("ready") is False:
        return "not-ready"
    return "ready"


def send_steam_ready(harness: Path, timeout: float) -> bool:
    """True when the game's Steamworks client is up; a mod that returns no result counts as ready."""
    return steam_ready_verdict(harness, timeout) == "ready"


def send_printing_result(
    harness: Path,
    payload: dict[str, object],
    timeout: float,
    request: Callable[[Path, dict[str, object], float], tuple[str, dict | None]] = request_result,
) -> bool:
    ok, result = send_for_result(harness, payload, timeout, request)
    if ok and result is not None:
        print(json.dumps(result.get("result")))
    elif ok:
        print(f"{payload['command']}: no result file written", file=sys.stderr)
    return ok and result is not None


def send_console(harness: Path, line: str, timeout: float) -> bool:
    ok, result = send_for_result(harness, build_console_command(line), timeout)
    if not ok:
        return False
    reply = (result or {}).get("result")
    if not isinstance(reply, dict) or not isinstance(reply.get("lines"), list):
        print("console: no reply lines returned", file=sys.stderr)
        return False
    for printed in reply["lines"]:
        print(printed)
    return reply.get("ok") is True


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


def default_menu_socket() -> Path:
    root = Path(os.environ.get("XDG_RUNTIME_DIR") or Path.home() / ".cache")
    return root / "megabonk-menu" / "input.sock"


def menu_socket(args: argparse.Namespace) -> Path:
    if args.socket is not None:
        return args.socket.expanduser()
    return default_menu_socket()


def stop_menu_service(timeout: float, path: Path | None = None) -> bool:
    """Stop the OS-level input service and wait for its socket to go; a service that was never started counts as stopped."""
    socket_path = path or default_menu_socket()
    if not socket_path.exists():
        print("menu: input service not running")
        return True
    print(json.dumps(menu_request(socket_path, {"command": "stop"}, timeout)))
    deadline = time.monotonic() + timeout
    while socket_path.exists() and time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
    if socket_path.exists():
        print(f"menu: stop was acknowledged but {socket_path} still exists", file=sys.stderr)
        return False
    return True


def read_menu_batch(source: str) -> list:
    if source == "-":
        text = sys.stdin.read(65537)
    elif source.startswith("@"):
        with Path(source[1:]).open() as batch:
            text = batch.read(65537)
    else:
        text = source
    if len(text.encode()) > 65535:
        raise ValueError("menu: command batch exceeds 64 KiB")
    return validate_batch(json.loads(text))


def menu_remote(args: argparse.Namespace, commands: list | None) -> int:
    if not args.remote_repo or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@:\[\]-]*", args.host):
        raise ValueError("menu: SSH requires a safe host name and an explicit --remote-repo")
    if args.menu_action == "serve":
        raise ValueError("menu: use 'start' instead of serving over SSH")
    repo = args.remote_repo
    directory = '"$HOME"/' + shlex.quote(repo[2:]) if repo.startswith("~/") else shlex.quote(repo)
    remote_out = f".tools/menu-{uuid.uuid4().hex}.png" if args.out else None
    command = [args.remote_python, "scripts/run.py", "--timeout", str(args.timeout), "menu", args.menu_action]
    if commands is not None:
        command.append("-")
        command += ["--settle", str(args.settle)]
    for flag, value in (("--game-dir", args.game_dir), ("--socket", args.socket), ("--display", args.display), ("--out", remote_out)):
        if value is not None:
            command += [flag, str(value)]
    if args.no_gamepad:
        command.append("--no-gamepad")
    ssh = ["ssh", "-oBatchMode=yes", "--", args.host]
    budget = args.timeout * (len(commands or []) + 2) + 10
    result = subprocess.run([*ssh, f"cd {directory} && {shlex.join(command)}"],
                            input=json.dumps(commands) if commands is not None else "", text=True, timeout=budget, check=False)
    if result.returncode or remote_out is None:
        return result.returncode
    download = subprocess.run([*ssh, f"cd {directory} && cat -- {shlex.quote(remote_out)}"], capture_output=True, timeout=args.timeout, check=False)
    if download.returncode or not download.stdout.startswith(PNG_SIGNATURE):
        raise RuntimeError("menu: remote screenshot download failed or did not contain a PNG")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    staging = args.out.with_name(f".{args.out.name}.{uuid.uuid4().hex}.tmp")
    try:
        staging.write_bytes(download.stdout)
        staging.replace(args.out)
    finally:
        staging.unlink(missing_ok=True)
    print(f"menu: downloaded {args.out} (remote evidence: {repo}/{remote_out})")
    return 0


def start_menu_service(args: argparse.Namespace, path: Path) -> bool:
    if path.exists():
        status = menu_request(path, {"command": "status"}, args.timeout)
        raise RuntimeError(f"menu: service already running: {status}; use status/stop first")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    command = [sys.executable, "-m", "megabonk_harness.run", "menu", "serve", "--socket", str(path)]
    display = args.display or os.environ.get("DISPLAY")
    if display:
        command += ["--display", display]
    if args.no_gamepad:
        command.append("--no-gamepad")
    log = path.with_suffix(".log")
    unit = None
    child = None
    if shutil.which("systemd-run"):
        unit = f"megabonk-menu-{uuid.uuid4().hex}"
        launch = ["systemd-run", "--user", "--collect", "--quiet", f"--unit={unit}",
                  f"--working-directory={Path.cwd()}", f"--property=StandardOutput=append:{log}", "--property=StandardError=inherit"]
        if os.environ.get("XAUTHORITY"):
            launch += [f"--setenv=XAUTHORITY={os.environ['XAUTHORITY']}"]
        try:
            launched = subprocess.run([*launch, *command], capture_output=True, text=True, timeout=args.timeout, check=False)
            if launched.returncode:
                raise RuntimeError(f"menu: user service launch failed: {launched.stderr}; a running systemd user manager is required")
        except BaseException:
            try:
                subprocess.run(["systemctl", "--user", "stop", unit], capture_output=True, timeout=5, check=False)
            except (OSError, subprocess.SubprocessError):
                print(f"menu: check cleanup of user service {unit}", file=sys.stderr)
            raise
    else:
        with log.open("ab") as output:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + args.timeout
    try:
        while (child is None or child.poll() is None) and time.monotonic() < deadline:
            try:
                status = menu_request(path, {"command": "status"}, min(args.timeout, 0.5))
                print(json.dumps(status))
                return True
            except RuntimeError:
                time.sleep(POLL_SECONDS)
        detail = log.read_text(errors="replace")[-2000:] if log.exists() else "no service log was written"
        raise RuntimeError(f"menu: input service did not start; see {log}:\n{detail}")
    except BaseException:
        if unit is not None:
            subprocess.run(["systemctl", "--user", "stop", unit], timeout=5, check=False)
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        raise


def run_menu(args: argparse.Namespace) -> int:
    commands = read_menu_batch(args.commands) if args.menu_action == "drive" else None
    if not 0 < args.timeout <= 300 or not 0 <= args.settle <= 10:
        raise ValueError("menu: timeout must be 0–300 seconds (exclusive of 0), settle must be 0–10 seconds")
    if args.host:
        return menu_remote(args, commands)
    if args.remote_repo or args.remote_python != ".venv/bin/python":
        raise ValueError("menu: --remote-repo/--remote-python require --host; refusing to drive the local machine")
    if platform.system() != "Linux":
        raise RuntimeError("menu: OS-level menu input requires Linux; use --host and --remote-repo for an SSH target")
    path = menu_socket(args)
    if args.menu_action == "start":
        return 0 if start_menu_service(args, path) else 1
    if args.menu_action == "serve":
        def terminate(_signum, _frame):
            raise KeyboardInterrupt
        previous = signal.signal(signal.SIGTERM, terminate)
        try:
            serve_menu(path, display=args.display or os.environ.get("DISPLAY"), gamepad=not args.no_gamepad)
        finally:
            signal.signal(signal.SIGTERM, previous)
        return 0
    if args.menu_action == "status":
        print(json.dumps(menu_request(path, {"command": "status"}, args.timeout)))
        return 0
    if args.menu_action == "stop":
        return 0 if stop_menu_service(args.timeout, path) else 1
    game_dir = args.game_dir.expanduser() if args.game_dir else resolve_game_dir(load_lookup())
    harness = game_dir / "harness"
    if (args.out or any(isinstance(command, dict) for command in commands)) and not (harness / "enabled").is_file():
        raise RuntimeError(f"menu: diagnostics/screenshots need the harness enabled at {harness}; input-only batches do not")
    status = menu_request(path, {"command": "status"}, args.timeout)
    if not status.get("gamepad") and any(isinstance(command, list) and command[0] in ("pad", "axis") for command in commands):
        raise ValueError("menu: gamepad is disabled; stop and start without --no-gamepad")
    for command in commands:
        if isinstance(command, dict):
            ok, result = send_for_result(harness, command, args.timeout)
            if not ok:
                return 1
            if result is None:
                raise RuntimeError(f"menu: {command['command']} completed without a diagnostic result file")
            print(json.dumps(result))
        else:
            menu_request(path, command, args.timeout)
        time.sleep(args.settle)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        return 0 if send_screenshot(harness, args.out, args.timeout) else 1
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drive the MegabonkLevels dev harness.")
    parser.add_argument("--timeout", type=float, default=15.0, help="seconds to wait for each command")
    sub = parser.add_subparsers(dest="action", required=True)
    menu = sub.add_parser("menu", help="drive stock Linux menus through OS-level devices, locally or over SSH")
    menu_sub = menu.add_subparsers(dest="menu_action", required=True)
    for verb in ("start", "serve", "status", "stop", "drive"):
        command = menu_sub.add_parser(verb)
        command.add_argument("--host", help="SSH host; runs the target checkout, never the local game")
        command.add_argument("--remote-repo", help="repository path on the SSH host; ~/ is supported")
        command.add_argument("--remote-python", default=".venv/bin/python", help="single interpreter path in the remote checkout's environment")
        command.add_argument("--socket", type=Path, help="target input service socket (default: XDG_RUNTIME_DIR or ~/.cache, under megabonk-menu)")
        command.add_argument("--display", help="target game's X11 display; start defaults to the target DISPLAY")
        command.add_argument("--no-gamepad", action="store_true", help="start keyboard/mouse only, without a virtual controller")
        command.add_argument("--game-dir", type=Path, help="target game directory for diagnostics/screenshots")
        command.add_argument("--settle", type=float, default=0.35, help="seconds between batch actions (0–10)")
        command.set_defaults(out=None)
        if verb == "drive":
            command.add_argument("commands", help="JSON batch, @file, or - to read stdin")
            command.add_argument("--out", type=Path, help="screenshot path on this machine, downloaded when --host is used")
    sub.add_parser("enable")
    sub.add_parser("disable")
    sub.add_parser("clear-console-log", help="delete the console's persisted history and scrollback so the next launch starts empty")
    quit_parser = sub.add_parser("quit")
    add_client_flags(quit_parser)
    teardown_parser = sub.add_parser("teardown", help="quit the game, reap the Wine leftovers, and stop the clients a run leaves behind")
    add_client_flags(teardown_parser)
    sub.add_parser("freeze")
    sub.add_parser("resume")
    sub.add_parser("invulnerable")
    sub.add_parser("vulnerable")
    sub.add_parser("kill")
    sub.add_parser("restart-run", help="run the game's own restart, the death screen's Retry button")
    sub.add_parser("press-death-confirm", help="press Confirm on the death screen, opening the run summary")
    sub.add_parser("press-summary-restart", help="press the run summary's Restart button")
    music = sub.add_parser("music", help="control level music: play, pause, next, prev, track <n>, list, now")
    music.add_argument("music_action", metavar="action", choices=MUSIC_ACTIONS)
    music.add_argument("track", nargs="?", type=int, help="1-based track number, for the track action")
    kill_enemies = sub.add_parser("kill-enemies", help="kill the nearest enemy, all enemies or all bosses through the game's own damage path")
    kill_enemies.add_argument("target", choices=KILL_ENEMY_TARGETS)
    damage = sub.add_parser("damage", help="apply 1–99 damage through the game, bypassing shield; nonlethal by default")
    damage.add_argument("amount", type=damage_amount)
    damage.add_argument("--nonlethal", action=argparse.BooleanOptionalAction, default=True, help="preserve at least 1 HP; --no-nonlethal can end the run")
    sub.add_parser("steam-ready")
    sub.add_parser("state")
    console = sub.add_parser("console", help="run one console line without opening the overlay")
    console.add_argument("line", help="entire console line as one quoted argument")
    sub.add_parser("shader-report")
    character_screen = sub.add_parser("character-screen")
    character_screen.add_argument("state", choices=["on", "off"])
    spawns = sub.add_parser("spawns")
    spawns.add_argument("state", choices=["on", "off"])
    hud = sub.add_parser("hud")
    hud.add_argument("state", choices=["on", "off"])
    coordinates = sub.add_parser("coordinates")
    coordinates.add_argument("state", choices=["on", "off"])
    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("state", choices=["on", "off"])
    cells = sub.add_parser("cells")
    cells.add_argument("state", choices=["on", "off"])
    perf = sub.add_parser("perf")
    perf.add_argument("perf_action", choices=list(PERF_ACTIONS))
    perf.add_argument("--count", type=perf_count, help=f"enemies to spawn around the player (1-{PERF_MAX_ENEMIES}), for 'spawn'")
    perf.add_argument("--value", type=perf_time_scale, help=f"time scale to hold ({PERF_MIN_TIME_SCALE}-{PERF_MAX_TIME_SCALE}) for 'timescale'; omit to release it")
    perf.add_argument("--target", help="for 'toggle': a tick name (KillFloor), a patch probe (EnemyManager.Update), or all")
    perf.add_argument("--enable", action="store_true", help="with 'toggle', 'vsync', 'render', 'physics' or 'animation', turn the target on")
    perf.add_argument("--disable", action="store_true", help="with 'toggle', 'vsync', 'render', 'physics' or 'animation', turn the target off")
    perf.add_argument("--hp", type=perf_hp, help=f"player hit points to park the player at (1-{PERF_MAX_PLAYER_HP}), for 'health'")
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
    mouse.add_argument("verb", choices=["move", "click", "down", "up", "scroll", "clear"])
    mouse.add_argument("position", type=float, nargs="*", metavar="X Y", help="screenshot pixels, origin top left")
    mouse.add_argument("--button", type=int, choices=[0, 1, 2], help="0 left (default), 1 right, 2 middle")
    mouse.add_argument("--delta", type=float, help="wheel notches for scroll, positive up (toward older console lines)")
    ui_tree = sub.add_parser("ui-tree")
    ui_tree.add_argument("position", type=float, nargs="*", metavar="X Y", help="screenshot pixels, origin top left")
    material_dump = sub.add_parser("material-dump")
    material_dump.add_argument("object", nargs="?", help="substring of an object or ancestor name; defaults to Warehouse")
    save_level = sub.add_parser("save-level")
    save_level.add_argument("level", nargs="?", help="level name to save as; defaults to the editor's save field")
    new_level = sub.add_parser("new-level")
    new_level.add_argument("level", nargs="?", help="file name for the new level; defaults to the first free untitled-N")
    new_level.add_argument("--map", type=int, help="eMap value (default 1, Forest)")
    new_level.add_argument("--stage", type=int, help="stage index (default 0)")
    new_level.add_argument("--tier", type=int, help="map tier (default 0)")
    new_level.add_argument("--size", type=int, help="square grid size, at least 3 (default 7)")
    sub.add_parser("list-levels")
    sub.add_parser("palette")
    query_objects = sub.add_parser("query-objects")
    query_objects.add_argument("type", help="UnityEngine.Object type name, e.g. MapData")
    query_objects.add_argument("--fields", nargs="*", metavar="FIELD", help="public fields to read besides name")
    query_objects.add_argument("--depth", type=query_depth, help=f"expand nested assets this many levels deep (0-{MAX_QUERY_DEPTH})")
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
    sub.add_parser("fall-damage", help="report the player's fall-damage inputs: thresholds, FallDamageReduction, fall speed, and both characters' stored values")
    dismiss = sub.add_parser("dismiss-levelup")
    dismiss.add_argument("--choice", type=int, default=0, help="zero-based index of the offered upgrade")
    dismiss_offers = sub.add_parser("dismiss-offers")
    dismiss_offers.add_argument("--choice", type=int, default=None, help="zero-based index of the offered upgrade to pick instead of closing the window")
    dismiss_offers.add_argument("--skip", action="store_true", help="skip the level-up window without choosing; only valid there")
    interact = sub.add_parser("interact")
    interact.add_argument("--type", help="only interactables whose class or object name contains this substring, e.g. Magnet")
    interact.add_argument("--max-distance", type=float, help="only interactables within this many units of the player")
    interact.add_argument("--force", action="store_true", help="call Interact even when the game's CanInteract returns false")
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
    relaunch.add_argument("level", type=Path, nargs="?", default=example_forest_level())
    relaunch.add_argument("--no-level", action="store_true", help="stop at the main menu without loading a level")
    add_load_overrides(relaunch)
    add_client_flags(relaunch)
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
    if args.verb == "scroll" and args.delta is None:
        raise SystemExit("mouse scroll: give --delta")
    if args.verb != "scroll" and args.delta is not None:
        raise SystemExit("mouse: --delta only applies to scroll")
    position = (args.position[0], args.position[1]) if args.position else None
    return build_mouse_command(args.verb, position, args.button, args.delta)


def ui_tree_payload(args: argparse.Namespace) -> dict[str, object]:
    if len(args.position) not in (0, 2):
        raise SystemExit("ui-tree: give both X and Y, or neither")
    return build_ui_tree_command((args.position[0], args.position[1]) if args.position else None)


def material_dump_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_material_dump_command(args.object)


def save_level_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_save_level_command(args.level)


def new_level_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_new_level_command(args.level, args.map, args.stage, args.tier, args.size)


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


def dismiss_offers_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_dismiss_offers_command(args.choice, args.skip)


def interact_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_interact_command(args.type, args.max_distance, args.force)


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


def hud_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_hud_command(args.state == "on")


def coordinates_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_coordinates_command(args.state == "on")


def spawns_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_spawns_command(args.state == "on")


def heartbeat_payload(args: argparse.Namespace) -> dict[str, object]:
    return build_heartbeat_command(args.state == "on")


def perf_payload(args: argparse.Namespace) -> dict[str, object]:
    verb = args.perf_action
    if verb == "spawn" and args.count is None:
        raise SystemExit(f"perf spawn: give --count N (1-{PERF_MAX_ENEMIES})")
    enabled = None
    if verb in ("toggle", "vsync", "render", "physics", "animation"):
        if args.enable == args.disable:
            raise SystemExit(f"perf {verb}: give exactly one of --enable or --disable")
        enabled = args.enable
    if verb == "toggle" and not args.target:
        raise SystemExit("perf toggle: give --target NAME")
    return build_perf_command(
        verb,
        count=args.count,
        value=args.value,
        target=args.target,
        enabled=enabled,
        hp=args.hp if verb == "health" else None,
    )


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


def wine_log_tail(game_dir: Path) -> str:
    """The exit-status line and last lines of the Wine launch log, appended to a startup failure so the reason reaches the terminal, not just the file."""
    wine_log = wine_log_path(game_dir)
    try:
        lines = [line for line in wine_log.read_text(errors="replace").splitlines() if line.strip()]
    except OSError:
        return ""
    if not lines:
        return ""
    exits = [line for line in lines if "game process exited with status" in line]
    rest = [line for line in lines if line not in exits]
    tail = (exits[-1:] + rest[-2:]) if exits else lines[-3:]
    return "\n" + "\n".join(f"  {line}" for line in tail)


def failure_evidence_root() -> Path:
    override = (os.environ.get("MEGABONK_EVIDENCE_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Logs" / "megabonk-relaunch-failures"
    return Path.home() / ".local" / "state" / "megabonk-relaunch-failures"


def player_log_dir(game_dir: Path) -> Path | None:
    prefix = wine_prefix(game_dir)
    if prefix is None:
        return None
    return prefix / "drive_c" / "users" / "crossover" / "AppData" / "LocalLow" / "Ved" / "Megabonk"


def save_failure_evidence(game_dir: Path) -> Path | None:
    """Copy the launch logs out of the game directory the moment a boot dies; every later launch rotates wine-latest.log over its only copy, so evidence must leave the tree to survive. Returns the saved folder, or None when nothing was there to save."""
    sources = [wine_log_path(game_dir), latest_log_path(game_dir)]
    if (players := player_log_dir(game_dir)) is not None:
        sources += [players / "Player.log", players / "Player-prev.log"]
    present = [path for path in sources if path.is_file()]
    if not present:
        return None
    destination = failure_evidence_root() / time.strftime("%Y-%m-%d_%H-%M-%S")
    try:
        destination.mkdir(parents=True, exist_ok=True)
        for path in present:
            shutil.copyfile(path, destination / path.name)
    except OSError:
        return None
    return destination


def game_exited_error(game_dir: Path) -> str:
    saved = save_failure_evidence(game_dir)
    saved_note = f"; evidence saved to {saved}" if saved else ""
    return f"relaunch: game exited during startup (see {latest_log_path(game_dir)}){saved_note}{wine_log_tail(game_dir)}"


CRASH_HANDLER_EXE = "UnityCrashHandler64.exe"


def unity_crash_handler_diag(game_dir: Path, diag: bool) -> None:
    """Hide Unity's crash handler for exception tracing, or restore it for a normal launch."""
    handler = game_dir / CRASH_HANDLER_EXE
    disabled = handler.with_name(f"{CRASH_HANDLER_EXE}.disabled")
    if diag:
        if handler.exists():
            handler.replace(disabled)
        os.environ["MEGABONK_WINEDEBUG_EXTRA"] = "+seh"
        subprocess.run(
            [str(wine_bin()), "reg", "add", "HKCU\\Software\\Wine\\WineDbg", "/v", "ShowCrashDialog", "/t", "REG_DWORD", "/d", "0", "/f"],
            env={**os.environ, "WINEPREFIX": str(resolve_wine_prefix())},
            capture_output=True,
            check=False,
        )
    else:
        if disabled.exists():
            disabled.replace(handler)
        os.environ.pop("MEGABONK_WINEDEBUG_EXTRA", None)


def relaunch(
    harness: Path,
    game_dir: Path,
    level: Path | None,
    timeout: float,
    task: str,
    on_step: Callable[[str], None],
    on_error: Callable[[str], None],
    overrides: Mapping[str, int | str | bool] | None = None,
    spawns: bool = True,
    invulnerable: bool = False,
    feathers: int = 2,
    diag: bool = False,
    stop_steam: bool = False,
    stop_menu: bool = False,
    is_alive: Callable[[], bool] = game_is_running,
) -> bool:
    """Quit, relaunch, wait for the harness and Steamworks, then load the level, go invulnerable if asked, set the Feathers amount unless it is 0, stop enemy spawns unless spawns is set, and enter editor. A level of None stops at the main menu once Steamworks is ready. A game that stays not-ready but keeps answering (an offline run with the Steam stub) continues after a grace period; one that stops answering or exits fails. diag hides Unity's crash handler and traces Wine exceptions so a native fault reports itself. Steam and the menu input service are stopped after the quit only when stop_steam or stop_menu is set."""
    started = time.time()

    def prepare_harness() -> str | None:
        """Quit, clear the stale harness queue, relaunch, and wait for the new session's harness to enable; the previous session's log must not satisfy the wait."""
        if not quit_game(harness, timeout, stop_steam=stop_steam, stop_menu=stop_menu):
            return "relaunch: harness did not become ready"
        if not wait_for_wineserver_to_exit():
            return "relaunch: wineserver did not exit before launch"
        clear_harness_queue(harness)
        unity_crash_handler_diag(game_dir, diag)
        on_step("relaunch: starting game")
        launched = time.time()
        if not launch_game(task):
            return "relaunch: harness did not become ready"
        on_step("relaunch: waiting for harness")
        grace_until = time.monotonic() + GAME_STARTUP_GRACE_SECONDS
        starting_up = lambda: is_alive() or time.monotonic() < grace_until
        if wait_for_log_line(latest_log_path(game_dir), HARNESS_ENABLED_LINE, launched, relaunch_timeout(timeout), alive=starting_up):
            return None
        return game_exited_error(game_dir) if not is_alive() else "relaunch: harness did not become ready"

    def wait_for_steamworks() -> str | None:
        on_step("relaunch: waiting for Steamworks")
        match wait_for_steamworks_ready(
            lambda: steam_ready_verdict(harness, min(timeout, 2.0)),
            relaunch_timeout(timeout),
            alive=is_alive,
        ):
            case "ready":
                return None
            case "offline":
                on_step("relaunch: Steamworks not ready (offline run); continuing")
                return None
            case "dead":
                return game_exited_error(game_dir)
            case _:
                return "relaunch: Steamworks did not become ready"

    for step in (prepare_harness, wait_for_steamworks):
        match step():
            case str() as error:
                on_error(error)
                force_kill_games("relaunch")
                reap_wine_leftovers_on_host()
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
    if args.action == "menu":
        try:
            return run_menu(args)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"{error}", file=sys.stderr)
            return 1
    game_dir = resolve_game_dir(load_lookup())
    harness = game_dir / "harness"

    if args.action in ("enable", "disable"):
        set_enabled(game_dir, args.action == "enable")
        print(f"harness {args.action}d at {harness}")
        return 0

    if args.action == "clear-console-log":
        print(f"console log {'removed' if clear_console_log(game_dir) else 'not present'} at {console_log_path(game_dir)}")
        return 0

    if args.action == "teardown":
        ok = quit_game(harness, args.timeout, stop_steam=args.stop_steam, stop_menu=args.stop_menu)
        return 0 if ok else 1

    if not (harness / "enabled").is_file():
        print(f"harness not enabled at {harness}; run 'run.py enable' and relaunch the game", file=sys.stderr)
        return 2

    match args.action:
        case "load":
            ok = send(harness, load_level_payload(args), args.timeout)
        case "bundle":
            ok = send_printing_result(harness, build_command("load-bundle", to_game_path(args.bundle.resolve())), args.timeout)
        case "screenshot":
            ok = send_screenshot(harness, args.out, args.timeout)
        case "quit":
            ok = quit_game(harness, args.timeout, stop_steam=args.stop_steam, stop_menu=args.stop_menu)
        case "steam-ready":
            ok = send_steam_ready(harness, args.timeout)
        case "freeze" | "resume" | "invulnerable" | "vulnerable" | "kill" | "restart-run":
            ok = send(harness, build_command(args.action), args.timeout)
        case "state":
            ok = send_printing_result(harness, build_command("state"), args.timeout)
        case "console":
            try:
                ok = send_console(harness, args.line, args.timeout)
            except ValueError as error:
                raise SystemExit(str(error)) from error
        case "press-death-confirm" | "press-summary-restart":
            ok = send_printing_result(harness, build_command(args.action), args.timeout, request=request_press)
        case "music":
            try:
                payload = build_music_command(args.music_action, args.track)
            except ValueError as error:
                raise SystemExit(str(error)) from error
            ok = send_printing_result(harness, payload, args.timeout)
        case "kill-enemies":
            ok = send_printing_result(harness, build_kill_enemies_command(args.target), args.timeout)
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
        case "new-level":
            ok = send_printing_result(harness, new_level_payload(args), args.timeout)
        case "list-levels":
            ok = send_printing_result(harness, build_command("list-levels"), args.timeout)
        case "palette":
            ok = send_printing_result(harness, build_command("palette"), args.timeout)
        case "query-objects":
            ok = send_printing_result(harness, query_objects_payload(args), args.timeout)
        case "click-widget":
            ok = send_printing_result(harness, click_widget_payload(args), args.timeout)
        case "teleport":
            ok = send_printing_result(harness, teleport_payload(args), args.timeout)
        case "item":
            ok = send_printing_result(harness, item_payload(args), args.timeout)
        case "grind-slide":
            ok = send_printing_result(harness, grind_slide_payload(args), args.timeout)
        case "fall-damage":
            ok = send_printing_result(harness, build_fall_damage_command(), args.timeout)
        case "dismiss-levelup":
            ok = send_printing_result(harness, dismiss_levelup_payload(args), args.timeout)
        case "dismiss-offers":
            ok = send_printing_result(harness, dismiss_offers_payload(args), args.timeout)
        case "interact":
            ok = send_printing_result(harness, interact_payload(args), args.timeout)
        case "music-probe":
            ok = send_printing_result(harness, music_probe_payload(args), args.timeout)
        case "character-screen":
            ok = send(harness, character_screen_payload(args), args.timeout)
        case "spawns":
            ok = send(harness, spawns_payload(args), args.timeout)
        case "hud":
            ok = send(harness, hud_payload(args), args.timeout)
        case "coordinates":
            ok = send_printing_result(harness, coordinates_payload(args), args.timeout)
        case "heartbeat":
            ok = send(harness, heartbeat_payload(args), args.timeout)
        case "cells":
            ok = send(harness, cells_payload(args), args.timeout)
        case "perf":
            ok = send_printing_result(harness, perf_payload(args), args.timeout)
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
                diag=resolve_relaunch_diag(load_lookup()),
                stop_steam=args.stop_steam,
                stop_menu=args.stop_menu,
            )
    return 0 if ok else 1


def run_main(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except KeyboardInterrupt:
        print("run.py: interrupted", file=sys.stderr)
        return 130
    except CheckoutNotFound as error:
        print(f"run.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_main())
