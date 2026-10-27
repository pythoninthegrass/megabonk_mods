#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#     "mcp>=2.3,<3",
#     "python-decouple>=3.8",
#     "pillow>=11",
# ]
# [tool.uv]
# exclude-newer = "2026-10-31T00:00:00Z"
# ///

# pyright: reportMissingImports=false

"""
MCP server over the MegabonkLevels dev harness (see docs/development.md). Exposes the harness commands as
typed tools so an agent can drive the game without shelling out to run.py, and returns screenshots as inline
image content. stdout is the MCP protocol channel: nothing here may print to it.

Run: uv run --script scripts/mcp_server.py
"""

import anyio
import io
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from mcp.server import MCPServer
from mcp.server.mcpserver import Context, Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PilImage

TIMEOUT = 15.0
LAUNCH_MARKER = "DevHarness: enabled"
DEFAULT_SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / ".tools" / "evidence"
LOG_POLL_INTERVAL = 0.2
# Mirrors KeyNames.All in src/MegabonkLevels.Mod/key_names.cs; a test keeps the two in step.
KEY_NAMES = (
    *"ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    *(f"Alpha{i}" for i in range(10)),
    *(f"Keypad{i}" for i in range(10)),
    *(f"F{i}" for i in range(1, 13)),
    "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "Escape", "Return", "Backspace", "Delete", "Space", "Tab",
    "LeftShift", "RightShift", "LeftControl", "RightControl", "LeftAlt", "RightAlt",
)  # fmt: skip

mcp = MCPServer("megabonk")


def _game_dir() -> Path:
    return run.resolve_game_dir(run.load_lookup())


def _harness() -> Path:
    return _game_dir() / "harness"


async def _request(harness: Path, payload: dict[str, object], timeout: float) -> dict | None:
    """Send a harness command off the event loop; raise ToolError on a rejection, a timeout or an ok:false result."""
    outcome, result = await anyio.to_thread.run_sync(run.request_result, harness, payload, timeout)
    if outcome == "done" and not (result is not None and result.get("ok") is False):
        return result
    error = result.get("error") if result is not None else None
    raise ToolError(error if error else f"{payload['command']} {outcome}")


@mcp.tool()
async def paths() -> dict[str, str]:
    """Return the resolved game_dir, harness folder, latest_log path and levels_dir (where the editor saves custom levels), so harness command files can be written without hand-typing the prefix path."""
    game = _game_dir()
    return {
        "game_dir": str(game),
        "harness": str(game / "harness"),
        "latest_log": str(run.latest_log_path(game)),
        "levels_dir": str(game / "UserData" / "Levels"),
    }


@mcp.tool()
async def relaunch(ctx: Context, level: str | None = None) -> dict | None:
    """Quit and relaunch the game, load a level, go invulnerable and enter editor; returns the final state."""
    game_dir = _game_dir()
    harness = game_dir / "harness"
    level_path = Path(level) if level else run.TEST_FOREST_LEVEL
    task = run.launch_task(run.resolve_macos_runtime(run.load_lookup()))
    errors: list[str] = []
    progress = {"step": 0}

    def on_step(message: str) -> None:
        progress["step"] += 1
        try:
            anyio.from_thread.run(ctx.report_progress, float(progress["step"]), None, message)
        except Exception:
            pass

    ok = await anyio.to_thread.run_sync(run.relaunch, harness, game_dir, level_path, TIMEOUT, task, on_step, errors.append)
    if not ok:
        raise ToolError("; ".join(errors) if errors else "relaunch failed")
    return await _request(harness, run.build_command("state"), TIMEOUT)


@mcp.tool()
async def load(level: str) -> dict | None:
    """Load a level file and start it."""
    payload = run.build_command("load-level", run.to_game_path(Path(level).resolve()))
    return await _request(_harness(), payload, TIMEOUT)


@mcp.tool()
async def quit() -> bool:
    """Quit the game and wait for the process to exit; a game that is not running counts as quit."""
    harness = _harness()
    if not await anyio.to_thread.run_sync(run.running_game_pids):
        return True
    await _request(harness, run.build_command("quit"), TIMEOUT)
    return await anyio.to_thread.run_sync(run.wait_for_exit)


