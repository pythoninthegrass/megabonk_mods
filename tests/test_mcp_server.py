"""Self-test for scripts/mcp_server.py, driving the tools through the in-memory MCP client."""

import base64
import json
import mcp_server
import pytest
import struct
import threading
import time
import zlib
from mcp.client import Client
from pathlib import Path

pytestmark = pytest.mark.anyio

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def tiny_png() -> bytes:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00"))
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
    saved = list(tmp_path.glob("megabonk-*.png"))
    assert len(saved) == 1
    assert saved[0].stem.removeprefix("megabonk-").isdigit()
    assert saved[0].read_bytes() == base64.b64decode(block.data)
    assert result.content[1].text == f"Saved screenshot to {saved[0]}"


@pytest.mark.parametrize("destination", [None, "evidence/nested", "absolute"])
async def test_screenshot_destinations_and_unique_names(tmp_path, monkeypatch, destination) -> None:
    setup_harness(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    directory = str(tmp_path / "outside") if destination == "absolute" else destination
    target = Path(directory).absolute() if directory else tmp_path

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


@pytest.mark.parametrize("filename", ["", "../escape.png", "/absolute.png", "nested/file.png", "nested\\file.png", "no-extension", "bad.jpg", "bad\x00.png", "bad:drive.png"])
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
    ("type_text", {"text": "chest"}, {"command": "type", "text": "chest"}),
    ("teleport", {"position": [1.5, 0, -3]}, {"command": "teleport", "position": [1.5, 0, -3]}),
    ("teleport", {"cell": [4, 7]}, {"command": "teleport", "cell": [4, 7]}),
    ("dismiss_levelup", {}, {"command": "dismiss-levelup", "choice": 0}),
    ("dismiss_levelup", {"choice": 2}, {"command": "dismiss-levelup", "choice": 2}),
]


@pytest.mark.parametrize(("tool", "args", "expected"), INPUT_TOOL_CASES)
async def test_input_tool_writes_the_harness_payload_and_returns_the_result(
    tmp_path, monkeypatch, tool, args, expected
) -> None:
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
    ("tool", "args"),
    [
        ("key", {"key": "R"}),
        ("mouse", {"action": "click"}),
        ("type_text", {"text": "x"}),
        ("teleport", {"cell": [1, 1]}),
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
        ("key", {"key": "R", "modifiers": ["LeftShift"], "action": "down"}, "modifiers"),
    ],
)
async def test_invalid_arguments_are_rejected_before_anything_is_sent(
    tmp_path, monkeypatch, tool, args, message
) -> None:
    harness = setup_harness(tmp_path, monkeypatch)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.is_error
    assert message in result.content[0].text
    assert list((harness / "commands").iterdir()) == []
