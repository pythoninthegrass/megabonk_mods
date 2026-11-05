"""Self-test for scripts/mcp_server.py, driving the tools through the in-memory MCP client."""

import base64
import json
import mcp_server
import pytest
import re
import run
import struct
import threading
import time
import toon_format
import zlib
from mcp.client import Client
from pathlib import Path

pytestmark = pytest.mark.anyio

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def tiny_png(width: int = 1, height: int = 1) -> bytes:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress((b"\x00" + b"\x00\x00\x00\x00" * width) * height))
    return PNG_SIGNATURE + ihdr + idat + chunk(b"IEND", b"")


def host_path(game_path: str) -> Path:
    """Invert to_game_path so the fake mod can write where the game would."""
    if game_path.startswith("Z:"):
        return Path(game_path[2:].replace("\\", "/"))
    return Path(game_path)


def setup_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    game = tmp_path / "game"
    harness = game / "harness"
    for folder in ("commands", "done", "rejected", "results"):
        (harness / folder).mkdir(parents=True)
    monkeypatch.setenv("MEGABONK_GAME_DIR", str(game))
    monkeypatch.setattr(mcp_server, "DEFAULT_SCREENSHOT_DIR", tmp_path / "evidence")
    return harness


def start_fake_mod(harness: Path, responder) -> threading.Event:
    """Background thread that answers each command file like the in-game mod would."""
    stop = threading.Event()

    def loop() -> None:
        while not stop.is_set():
            for command in sorted((harness / "commands").glob("*.json")):
                payload = json.loads(command.read_text())
                outcome, body = responder(payload)
                if body is not None:
                    (harness / "results" / command.name).write_text(body)
                command.rename(harness / outcome / command.name)
            time.sleep(0.01)

    threading.Thread(target=loop, daemon=True).start()
    return stop


def ok_result(payload: dict, result: dict | None = None) -> tuple[str, str]:
    body = {"command": payload["command"], "ok": True}
    if result is not None:
        body["result"] = result
    return "done", json.dumps(body)


async def test_state_tool_returns_the_result_and_writes_nothing_to_stdout(tmp_path, monkeypatch, capsys) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    stop = start_fake_mod(harness, lambda p: ok_result(p, {"editor": True, "player": None}))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("state", {})
    finally:
        stop.set()
    assert not result.is_error
    assert json.loads(result.content[0].text) == {
        "command": "state",
        "ok": True,
        "result": {"editor": True, "player": None},
    }
    assert capsys.readouterr().out == ""


async def test_rejected_command_surfaces_the_error_as_a_toolerror(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    rejected = json.dumps({"command": "state", "ok": False, "error": "no player here"})
    stop = start_fake_mod(harness, lambda p: ("rejected", rejected))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("state", {})
    finally:
        stop.set()
    assert result.is_error
    assert "no player here" in result.content[0].text


async def test_timeout_surfaces_as_a_toolerror(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(mcp_server, "TIMEOUT", 0.3)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("state", {})
    assert result.is_error
    assert "state timeout" in result.content[0].text


async def test_editor_tool_sends_the_enabled_flag(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload)

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("editor", {"on": True})
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "editor", "enabled": True}]


async def test_screenshot_returns_an_inline_png(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)

    def responder(payload):
        if payload["command"] == "screenshot":
            host_path(payload["path"]).write_bytes(tiny_png())
        return ok_result(payload)

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("screenshot", {})
    finally:
        stop.set()
    assert not result.is_error
    block = result.content[0]
    assert block.type == "image"
    assert block.mime_type == "image/png"
    assert base64.b64decode(block.data).startswith(PNG_SIGNATURE)
    saved = list((tmp_path / "evidence").glob("megabonk-*.png"))
    assert len(saved) == 1
    assert not list(tmp_path.glob("*.png"))
    assert saved[0].stem.removeprefix("megabonk-").isdigit()
    assert saved[0].read_bytes() == base64.b64decode(block.data)
    assert result.content[1].text == f"Saved screenshot to {saved[0]}"