@mcp.tool()
async def screenshot(
    *,
    directory: str | None = None,
    filename: str | None = None,
    overwrite: bool = False,
    scale: float | None = None,
    crop: list[int] | None = None,
) -> list[Image | str]:
    """Save a PNG (default: timestamped name in the repo's gitignored .tools/evidence), returning inline image and absolute path. Creates directories; refuses to replace an existing file unless overwrite is true. filename must be a single .png basename. To cut token cost, crop [x, y, width, height] (screenshot pixels) and scale (0 to 1] shrink the inline image only; the saved file is the full capture."""
    if filename is not None and (
        not filename
        or any(c in filename for c in '/\\\x00<>:"|?*')
        or any(ord(c) < 32 for c in filename)
        or not filename.lower().endswith(".png")
    ):
        raise ToolError("screenshot: filename must be a single .png basename without path separators or invalid characters")
    if scale is not None and not 0 < scale <= 1:
        raise ToolError("screenshot: scale must be greater than 0 and at most 1")
    if crop is not None and (len(crop) != 4 or crop[0] < 0 or crop[1] < 0 or crop[2] <= 0 or crop[3] <= 0):
        raise ToolError("screenshot: crop must be [x, y, width, height] with x and y >= 0 and positive width and height")
    harness = _harness()
    try:
        folder = Path(directory if directory is not None else DEFAULT_SCREENSHOT_DIR).resolve()
        out = folder / (filename if filename is not None else f"megabonk-{time.time_ns()}.png")
        if not overwrite and (out.exists() or out.is_symlink()):
            raise FileExistsError(f"{out} already exists")
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".megabonk-", dir=folder) as staging:
            capture = Path(staging) / "capture.png"
            await _request(harness, run.build_command("screenshot", run.to_game_path(capture)), TIMEOUT)
            captured = await anyio.to_thread.run_sync(run.wait_for_png, capture, TIMEOUT)
            if not captured:
                raise ToolError(f"screenshot: no valid PNG at {capture} after {TIMEOUT}s; retry the capture")
            image = Image(data=_shrink_png(capture.read_bytes(), scale, crop), format="png")
            if overwrite:
                os.replace(capture, out)
            else:
                out.hardlink_to(capture)
        return [image, f"Saved screenshot to {out}"]
    except FileExistsError as exc:
        raise ToolError(f"screenshot: destination exists; choose another filename or directory: {exc}") from exc
    except (OSError, ValueError) as exc:
        raise ToolError(f"screenshot: cannot save PNG; check directory, filename and write permissions: {exc}") from exc


def _shrink_png(data: bytes, scale: float | None, crop: list[int] | None) -> bytes:
    if scale is None and crop is None:
        return data
    with PilImage.open(io.BytesIO(data)) as source:
        image = source.convert("RGBA")
    if crop is not None:
        x, y, width, height = crop
        if x + width > image.width or y + height > image.height:
            raise ToolError(f"screenshot: crop {crop} is outside the {image.width}x{image.height} capture")
        image = image.crop((x, y, x + width, y + height))
    if scale is not None:
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), PilImage.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@mcp.tool()
async def state() -> dict | None:
    """Return the game's current state (level, editor, player, tool, selection)."""
    return await _request(_harness(), run.build_command("state"), TIMEOUT)


@mcp.tool()
async def editor(on: bool) -> dict | None:
    """Enter or leave editor mode (frozen run, free-fly camera), like pressing F8."""
    return await _request(_harness(), run.build_editor_command(on), TIMEOUT)


@mcp.tool()
async def freeze() -> dict | None:
    """Pause gameplay through MyTime.Pause."""
    return await _request(_harness(), run.build_command("freeze"), TIMEOUT)


@mcp.tool()
async def resume() -> dict | None:
    """Unpause gameplay through MyTime.Unpause."""
    return await _request(_harness(), run.build_command("resume"), TIMEOUT)


