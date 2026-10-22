#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#     "mcp>=2.3,<3",
#     "python-decouple>=3.8",
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
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from mcp.server import MCPServer
from mcp.server.mcpserver import Context, Image
from mcp.server.mcpserver.exceptions import ToolError

TIMEOUT = 15.0
LAUNCH_MARKER = "DevHarness: enabled"

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

    ok = await anyio.to_thread.run_sync(
        run.relaunch, harness, game_dir, level_path, TIMEOUT, task, on_step, errors.append
    )
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
async def screenshot() -> Image:
    """Capture the game's current frame and return it as an inline PNG."""
    harness = _harness()
    out = Path(tempfile.gettempdir()) / f"megabonk-{time.time_ns()}.png"
    out.unlink(missing_ok=True)
    await _request(harness, run.build_command("screenshot", run.to_game_path(out)), TIMEOUT)
    captured = await anyio.to_thread.run_sync(run.wait_for_png, out, TIMEOUT)
    if not captured:
        raise ToolError(f"screenshot: no valid PNG at {out} after {TIMEOUT}s")
    return Image(path=str(out))


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
async def camera(
    position: list[float] | None = None, rotation: list[float] | None = None, clear: bool = False
) -> dict | None:
    """Hold the camera at a world pose (position and rotation euler degrees), or return it to the game with clear."""
    if clear:
        payload = run.build_command("camera-clear")
    elif position is not None and rotation is not None:
        payload = run.build_camera_command(tuple(position), tuple(rotation))
    else:
        raise ToolError("camera: give position and rotation, or clear=true")
    return await _request(_harness(), payload, TIMEOUT)


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


if __name__ == "__main__":
    mcp.run()