@pytest.mark.parametrize("destination", [None, "evidence/nested", "absolute"])
async def test_screenshot_destinations_and_unique_names(tmp_path, monkeypatch, destination) -> None:
    setup_harness(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    directory = str(tmp_path / "outside") if destination == "absolute" else destination
    target = Path(directory).absolute() if directory else tmp_path / "evidence"

    async def request(harness, payload, timeout):
        host_path(payload["path"]).write_bytes(tiny_png())

    monkeypatch.setattr(mcp_server, "_request", request)
    async with Client(mcp_server.mcp) as client:
        for args in ({"directory": directory}, {"directory": directory}, {"directory": directory, "filename": "final.png"}):
            result = await client.call_tool("screenshot", args)
            assert not result.is_error
            assert result.content[0].type == "image"
            path = Path(result.content[1].text.removeprefix("Saved screenshot to "))
            assert path.is_absolute()
            assert path.parent == target
            assert path.read_bytes() == base64.b64decode(result.content[0].data) == tiny_png()
    assert len(list(target.glob("*.png"))) == 3
    assert (target / "final.png").is_file()
    assert not list(target.glob(".megabonk-*"))


@pytest.mark.parametrize(
    "filename",
    [
        "",
        "../escape.png",
        "/absolute.png",
        "nested/file.png",
        "nested\\file.png",
        "no-extension",
        "bad.jpg",
        "bad\x00.png",
        "bad:drive.png",
    ],
)
async def test_screenshot_invalid_filename_is_actionable(tmp_path, monkeypatch, filename) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("screenshot", {"filename": filename})
    assert result.is_error
    assert "filename" in result.content[0].text
    assert ".png" in result.content[0].text
    assert not list((harness / "commands").iterdir())


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "race"])
async def test_screenshot_never_overwrites_existing_destinations(tmp_path, monkeypatch, kind) -> None:
    setup_harness(tmp_path, monkeypatch)
    out = tmp_path / "final.png"
    original = b"existing evidence"
    if kind == "directory":
        out.mkdir()
    elif kind == "symlink":
        out.symlink_to(tmp_path / "missing.png")
    elif kind == "file":
        out.write_bytes(original)

    async def request(harness, payload, timeout):
        assert kind == "race", "preexisting destinations must fail before capture"
        host_path(payload["path"]).write_bytes(tiny_png())
        out.write_bytes(original)

    monkeypatch.setattr(mcp_server, "_request", request)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("screenshot", {"directory": str(tmp_path), "filename": out.name})
    assert result.is_error
    assert "exists" in result.content[0].text
    assert "filename" in result.content[0].text
    if kind in ("file", "race"):
        assert out.read_bytes() == original
    elif kind == "symlink":
        assert out.is_symlink()
        assert not (tmp_path / "missing.png").exists()
    else:
        assert out.is_dir()


@pytest.mark.parametrize("failure", ["directory", "permission", "rejected", "invalid-png"])
async def test_screenshot_failures_are_actionable_and_leave_no_final_file(tmp_path, monkeypatch, failure) -> None:
    setup_harness(tmp_path, monkeypatch)
    directory = tmp_path / "evidence"
    if failure == "directory":
        directory.write_bytes(b"not a directory")
    elif failure == "permission":

        def denied(*args, **kwargs):
            raise PermissionError("permission denied")

        monkeypatch.setattr(mcp_server.tempfile, "TemporaryDirectory", denied)

    async def request(harness, payload, timeout):
        if failure == "rejected":
            raise mcp_server.ToolError("screenshot rejected")
        host_path(payload["path"]).write_bytes(b"invalid")

    monkeypatch.setattr(mcp_server, "_request", request)
    monkeypatch.setattr(mcp_server, "TIMEOUT", 0.05)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("screenshot", {"directory": str(directory), "filename": "final.png"})
    assert result.is_error
    assert "screenshot" in result.content[0].text
    if failure != "directory":
        assert not list(directory.iterdir())