@mcp.tool()
async def invulnerable(on: bool) -> dict | None:
    """Make the player survive enemy damage (on) or restore normal damage (off)."""
    return await _request(_harness(), run.build_command("invulnerable" if on else "vulnerable"), TIMEOUT)


@mcp.tool()
async def camera(position: list[float] | None = None, rotation: list[float] | None = None, clear: bool = False) -> dict | None:
    """Hold the camera at a world pose (position and rotation euler degrees), or return it to the game with clear."""
    if clear:
        payload = run.build_command("camera-clear")
    elif position is not None and rotation is not None:
        payload = run.build_camera_command(tuple(position), tuple(rotation))
    else:
        raise ToolError("camera: give position and rotation, or clear=true")
    return await _request(_harness(), payload, TIMEOUT)


@mcp.tool()
async def key(key: str, modifiers: list[str] | None = None, action: Literal["tap", "down", "up"] = "tap") -> dict | None:
    """Inject a key for the editor (not the game's own input). Valid names are listed under "Key, mouse and type commands" in docs/development.md (A-Z, Alpha0-9, F1-F12, arrows, Escape, Return, Space, Tab, shift/control/alt). tap presses and releases over the next frames (one frame down, one up; with modifiers they are held around it, four frames); down holds until up. modifiers only apply to tap. Returns once the mod queued it, so take a screenshot after a moment to see the effect."""
    if modifiers and action != "tap":
        raise ToolError("key: modifiers are only valid with action=tap")
    unknown = [name for name in (key, *(modifiers or [])) if name not in KEY_NAMES]
    if unknown:
        raise ToolError(f"key: the mod does not accept {unknown}; valid names: {', '.join(KEY_NAMES)}")
    return await _request(_harness(), run.build_key_command(action, key, modifiers), TIMEOUT)


@mcp.tool()
async def mouse(
    action: Literal["move", "click", "down", "up", "clear"],
    x: float | None = None,
    y: float | None = None,
    button: int = 0,
) -> dict | None:
    """Inject mouse input for the editor. x and y are screenshot pixels with the origin at the top left, the same space as the screenshot tool and the screen field of state. move needs x and y; click, down and up take an optional x and y (both or neither) that move the pointer first, and button 0 left, 1 right, 2 middle; clear returns the pointer to the real cursor. A click is one frame down then one frame up, so a screenshot straight after may predate its effect."""
    if (x is None) != (y is None):
        raise ToolError("mouse: give both or neither of x and y")
    if action == "move" and x is None:
        raise ToolError("mouse: move needs x and y")
    position = (x, y) if x is not None and y is not None else None
    payload = run.build_mouse_command(action, position, button if action in ("click", "down", "up") else None)
    return await _request(_harness(), payload, TIMEOUT)


@mcp.tool()
async def ui_tree(x: float | None = None, y: float | None = None) -> dict | None:
    """List the editor's widgets (toolbar buttons and tools, load list, palette entries and tabs) as {name, x, y, width, height, enabled} in screenshot pixels, the space of the screenshot and mouse tools. Give both x and y to also get `at`, the name of the first listed widget under that pixel (null over the world). Names are what click_widget takes; enabled is false for a button that ignores clicks (Undo with nothing to undo); anything on another palette page is not listed. Needs editor mode."""
    if (x is None) != (y is None):
        raise ToolError("ui_tree: give both or neither of x and y")
    position = (x, y) if x is not None and y is not None else None
    return await _request(_harness(), run.build_ui_tree_command(position), TIMEOUT)


@mcp.tool()
async def save_level(level: str | None = None) -> dict | None:
    """Save the editor's level like the Save button, optionally as `level` (normalized to a safe *.mblevel.json file name; omitted, the save field's text is used). Returns {name, path, edits}. Needs editor mode with a live run; a failed write is an error."""
    return await _request(_harness(), run.build_save_level_command(level), TIMEOUT)


@mcp.tool()
async def list_levels() -> dict | None:
    """List the saved custom-level files as {directory, levels}; the names are what the editor's Load list shows and what a load needs after the directory."""
    return await _request(_harness(), run.build_command("list-levels"), TIMEOUT)


