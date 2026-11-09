import json
import mcp_server
import pytest
from mcp.client import Client
from test_mcp_server import ok_result, setup_harness, start_fake_mod

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("amount,nonlethal", [(1, True), (37, True), (99, False)])
async def test_damage_tool_preserves_amount_safety_and_result(tmp_path, monkeypatch, amount, nonlethal):
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def respond(payload):
        seen.append(payload)
        return ok_result(payload, {"requestedDamage": amount, "actualDamage": 0, "blocked": True})

    stop = start_fake_mod(harness, respond)
    try:
        async with Client(mcp_server.mcp) as client:
            arguments = {"amount": amount}
            if not nonlethal:
                arguments["nonlethal"] = False
            result = await client.call_tool("damage", arguments)
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "damage", "amount": amount, "nonlethal": nonlethal}]
    assert json.loads(result.content[0].text)["result"]["blocked"] is True


@pytest.mark.parametrize("amount", [0, -1, 100, 1.5, 1.0, True, "5", None])
async def test_damage_tool_rejects_invalid_before_sending(tmp_path, monkeypatch, amount):
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(mcp_server, "TIMEOUT", 0.1)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("damage", {"amount": amount})
    assert result.is_error
    assert not list((harness / "commands").iterdir())


@pytest.mark.parametrize("nonlethal", [None, "false", 0])
async def test_damage_tool_rejects_nonboolean_safety(tmp_path, monkeypatch, nonlethal):
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(mcp_server, "TIMEOUT", 0.1)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("damage", {"amount": 5, "nonlethal": nonlethal})
    assert result.is_error
    assert not list((harness / "commands").iterdir())


@pytest.mark.parametrize("error", ["damage: no player health in the scene", "damage: player is dead"])
async def test_damage_tool_reports_player_rejection(tmp_path, monkeypatch, error):
    harness = setup_harness(tmp_path, monkeypatch)
    stop = start_fake_mod(harness, lambda p: ("rejected", json.dumps({"command": p["command"], "ok": False, "error": error})))
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("damage", {"amount": 5})
    finally:
        stop.set()
    assert result.is_error
    assert error in result.content[0].text


@pytest.mark.parametrize("target", ["nearest", "all", "bosses"])
async def test_kill_enemies_tool_sends_target_and_returns_result(tmp_path, monkeypatch, target):
    harness = setup_harness(tmp_path, monkeypatch)
    seen = []

    def respond(payload):
        seen.append(payload)
        return ok_result(payload, {"target": target, "killed": 2, "bossesKilled": 1})

    stop = start_fake_mod(harness, respond)
    try:
        async with Client(mcp_server.mcp) as client:
            result = await client.call_tool("kill_enemies", {"target": target})
    finally:
        stop.set()
    assert not result.is_error
    assert seen == [{"command": "kill-enemies", "target": target}]
    assert json.loads(result.content[0].text)["result"]["killed"] == 2


@pytest.mark.parametrize("target", ["", "everyone", None, 3])
async def test_kill_enemies_tool_rejects_unknown_target_before_sending(tmp_path, monkeypatch, target):
    harness = setup_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(mcp_server, "TIMEOUT", 0.1)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("kill_enemies", {"target": target})
    assert result.is_error
    assert not list((harness / "commands").iterdir())