async def test_log_tail_returns_matching_lines(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    log = mcp_server.run.latest_log_path(harness.parent)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("boot\nDevHarness: enabled\nKillFloor: armed\nnoise\nKillFloor: disarmed\n")
    stop = start_fake_mod(harness, lambda p: ok_result(p))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("log_tail", {"pattern": "KillFloor"})
    finally:
        stop.set()
    assert not result.is_error
    lines = [block.text for block in result.content]
    assert lines == ["KillFloor: armed", "KillFloor: disarmed"]


async def test_log_tail_since_launch_trims_to_the_last_session(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    log = mcp_server.run.latest_log_path(harness.parent)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("old-session\nDevHarness: enabled\nfresh line\n")
    async with Client(mcp_server.mcp) as client:
        since = await client.call_tool("log_tail", {})
        every = await client.call_tool("log_tail", {"since_launch": False})
    assert [block.text for block in since.content] == ["DevHarness: enabled", "fresh line"]
    assert [block.text for block in every.content] == ["old-session", "DevHarness: enabled", "fresh line"]


async def test_log_tail_rejects_an_invalid_regex(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    log = mcp_server.run.latest_log_path(harness.parent)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("DevHarness: enabled\n")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_tail", {"pattern": "("})
    assert result.is_error
    assert "log_tail: invalid pattern" in result.content[0].text
    assert "missing )" in result.content[0].text


async def test_log_tail_caps_the_matches_not_the_session(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    log = mcp_server.run.latest_log_path(harness.parent)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("DevHarness: enabled\nhit 1\nnoise\nhit 2\nnoise\nhit 3\nnoise\n")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_tail", {"pattern": "hit", "max_lines": 2})
    assert [block.text for block in result.content] == ["hit 2", "hit 3"]


INPUT_TOOL_CASES = [
    ("key", {"key": "R"}, {"command": "key", "action": "tap", "key": "R"}),
    (
        "key",
        {"key": "R", "modifiers": ["LeftShift"], "action": "tap"},
        {"command": "key", "action": "tap", "key": "R", "modifiers": ["LeftShift"]},
    ),
    ("key", {"key": "W", "action": "down"}, {"command": "key", "action": "down", "key": "W"}),
    ("key", {"key": "W", "action": "up"}, {"command": "key", "action": "up", "key": "W"}),
    ("mouse", {"action": "move", "x": 10, "y": 20}, {"command": "mouse", "action": "move", "x": 10, "y": 20}),
    ("mouse", {"action": "click"}, {"command": "mouse", "action": "click", "button": 0}),
    (
        "mouse",
        {"action": "click", "x": 960, "y": 540, "button": 1},
        {"command": "mouse", "action": "click", "x": 960, "y": 540, "button": 1},
    ),
    ("mouse", {"action": "clear"}, {"command": "mouse", "action": "clear"}),
    ("material_dump", {}, {"command": "material-dump"}),
    ("material_dump", {"object": "Warehouse"}, {"command": "material-dump", "object": "Warehouse"}),
    ("save_level", {}, {"command": "save-level"}),
    ("save_level", {"level": "my"}, {"command": "save-level", "level": "my"}),
    ("new_level", {}, {"command": "new-level"}),
    (
        "new_level",
        {"level": "arena", "map": 64, "stage": 1, "tier": 2, "size": 9},
        {"command": "new-level", "level": "arena", "map": 64, "stageIndex": 1, "tier": 2, "size": 9},
    ),
    ("list_levels", {}, {"command": "list-levels"}),
    ("kill", {}, {"command": "kill"}),
    ("restart_run", {}, {"command": "restart-run"}),
    ("press_death_confirm", {}, {"command": "press-death-confirm"}),
    ("press_summary_restart", {}, {"command": "press-summary-restart"}),
    ("click_widget", {"name": "Save"}, {"command": "click-widget", "name": "Save"}),
    ("ui_tree", {}, {"command": "ui-tree"}),
    ("ui_tree", {"x": 120, "y": 35}, {"command": "ui-tree", "x": 120, "y": 35}),
    ("type_text", {"text": "chest"}, {"command": "type", "text": "chest"}),
    ("teleport", {"position": [1.5, 0, -3]}, {"command": "teleport", "position": [1.5, 0, -3]}),
    ("teleport", {"cell": [4, 7]}, {"command": "teleport", "cell": [4, 7]}),
    ("item", {"name": "Mirror"}, {"command": "item", "name": "Mirror"}),
    ("item", {"name": "Mirror", "amount": 0}, {"command": "item", "name": "Mirror", "amount": 0}),
    ("grind_slide", {"held": True}, {"command": "grind-slide", "held": True}),
    ("grind_slide", {"held": False}, {"command": "grind-slide", "held": False}),
    ("grind_slide", {}, {"command": "grind-slide"}),
    ("fall_damage", {}, {"command": "fall-damage"}),
    ("dismiss_levelup", {}, {"command": "dismiss-levelup", "choice": 0}),
    ("dismiss_levelup", {"choice": 2}, {"command": "dismiss-levelup", "choice": 2}),
    ("dismiss_offers", {}, {"command": "dismiss-offers"}),
    ("dismiss_offers", {"choice": 2}, {"command": "dismiss-offers", "choice": 2}),
    ("dismiss_offers", {"skip": True}, {"command": "dismiss-offers", "skip": True}),
    ("interact", {"type": "Magnet"}, {"command": "interact", "type": "Magnet"}),
    ("interact", {"type": "Magnet", "max_distance": 4.5}, {"command": "interact", "type": "Magnet", "maxDistance": 4.5}),
    ("interact", {"type": "Magnet", "force": True}, {"command": "interact", "type": "Magnet", "force": True}),
]


@pytest.mark.parametrize("args", [{}, {"type": ""}, {"type": "   "}])
async def test_interact_without_a_type_is_a_tool_error_and_sends_nothing(tmp_path, monkeypatch, args) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("interact", args)
    finally:
        stop.set()
    assert result.is_error
    assert seen == []


@pytest.mark.parametrize(("tool", "args", "expected"), INPUT_TOOL_CASES)
async def test_input_tool_writes_the_harness_payload_and_returns_the_result(tmp_path, monkeypatch, tool, args, expected) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"echo": True})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool(tool, args)
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [expected]
    assert json.loads(result.content[0].text)["result"] == {"echo": True}


@pytest.mark.parametrize(
    ("tool", "command"),
    [("press_death_confirm", "press-death-confirm"), ("press_summary_restart", "press-summary-restart")],
)
async def test_press_tool_waits_out_a_transient_refusal(tmp_path, monkeypatch, tool, command) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(run, "PRESS_POLL_INTERVAL", 0.01)
    attempts = []

    def responder(payload):
        attempts.append(payload)
        if len(attempts) < 3:
            return "rejected", json.dumps({"command": command, "ok": False, "error": "the run summary is not showing"})
        return ok_result(payload, {"button": "B"})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool(tool, {})
    finally:
        stop.set()
    assert not result.is_error
    assert len(attempts) == 3
    assert json.loads(result.content[0].text)["result"] == {"button": "B"}


async def test_press_tool_surfaces_the_refusal_after_the_wait(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(run, "PRESS_POLL_INTERVAL", 0.01)
    monkeypatch.setattr(run, "PRESS_WAIT_SECONDS", 0.1)
    refusal = json.dumps({"command": "press-death-confirm", "ok": False, "error": "no death screen is showing"})
    stop = start_fake_mod(harness, lambda p: ("rejected", refusal))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("press_death_confirm", {})
    finally:
        stop.set()
    assert result.is_error
    assert "no death screen is showing (still refused after waiting" in result.content[0].text


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("key", {"key": "R"}),
        ("mouse", {"action": "click"}),
        ("type_text", {"text": "x"}),
        ("teleport", {"cell": [1, 1]}),
        ("item", {"name": "Mirror"}),
        ("dismiss_levelup", {}),
    ],
)
async def test_input_tool_rejection_surfaces_the_error(tmp_path, monkeypatch, tool, args) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    rejected = json.dumps({"command": None, "ok": False, "error": "unknown key 'Nope'"})
    stop = start_fake_mod(harness, lambda p: ("rejected", rejected))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool(tool, args)
    finally:
        stop.set()
    assert result.is_error
    assert "unknown key 'Nope'" in result.content[0].text


@pytest.mark.parametrize(
    ("tool", "args", "message"),
    [
        ("teleport", {}, "exactly one"),
        ("teleport", {"position": [0, 0, 0], "cell": [1, 1]}, "exactly one"),
        ("teleport", {"position": [0, 0]}, "three"),
        ("teleport", {"cell": [1]}, "two"),
        ("mouse", {"action": "move"}, "x and y"),
        ("mouse", {"action": "move", "x": 5}, "x and y"),
        ("mouse", {"action": "click", "x": 5}, "both or neither"),
        ("ui_tree", {"x": 5}, "both or neither"),
        ("key", {"key": "R", "modifiers": ["LeftShift"], "action": "down"}, "modifiers"),
    ],
)
async def test_invalid_arguments_are_rejected_before_anything_is_sent(tmp_path, monkeypatch, tool, args, message) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.is_error
    assert message in result.content[0].text
    assert list((harness / "commands").iterdir()) == []


async def test_paths_reports_the_game_harness_log_and_levels_directories(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    game = harness.parent
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("paths", {})
    assert not result.is_error
    assert json.loads(result.content[0].text) == {
        "game_dir": str(game),
        "harness": str(harness),
        "latest_log": str(mcp_server.run.latest_log_path(game)),
        "levels_dir": str(game / "UserData" / "Levels"),
    }


def write_log(harness: Path, text: str) -> Path:
    log = mcp_server.run.latest_log_path(harness.parent)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text)
    return log


async def test_log_wait_returns_an_existing_matching_line(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    write_log(harness, "DevHarness: enabled\nKillFloor: armed\n")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_wait", {"pattern": "KillFloor: arm"})
    assert not result.is_error
    assert result.content[0].text == "KillFloor: armed"


async def test_log_wait_returns_a_line_that_appears_later(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    log = write_log(harness, "DevHarness: enabled\n")

    def append_later() -> None:
        time.sleep(0.3)
        with log.open("a") as handle:
            handle.write("KillFloor: armed\n")

    threading.Thread(target=append_later, daemon=True).start()
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_wait", {"pattern": "KillFloor", "timeout": 5})
    assert not result.is_error
    assert result.content[0].text == "KillFloor: armed"


async def test_log_wait_ignores_lines_from_before_the_last_launch(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    write_log(harness, "KillFloor: armed\nDevHarness: enabled\n")
    async with Client(mcp_server.mcp) as client:
        fresh = await client.call_tool("log_wait", {"pattern": "KillFloor", "timeout": 0.3})
        every = await client.call_tool("log_wait", {"pattern": "KillFloor", "timeout": 0.3, "since_launch": False})
    assert fresh.is_error
    assert not every.is_error


async def test_log_wait_times_out_with_a_tool_error(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    write_log(harness, "DevHarness: enabled\n")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_wait", {"pattern": "never", "timeout": 0.3})
    assert result.is_error
    assert "never" in result.content[0].text
    assert "timeout" in result.content[0].text


async def test_log_wait_waits_for_a_log_that_does_not_exist_yet(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_wait", {"pattern": "x", "timeout": 0.3})
    assert result.is_error
    assert "timeout" in result.content[0].text


async def test_log_wait_rejects_an_invalid_regex(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_wait", {"pattern": "(", "timeout": 0.3})
    assert result.is_error
    assert "pattern" in result.content[0].text


def key_names_in_the_mod() -> set[str]:
    source = (Path(__file__).resolve().parent.parent / "src" / "MegabonkLevels.Mod" / "key_names.cs").read_text()
    named = set(re.findall(r'"([A-Za-z]+)"', source.split("Named =")[1].split("};")[0]))
    return (
        named
        | {chr(c) for c in range(ord("A"), ord("Z") + 1)}
        | {f"Alpha{i}" for i in range(10)}
        | {f"Keypad{i}" for i in range(10)}
        | {f"F{i}" for i in range(1, 13)}
    )


def test_key_name_mirror_matches_the_mod() -> None:
    assert set(mcp_server.KEY_NAMES) == key_names_in_the_mod()


@pytest.mark.parametrize(
    "args",
    [
        {"key": "Nope"},
        {"key": "r"},
        {"key": "R", "modifiers": ["Hyper"]},
    ],
)
async def test_key_rejects_names_the_mod_does_not_accept_before_sending(tmp_path, monkeypatch, args) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("key", args)
    assert result.is_error
    assert "valid names" in result.content[0].text
    assert list((harness / "commands").iterdir()) == []


async def test_screenshot_overwrite_replaces_an_existing_file(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    out = tmp_path / "final.png"
    out.write_bytes(b"old evidence")

    async def request(harness, payload, timeout):
        host_path(payload["path"]).write_bytes(tiny_png())

    monkeypatch.setattr(mcp_server, "_request", request)
    async with Client(mcp_server.mcp) as client:
        refused = await client.call_tool("screenshot", {"directory": str(tmp_path), "filename": out.name})
        assert refused.is_error
        assert out.read_bytes() == b"old evidence"
        replaced = await client.call_tool("screenshot", {"directory": str(tmp_path), "filename": out.name, "overwrite": True})
    assert not replaced.is_error
    assert out.read_bytes() == tiny_png()
    assert not list(tmp_path.glob(".megabonk-*"))


def png_size(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


async def screenshot_with(tmp_path, monkeypatch, args, size=(40, 20)):
    setup_harness(tmp_path, monkeypatch)

    async def request(harness, payload, timeout):
        host_path(payload["path"]).write_bytes(tiny_png(*size))

    monkeypatch.setattr(mcp_server, "_request", request)
    async with Client(mcp_server.mcp) as client:
        return await client.call_tool("screenshot", {"directory": str(tmp_path / "out"), **args})


async def test_screenshot_scale_shrinks_the_inline_image_and_keeps_the_saved_capture(tmp_path, monkeypatch) -> None:
    result = await screenshot_with(tmp_path, monkeypatch, {"filename": "s.png", "scale": 0.5})
    assert not result.is_error
    assert png_size(base64.b64decode(result.content[0].data)) == (20, 10)
    assert png_size((tmp_path / "out" / "s.png").read_bytes()) == (40, 20)


async def test_screenshot_crop_selects_a_pixel_rectangle(tmp_path, monkeypatch) -> None:
    result = await screenshot_with(tmp_path, monkeypatch, {"filename": "c.png", "crop": [10, 5, 20, 10]})
    assert not result.is_error
    assert png_size(base64.b64decode(result.content[0].data)) == (20, 10)


async def test_screenshot_crop_then_scale(tmp_path, monkeypatch) -> None:
    result = await screenshot_with(tmp_path, monkeypatch, {"crop": [0, 0, 20, 10], "scale": 0.5})
    assert png_size(base64.b64decode(result.content[0].data)) == (10, 5)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({"scale": 0}, "scale"),
        ({"scale": 1.5}, "scale"),
        ({"crop": [0, 0, 10]}, "crop"),
        ({"crop": [30, 0, 20, 10]}, "crop"),
        ({"crop": [0, 0, 0, 10]}, "crop"),
    ],
)
async def test_screenshot_rejects_bad_scale_and_crop(tmp_path, monkeypatch, args, message) -> None:
    result = await screenshot_with(tmp_path, monkeypatch, args)
    assert result.is_error
    assert message in result.content[0].text


TRICKY = {
    "quote": 'say "hi"',
    "comma": "a,b,c",
    "colon": "key: value",
    "newline": "line1\nline2",
    "rows": [{"name": "a,b", "x": 1}, {"name": 'q"', "x": 2}],
    "none": None,
}


async def call_state(tmp_path, monkeypatch, result_body):
    harness = setup_harness(tmp_path, monkeypatch)
    stop = start_fake_mod(harness, lambda p: ok_result(p, result_body))
    try:
        async with Client(mcp_server.mcp) as client:
            return await client.call_tool("state", {})
    finally:
        stop.set()


async def test_json_encoding_is_indented_with_structured_content(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "json")
    result = await call_state(tmp_path, monkeypatch, {"a": 1})
    body = {"command": "state", "ok": True, "result": {"a": 1}}
    assert result.content[0].text == json.dumps(body, indent=2)
    assert result.structured_content == {"result": body}


async def test_default_encoding_is_json_min_whatever_dot_env_says(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mcp_server.run, "find_env_file", lambda *args, **kwargs: None)
    result = await call_state(tmp_path, monkeypatch, {"a": 1})
    assert result.content[0].text == '{"command":"state","ok":true,"result":{"a":1}}'
    assert result.structured_content is None


async def test_json_min_encoding_is_compact_text_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "json-min")
    result = await call_state(tmp_path, monkeypatch, TRICKY)
    assert not result.is_error
    assert "\n  " not in result.content[0].text
    assert json.loads(result.content[0].text)["result"] == TRICKY
    assert result.structured_content is None


async def test_toon_encoding_round_trips_tricky_strings(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "toon")
    result = await call_state(tmp_path, monkeypatch, TRICKY)
    assert not result.is_error
    assert toon_format.decode(result.content[0].text)["result"] == TRICKY
    assert result.structured_content is None


@pytest.mark.parametrize("encoding", ["json", "json-min", "toon"])
async def test_none_result_has_no_content(tmp_path, monkeypatch, encoding) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", encoding)
    harness = setup_harness(tmp_path, monkeypatch)
    stop = start_fake_mod(harness, lambda p: ("done", None))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("state", {})
    finally:
        stop.set()
    assert not result.is_error
    assert result.content == []


async def test_unknown_encoding_is_a_tool_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "yaml")
    result = await call_state(tmp_path, monkeypatch, {"a": 1})
    assert result.is_error
    assert "MEGABONK_MCP_ENCODING" in result.content[0].text
    assert "yaml" in result.content[0].text


async def test_errors_are_not_re_encoded(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "toon")
    harness = setup_harness(tmp_path, monkeypatch)
    rejected = json.dumps({"command": "state", "ok": False, "error": "no player here"})
    stop = start_fake_mod(harness, lambda p: ("rejected", rejected))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("state", {})
    finally:
        stop.set()
    assert result.is_error
    assert result.content[0].text == "Error executing tool state: no player here"


async def test_paths_tool_goes_through_the_encoding(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "toon")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("paths", {})
    decoded = toon_format.decode(result.content[0].text)
    assert set(decoded) == {"game_dir", "harness", "latest_log", "levels_dir"}


async def test_log_tools_stay_plain_text_under_toon(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", "toon")
    log = mcp_server.run.latest_log_path(harness.parent)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("DevHarness: enabled\nKillFloor: armed\n")
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("log_wait", {"pattern": "KillFloor"})
    assert result.content[0].text == "KillFloor: armed"


def test_toon_encode_is_not_the_stub_release() -> None:
    assert toon_format.encode({"a": [{"x": 1}, {"x": 2}]}) == "a[2]{x}:\n  1\n  2"


FIXTURES = sorted((Path(__file__).parent / "fixtures" / "mcp_payloads").glob("*.json"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.stem)
@pytest.mark.parametrize("encoding", ["json", "json-min", "toon"])
async def test_captured_payloads_round_trip(tmp_path, monkeypatch, fixture, encoding) -> None:
    monkeypatch.setenv("MEGABONK_MCP_ENCODING", encoding)
    body = json.loads(fixture.read_text())
    harness = setup_harness(tmp_path, monkeypatch)
    stop = start_fake_mod(harness, lambda p: ("done", json.dumps(body)))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("state", {})
    finally:
        stop.set()
    text = result.content[0].text
    assert (toon_format.decode(text) if encoding == "toon" else json.loads(text)) == body


MAP_ROWS = {
    "type": "MapData",
    "count": 3,
    "objects": [
        {"name": "MapForest", "eMap": 1},
        {"name": "MapGraveyard", "eMap": 8},
        {"name": "MapHell", "eMap": 64},
    ],
}


async def query_objects(tmp_path, monkeypatch, arguments, responder=None):
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def default_responder(payload):
        seen.append(payload)
        return ok_result(payload, MAP_ROWS)

    stop = start_fake_mod(harness, responder or default_responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("query_objects", arguments)
    finally:
        stop.set()
    return result, seen


async def test_query_objects_sends_the_type_and_fields_and_returns_the_result(tmp_path, monkeypatch) -> None:
    result, seen = await query_objects(tmp_path, monkeypatch, {"type": "MapData", "fields": ["eMap"]})
    assert not result.is_error
    assert seen == [{"command": "query-objects", "type": "MapData", "fields": ["eMap"]}]
    assert json.loads(result.content[0].text) == MAP_ROWS


async def test_query_objects_applies_the_jq_filter_to_the_result(tmp_path, monkeypatch) -> None:
    result, _ = await query_objects(
        tmp_path, monkeypatch, {"type": "MapData", "fields": ["eMap"], "jq": ".objects[] | select(.eMap == 64) | .name"}
    )
    assert not result.is_error
    assert json.loads(result.content[0].text) == "MapHell"


async def test_query_objects_jq_with_several_outputs_returns_a_list(tmp_path, monkeypatch) -> None:
    result, _ = await query_objects(tmp_path, monkeypatch, {"type": "MapData", "jq": ".objects[].name"})
    assert json.loads(result.content[0].text) == ["MapForest", "MapGraveyard", "MapHell"]


async def test_query_objects_invalid_jq_is_a_toolerror_naming_the_parse_failure_and_sends_nothing(tmp_path, monkeypatch) -> None:
    result, seen = await query_objects(tmp_path, monkeypatch, {"type": "MapData", "jq": ".objects[ | "})
    assert result.is_error
    assert "jq" in result.content[0].text
    assert "syntax error" in result.content[0].text
    assert seen == []


async def test_query_objects_jq_runtime_failure_is_a_toolerror(tmp_path, monkeypatch) -> None:
    result, _ = await query_objects(tmp_path, monkeypatch, {"type": "MapData", "jq": ".name | ascii_downcase | error"})
    assert result.is_error
    assert "jq" in result.content[0].text


async def test_query_objects_unknown_type_surfaces_the_mods_error(tmp_path, monkeypatch) -> None:
    rejected = json.dumps({"command": "query-objects", "ok": False, "error": "unknown type 'Nope'"})
    result, _ = await query_objects(tmp_path, monkeypatch, {"type": "Nope"}, lambda p: ("done", rejected))
    assert result.is_error
    assert "unknown type 'Nope'" in result.content[0].text


async def test_query_objects_rejects_an_empty_type_or_field(tmp_path, monkeypatch) -> None:
    for index, arguments in enumerate(({"type": ""}, {"type": "MapData", "fields": [""]})):
        result, seen = await query_objects(tmp_path / str(index), monkeypatch, arguments)
        assert result.is_error
        assert seen == []


async def test_load_tool_sends_the_overrides(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload)

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("load", {"level": "a.json", "map": 64, "stage": 1, "tier": 2, "seed": 7})
    finally:
        stop.set()
    assert not result.is_error
    assert (seen[0]["map"], seen[0]["stageIndex"], seen[0]["tier"], seen[0]["seed"]) == (64, 1, 2, 7)


async def test_load_tool_rejects_a_non_integer_override(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("load", {"level": "a.json", "stage": "one"})
    assert result.is_error
    assert "stage" in result.content[0].text


async def test_relaunch_tool_forwards_the_overrides(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    seen = {}

    def fake_relaunch(harness, game_dir, level, timeout, task, on_step, on_error, overrides=None, spawns=True, invulnerable=False, feathers=2):
        seen["overrides"] = overrides
        seen["spawns"] = spawns
        seen["invulnerable"] = invulnerable
        seen["feathers"] = feathers
        return True

    monkeypatch.setattr(mcp_server.run, "relaunch", fake_relaunch)

    async def fake_command(harness, payload, timeout):
        return mcp_server._encode({"ok": True})

    monkeypatch.setattr(mcp_server, "_command", fake_command)
    async with Client(mcp_server.mcp) as client:
        await client.call_tool("relaunch", {"map": 2, "seed": 3})
    assert seen["overrides"] == {"map": 2, "seed": 3}
    assert seen["spawns"] is True
    assert seen["invulnerable"] is False
    assert seen["feathers"] == 2


async def test_relaunch_tool_no_level_passes_no_level_path(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    seen = {}

    def fake_relaunch(harness, game_dir, level, timeout, task, on_step, on_error, overrides=None, spawns=True, invulnerable=False, feathers=2):
        seen["level"] = level
        return True

    monkeypatch.setattr(mcp_server.run, "relaunch", fake_relaunch)

    async def fake_command(harness, payload, timeout):
        return mcp_server._encode({"ok": True})

    monkeypatch.setattr(mcp_server, "_command", fake_command)
    async with Client(mcp_server.mcp) as client:
        await client.call_tool("relaunch", {"no_level": True})
    assert seen["level"] is None


async def test_relaunch_tool_applies_the_spawn_and_invulnerable_settings(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)
    monkeypatch.setenv("MEGABONK_RELAUNCH_SPAWNS", "false")
    monkeypatch.setenv("MEGABONK_RELAUNCH_INVULNERABLE", "true")
    monkeypatch.setenv("MEGABONK_RELAUNCH_FEATHERS", "0")
    seen = {}

    def fake_relaunch(harness, game_dir, level, timeout, task, on_step, on_error, overrides=None, spawns=True, invulnerable=False, feathers=2):
        seen["spawns"] = spawns
        seen["invulnerable"] = invulnerable
        seen["feathers"] = feathers
        return True

    monkeypatch.setattr(mcp_server.run, "relaunch", fake_relaunch)

    async def fake_command(harness, payload, timeout):
        return mcp_server._encode({"ok": True})

    monkeypatch.setattr(mcp_server, "_command", fake_command)
    async with Client(mcp_server.mcp) as client:
        await client.call_tool("relaunch", {})
    assert seen["spawns"] is False
    assert seen["invulnerable"] is True
    assert seen["feathers"] == 0


async def test_relaunch_tool_error_carries_the_failing_log_line(tmp_path, monkeypatch) -> None:
    setup_harness(tmp_path, monkeypatch)

    def fake_relaunch(harness, game_dir, level, timeout, task, on_step, on_error, overrides=None, spawns=True, invulnerable=False, feathers=2):
        on_error("relaunch: the level failed to load: LevelLoader: load failed: no MapData found for map=32")
        return False

    monkeypatch.setattr(mcp_server.run, "relaunch", fake_relaunch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("relaunch", {})
    assert result.is_error
    assert "LevelLoader: load failed: no MapData found for map=32" in result.content[0].text


async def test_perf_tool_sends_the_verb_and_its_arguments(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"frames": 900, "p50Ms": 16.7})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("perf", {"verb": "spawn", "count": 120})
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "perf", "action": "spawn", "count": 120}]
    assert json.loads(result.content[0].text)["result"]["p50Ms"] == 16.7


async def test_perf_tool_sends_toggle_target_and_enabled(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"target": "EnemyManager.Update", "enabled": False})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("perf", {"verb": "toggle", "target": "EnemyManager.Update", "enabled": False})
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "perf", "action": "toggle", "target": "EnemyManager.Update", "enabled": False}]


async def test_perf_tool_sends_render_with_its_enabled_state(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"renderersOff": 240, "enemies": 240})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("perf", {"verb": "render", "enabled": False})
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "perf", "action": "render", "enabled": False}]
    assert json.loads(result.content[0].text)["result"]["renderersOff"] == 240


async def test_perf_tool_sends_the_engine_side_controls_with_their_enabled_state(tmp_path, monkeypatch) -> None:
    """physics off kinematicises the enemy bodies, animation off stops their updates: both are the verb plus enabled."""
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"armed": True})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            physics = await client.call_tool("perf", {"verb": "physics", "enabled": False})
            animation = await client.call_tool("perf", {"verb": "animation", "enabled": False})
            restore = await client.call_tool("perf", {"verb": "physics", "enabled": True})
    finally:
        stop.set()
    assert not physics.is_error and not animation.is_error and not restore.is_error
    assert seen == [
        {"command": "perf", "action": "physics", "enabled": False},
        {"command": "perf", "action": "animation", "enabled": False},
        {"command": "perf", "action": "physics", "enabled": True},
    ]


async def test_perf_tool_omits_arguments_a_verb_does_not_use(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"window": 1})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            await client.call_tool("perf", {"verb": "start"})
            await client.call_tool("perf", {"verb": "timescale", "value": 4})
    finally:
        stop.set()
    assert seen == [
        {"command": "perf", "action": "start"},
        {"command": "perf", "action": "timescale", "value": 4},
    ]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"verb": "profile"}, "unknown perf verb"),
        ({"verb": "spawn"}, "count"),
        ({"verb": "spawn", "count": 0}, "count"),
        ({"verb": "spawn", "count": 301}, "count"),
        ({"verb": "timescale", "value": 25}, "value"),
        ({"verb": "toggle", "target": "KillFloor"}, "enabled"),
        ({"verb": "toggle", "enabled": False}, "target"),
        ({"verb": "render"}, "enabled"),
        ({"verb": "physics"}, "enabled"),
        ({"verb": "animation"}, "enabled"),
        ({"verb": "health", "hp": 0}, "hp"),
        ({"verb": "health", "hp": 100000001}, "hp"),
    ],
)
async def test_perf_tool_rejects_bad_arguments_before_sending(tmp_path, monkeypatch, arguments, message) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("perf", arguments)
    assert result.is_error
    assert message in result.content[0].text
    assert not list((harness / "commands").glob("*.json"))


async def test_perf_tool_sends_vsync(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def responder(payload):
        seen.append(payload)
        return ok_result(payload, {"vsync": False, "vSyncCount": 0})

    stop = start_fake_mod(harness, responder)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("perf", {"verb": "vsync", "enabled": False})
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "perf", "action": "vsync", "enabled": False}]


async def test_perf_tool_requires_enabled_for_vsync(tmp_path, monkeypatch) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("perf", {"verb": "vsync"})
    assert result.is_error
    assert "enabled" in result.content[0].text
    assert not list((harness / "commands").glob("*.json"))