@mcp.tool()
async def click_widget(name: str) -> dict | None:
    """Left-click the centre of the named editor widget, e.g. Save, Undo, Tab:All, Palette:<entry id>; take names from ui_tree (case-insensitive). Returns the widget's rect. An unknown name is an error that lists the known names, and a disabled widget is an error too. Like mouse click, the effect lands over the next frames, so read state or take a screenshot after a moment. Tools are not widgets: switch them with key (Alpha1 to Alpha6). Needs editor mode."""
    return await _request(_harness(), run.build_click_widget_command(name), TIMEOUT)


@mcp.tool()
async def type_text(text: str) -> dict | None:
    """Type 1 to 200 characters into the focused editor text field, one character per frame; \\b is backspace and \\n is return. A screenshot straight after may show only part of the text."""
    return await _request(_harness(), run.build_type_command(text), TIMEOUT)


@mcp.tool()
async def teleport(position: list[float] | None = None, cell: list[int] | None = None) -> dict | None:
    """Move the player. Give exactly one of position (world [x, y, z], the feet point) or cell ([cx, cz], the grid used by state; needs a loaded custom level). Returns the body position and cell at the moment of the call; the transform catches up within about a second, so wait before reading state. Targets below the kill floor are rejected."""
    if (position is None) == (cell is None):
        raise ToolError("teleport: give exactly one of position or cell")
    if position is not None and len(position) != 3:
        raise ToolError("teleport: position needs three numbers")
    if cell is not None and len(cell) != 2:
        raise ToolError("teleport: cell needs two integers")
    payload = run.build_teleport_command(
        tuple(position) if position is not None else None, tuple(cell) if cell is not None else None
    )
    return await _request(_harness(), payload, TIMEOUT)


@mcp.tool()
async def dismiss_levelup(choice: int = 0) -> dict | None:
    """Pick the upgrade at the zero-based index choice in the open level-up dialog without a click. With no dialog open it succeeds and changes nothing (dialogWasOpen false)."""
    return await _request(_harness(), run.build_dismiss_levelup_command(choice), TIMEOUT)


@mcp.tool()
async def log_tail(pattern: str | None = None, since_launch: bool = True, max_lines: int = 50) -> list[str]:
    """Read the game's Latest.log: filter to the current session, to lines matching a regex, and to the last N lines."""
    try:
        lines = run.latest_log_path(_game_dir()).read_text(errors="ignore").splitlines()
    except OSError:
        return []
    if since_launch:
        starts = [i for i, line in enumerate(lines) if LAUNCH_MARKER in line]
        if starts:
            lines = lines[starts[-1] :]
    if pattern is not None:
        regex = re.compile(pattern)
        lines = [line for line in lines if regex.search(line)]
    return lines[-max_lines:]


@mcp.tool()
async def log_wait(pattern: str, timeout: float = 30.0, since_launch: bool = True) -> str:
    """Block until Latest.log has a line matching the regex pattern, then return that line; a tool error on timeout. since_launch (default true) only considers lines after the last `DevHarness: enabled`. Use it after load or relaunch instead of sleeping, e.g. pattern `KillFloor: armed`."""
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ToolError(f"log_wait: invalid pattern {pattern!r}: {exc}") from exc
    log = run.latest_log_path(_game_dir())
    deadline = time.monotonic() + timeout
    while True:
        match = await anyio.to_thread.run_sync(_first_log_match, log, regex, since_launch)
        if match is not None:
            return match
        if time.monotonic() >= deadline:
            raise ToolError(f"log_wait: timeout after {timeout}s waiting for {pattern!r} in {log}")
        await anyio.sleep(LOG_POLL_INTERVAL)


def _first_log_match(log: Path, regex: re.Pattern[str], since_launch: bool) -> str | None:
    try:
        lines = log.read_text(errors="ignore").splitlines()
    except OSError:
        return None
    if since_launch:
        starts = [i for i, line in enumerate(lines) if LAUNCH_MARKER in line]
        if starts:
            lines = lines[starts[-1] :]
    return next((line for line in lines if regex.search(line)), None)


if __name__ == "__main__":
    mcp.run()
