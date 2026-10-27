"""
Self-test for scripts/run.py.
"""

import json
import os
import pytest
import run
import tempfile
import threading
import time
from pathlib import Path


def test_find_env_file_walks_up_from_start() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".env").write_text("A=1\n")
        nested = root / "a" / "b"
        nested.mkdir(parents=True)
        assert run.find_env_file(nested) == root / ".env"


def test_find_env_file_returns_none_when_absent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert run.find_env_file(Path(tmp), stop_at=Path(tmp)) is None


def test_game_dir_prefers_game_dir_over_bottle() -> None:
    values = {"MEGABONK_GAME_DIR": "/g", "MEGABONK_BOTTLE": "/b"}
    assert run.resolve_game_dir(values.get, system="Darwin") == Path("/g")


def test_game_dir_from_bottle() -> None:
    values = {"MEGABONK_BOTTLE": "/b"}
    expected = Path("/b/Program Files (x86)/Steam/steamapps/common/Megabonk")
    assert run.resolve_game_dir(values.get, system="Darwin") == expected


def test_game_dir_macos_default_is_the_megabonk_wine_prefix() -> None:
    game = run.resolve_game_dir({}.get, system="Darwin")
    assert str(game).endswith(".local/share/megabonk/wine/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")


def test_game_dir_macos_crossover_runtime_default_is_the_crossover_bottle() -> None:
    game = run.resolve_game_dir({"MEGABONK_MACOS_RUNTIME": "crossover"}.get, system="Darwin")
    assert str(game).endswith("CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")


def test_game_dir_from_wine_prefix() -> None:
    values = {"MEGABONK_WINE_PREFIX": "/p"}
    expected = Path("/p/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    assert run.resolve_game_dir(values.get, system="Darwin") == expected


def test_game_dir_windows_default() -> None:
    game = run.resolve_game_dir({}.get, system="Windows")
    assert str(game) == r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk"


def test_macos_runtime_defaults_to_wine_and_reads_lookup() -> None:
    assert run.resolve_macos_runtime({}.get) == "wine"
    assert run.resolve_macos_runtime({"MEGABONK_MACOS_RUNTIME": "crossover"}.get) == "crossover"


def test_macos_runtime_rejects_unknown_value() -> None:
    try:
        run.resolve_macos_runtime({"MEGABONK_MACOS_RUNTIME": "proton"}.get)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit")


def test_launch_task_is_crossover_only_for_the_crossover_runtime_on_macos() -> None:
    assert run.launch_task("crossover", system="Darwin") == "crossover:run"
    assert run.launch_task("wine", system="Darwin") == "game:run"
    assert run.launch_task("crossover", system="Linux") == "game:run"


def test_to_game_path_maps_host_path_into_wine_z_drive_on_macos() -> None:
    assert run.to_game_path(Path("/tmp/a.png"), system="Darwin") == "Z:\\tmp\\a.png"


def test_to_game_path_is_identity_on_linux_and_windows() -> None:
    assert run.to_game_path(Path("/tmp/a.png"), system="Linux") == "/tmp/a.png"
    assert run.to_game_path(Path("C:/x/a.png"), system="Windows") == str(Path("C:/x/a.png"))


def test_build_command_load_level() -> None:
    assert run.build_command("load-level", "Z:\\a.json") == {
        "command": "load-level",
        "path": "Z:\\a.json",
    }


def test_build_command_quit_has_no_path() -> None:
    assert run.build_command("quit") == {"command": "quit"}


def test_build_command_steam_ready_has_no_path() -> None:
    assert run.build_command("steam-ready") == {"command": "steam-ready"}


def test_write_command_is_atomic_and_ordered() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        commands = Path(tmp)
        first = run.write_command(commands, {"command": "quit"})
        second = run.write_command(commands, {"command": "quit"})
        assert first.suffix == ".json" and first.parent == commands
        assert sorted(p.name for p in commands.iterdir()) == [first.name, second.name]
        assert first.name < second.name
        assert json.loads(first.read_text()) == {"command": "quit"}
        assert not list(commands.glob("*.tmp"))


def test_enable_and_disable_toggle_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp)
        run.set_enabled(game, True)
        assert (game / "harness" / "enabled").is_file()
        assert (game / "harness" / "commands").is_dir()
        run.set_enabled(game, False)
        assert not (game / "harness" / "enabled").exists()
        run.set_enabled(game, False)


def test_wait_for_outcome_reports_done_rejected_and_timeout() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp)
        (harness / "done").mkdir()
        (harness / "rejected").mkdir()
        (harness / "done" / "a.json").write_text("{}")
        (harness / "rejected" / "b.json").write_text("{}")
        assert run.wait_for_outcome(harness, "a.json", timeout=0.2) == "done"
        assert run.wait_for_outcome(harness, "b.json", timeout=0.2) == "rejected"
        assert run.wait_for_outcome(harness, "c.json", timeout=0.2) == "timeout"


def write_result(harness: Path, name: str, body: str) -> None:
    (harness / "results").mkdir(exist_ok=True)
    (harness / "results" / name).write_text(body)


def test_read_result_returns_the_parsed_object() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp)
        write_result(harness, "a.json", '{"command":"state","ok":true,"result":{"editor":true}}')
        assert run.read_result(harness, "a.json") == {"command": "state", "ok": True, "result": {"editor": True}}


def test_read_result_is_none_when_absent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert run.read_result(Path(tmp), "missing.json") is None


def test_read_result_is_none_for_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp)
        write_result(harness, "a.json", "{not json")
        assert run.read_result(harness, "a.json") is None


def fake_game(tmp: str, result: str | None, outcome: str = "done") -> Path:
    """Game dir with an enabled harness whose first command is answered by a background responder."""
    game = Path(tmp)
    harness = game / "harness"
    run.set_enabled(game, True)
    for folder in ("done", "rejected", "results"):
        (harness / folder).mkdir(exist_ok=True)

    def respond() -> None:
        for _ in range(100):
            for command in (harness / "commands").glob("*.json"):
                if result is not None:
                    write_result(harness, command.name, result)
                command.rename(harness / outcome / command.name)
                return
            time.sleep(0.05)

    threading.Thread(target=respond, daemon=True).start()
    return game


def run_main(game: Path, *argv: str) -> int:
    previous = os.environ.get("MEGABONK_GAME_DIR")
    os.environ["MEGABONK_GAME_DIR"] = str(game)
    try:
        return run.main(["--timeout", "5", *argv])
    finally:
        if previous is None:
            os.environ.pop("MEGABONK_GAME_DIR")
        else:
            os.environ["MEGABONK_GAME_DIR"] = previous


def test_state_prints_the_result_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"state","ok":true,"result":{"editor":true,"player":null}}')
        assert run_main(game, "state") == 0
    printed = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(printed) == {"editor": True, "player": None}


def test_bundle_sends_load_bundle_and_prints_the_result_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"load-bundle","ok":true,"result":{"assets":["a.prefab"],"prefab":"A"}}')
        assert run_main(game, "bundle", "/tmp/testprop") == 0
        sent = next((game / "harness" / "done").glob("*.json"))
        assert json.loads(sent.read_text())["command"] == "load-bundle"
    printed = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(printed) == {"assets": ["a.prefab"], "prefab": "A"}


def test_shader_report_sends_shader_report_and_prints_the_result_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"shader-report","ok":true,"result":{"found":{"Standard":true}}}')
        assert run_main(game, "shader-report") == 0
        sent = next((game / "harness" / "done").glob("*.json"))
        assert json.loads(sent.read_text())["command"] == "shader-report"
    printed = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(printed) == {"found": {"Standard": True}}


def test_state_exits_1_when_the_result_is_not_ok(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"state","ok":false,"error":"no player"}', outcome="rejected")
        assert run_main(game, "state") == 1
    assert "no player" in capsys.readouterr().err


def test_send_reports_an_ok_false_result_even_when_the_file_landed_in_done(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"freeze","ok":false,"error":"boom"}')
        assert run_main(game, "freeze") == 1
    assert "boom" in capsys.readouterr().err


def test_send_still_succeeds_when_no_result_file_is_written() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, None)
        assert run_main(game, "freeze") == 0


def test_is_png_checks_signature() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "good.png"
        good.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 8)
        bad = Path(tmp) / "bad.png"
        bad.write_bytes(b"nope")
        assert run.is_png(good)
        assert not run.is_png(bad)
        assert not run.is_png(Path(tmp) / "missing.png")


def test_build_command_freeze_and_resume_have_no_payload() -> None:
    assert run.build_command("freeze") == {"command": "freeze"}
    assert run.build_command("resume") == {"command": "resume"}


def test_build_command_invulnerable_and_vulnerable_have_no_payload() -> None:
    assert run.build_command("invulnerable") == {"command": "invulnerable"}
    assert run.build_command("vulnerable") == {"command": "vulnerable"}


def test_parse_args_invulnerable_and_vulnerable_subcommands() -> None:
    assert run.parse_args(["invulnerable"]).action == "invulnerable"
    assert run.parse_args(["vulnerable"]).action == "vulnerable"


def test_build_heartbeat_command_carries_the_enabled_flag() -> None:
    assert run.build_heartbeat_command(True) == {"command": "heartbeat", "enabled": True}
    assert run.build_heartbeat_command(False) == {"command": "heartbeat", "enabled": False}


def test_parse_args_heartbeat_takes_on_or_off() -> None:
    assert run.parse_args(["heartbeat", "on"]).state == "on"
    assert run.parse_args(["heartbeat", "off"]).state == "off"


def test_parse_args_heartbeat_rejects_other_states_and_a_missing_state() -> None:
    for argv in (["heartbeat"], ["heartbeat", "maybe"]):
        try:
            run.parse_args(argv)
        except SystemExit:
            continue
        raise AssertionError(f"{argv} should have been rejected")


def test_heartbeat_payload_maps_the_state_to_the_wire_command() -> None:
    assert run.heartbeat_payload(run.parse_args(["heartbeat", "on"])) == {"command": "heartbeat", "enabled": True}
    assert run.heartbeat_payload(run.parse_args(["heartbeat", "off"])) == {"command": "heartbeat", "enabled": False}


def test_build_cells_command_carries_the_enabled_flag() -> None:
    assert run.build_cells_command(True) == {"command": "cells", "enabled": True}
    assert run.build_cells_command(False) == {"command": "cells", "enabled": False}


def test_parse_args_cells_takes_on_or_off() -> None:
    assert run.parse_args(["cells", "on"]).state == "on"
    assert run.parse_args(["cells", "off"]).state == "off"


def test_parse_args_cells_rejects_other_states_and_a_missing_state() -> None:
    for argv in (["cells"], ["cells", "maybe"]):
        try:
            run.parse_args(argv)
        except SystemExit:
            continue
        raise AssertionError(f"{argv} should have been rejected")


def test_cells_payload_maps_the_state_to_the_wire_command() -> None:
    assert run.cells_payload(run.parse_args(["cells", "on"])) == {"command": "cells", "enabled": True}
    assert run.cells_payload(run.parse_args(["cells", "off"])) == {"command": "cells", "enabled": False}


def test_build_editor_command_carries_the_enabled_flag() -> None:
    assert run.build_editor_command(True) == {"command": "editor", "enabled": True}
    assert run.build_editor_command(False) == {"command": "editor", "enabled": False}


def test_parse_args_editor_takes_on_or_off() -> None:
    assert run.parse_args(["editor", "on"]).state == "on"
    assert run.parse_args(["editor", "off"]).state == "off"


def test_parse_args_editor_rejects_other_states_and_a_missing_state() -> None:
    for argv in (["editor"], ["editor", "maybe"]):
        try:
            run.parse_args(argv)
        except SystemExit:
            continue
        raise AssertionError(f"{argv} should have been rejected")


def test_editor_payload_maps_the_state_to_the_wire_command() -> None:
    assert run.editor_payload(run.parse_args(["editor", "on"])) == {"command": "editor", "enabled": True}
    assert run.editor_payload(run.parse_args(["editor", "off"])) == {"command": "editor", "enabled": False}


def test_build_teleport_command_carries_a_position_or_a_cell() -> None:
    assert run.build_teleport_command(position=(1.5, 0.0, -200.0)) == {"command": "teleport", "position": [1.5, 0.0, -200.0]}
    assert run.build_teleport_command(cell=(3, 12)) == {"command": "teleport", "cell": [3, 12]}


def test_build_dismiss_levelup_command_carries_the_choice() -> None:
    assert run.build_dismiss_levelup_command(0) == {"command": "dismiss-levelup", "choice": 0}
    assert run.build_dismiss_levelup_command(2) == {"command": "dismiss-levelup", "choice": 2}


def test_teleport_payload_takes_xyz_or_cell() -> None:
    assert run.teleport_payload(run.parse_args(["teleport", "1", "2", "3"])) == {
        "command": "teleport",
        "position": [1.0, 2.0, 3.0],
    }
    assert run.teleport_payload(run.parse_args(["teleport", "--cell", "3", "12"])) == {"command": "teleport", "cell": [3, 12]}


def test_teleport_payload_rejects_missing_partial_or_both_targets() -> None:
    for argv in (["teleport"], ["teleport", "1", "2"], ["teleport", "1", "2", "3", "--cell", "1", "2"]):
        try:
            run.teleport_payload(run.parse_args(argv))
        except SystemExit:
            continue
        raise AssertionError(f"{argv} should have been rejected")


def test_dismiss_levelup_payload_defaults_to_the_first_offer() -> None:
    assert run.dismiss_levelup_payload(run.parse_args(["dismiss-levelup"])) == {"command": "dismiss-levelup", "choice": 0}
    assert run.dismiss_levelup_payload(run.parse_args(["dismiss-levelup", "--choice", "2"])) == {
        "command": "dismiss-levelup",
        "choice": 2,
    }


def test_teleport_prints_the_result_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"teleport","ok":true,"result":{"position":[1,2,3],"cell":[4,5]}}')
        assert run_main(game, "teleport", "--cell", "4", "5") == 0
    printed = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(printed) == {"position": [1, 2, 3], "cell": [4, 5]}


def test_dismiss_levelup_exits_1_when_the_result_is_not_ok(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"dismiss-levelup","ok":false,"error":"choice 9 out of range"}', outcome="rejected")
        assert run_main(game, "dismiss-levelup", "--choice", "9") == 1
    assert "out of range" in capsys.readouterr().err


def test_parse_args_cycle_accepts_invulnerable_flag() -> None:
    assert run.parse_args(["cycle", "a.json", "o.png", "--invulnerable"]).invulnerable is True
    assert run.parse_args(["cycle", "a.json", "o.png"]).invulnerable is False


def test_parse_args_relaunch_defaults_to_the_test_forest_level() -> None:
    args = run.parse_args(["relaunch"])
    assert args.action == "relaunch"
    assert args.level == run.TEST_FOREST_LEVEL


def test_relaunch_timeout_allows_melonloader_to_initialize() -> None:
    assert run.relaunch_timeout(15) == 60
    assert run.relaunch_timeout(120) == 120


def test_steam_ready_exits_1_when_the_game_reports_not_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"steam-ready","ok":true,"result":{"ready":false}}')
        assert run_main(game, "steam-ready") == 1


def test_steam_ready_exits_0_when_the_game_reports_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"steam-ready","ok":true,"result":{"ready":true,"buildId":"21750826"}}')
        assert run_main(game, "steam-ready") == 0


def test_steam_ready_exits_0_for_a_mod_that_returns_no_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"steam-ready","ok":true,"result":null}')
        assert run_main(game, "steam-ready") == 0


def test_wait_for_steamworks_ready_retries_until_the_game_reports_ready() -> None:
    results = iter([False, False, True])
    assert run.wait_for_steamworks_ready(lambda: next(results), timeout=5, sleep=lambda _: None)


def test_wait_for_steamworks_ready_times_out_when_the_game_never_reports_ready() -> None:
    clock = iter(range(100))
    assert not run.wait_for_steamworks_ready(lambda: False, timeout=3, sleep=lambda _: None, now=lambda: next(clock))


def test_build_camera_command_carries_position_and_rotation() -> None:
    assert run.build_camera_command((1.0, 200.0, -3.0), (90.0, 0.0, 45.5)) == {
        "command": "camera",
        "position": [1.0, 200.0, -3.0],
        "rotation": [90.0, 0.0, 45.5],
    }


def test_parse_args_camera_pose_and_clear() -> None:
    args = run.parse_args(["camera", "1", "2", "3", "--rot", "90", "0", "0"])
    assert (args.action, args.position, args.rot) == ("camera", [1.0, 2.0, 3.0], [90.0, 0.0, 0.0])
    assert run.parse_args(["camera", "--clear"]).clear is True


def test_parse_args_cycle_accepts_freeze_and_camera_flags() -> None:
    args = run.parse_args(["cycle", "a.json", "o.png", "--freeze", "--camera", "0", "300", "0", "90", "0", "0"])
    assert args.freeze is True
    assert args.camera == [0.0, 300.0, 0.0, 90.0, 0.0, 0.0]
    plain = run.parse_args(["cycle", "a.json", "o.png"])
    assert plain.freeze is False and plain.camera is None


PS_LISTING = """\
 6308 C:\\windows\\system32\\winemenubuilder.exe -w -u C:\\users\\crossover\\Start Menu\\Programs\\Steam\\Megabonk.url
87328 /Applications/CrossOver.app/lib/wine/winewrapper.exe --run -- /Users/lance/Steam/common/Megabonk/Megabonk.exe
87663 C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\Megabonk.exe
87667 C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\UnityCrashHandler64.exe --attach 1580
90001 bash -c cd /x && wine --cx-app Megabonk.exe
"""


def test_find_game_pids_matches_only_the_game_executable() -> None:
    assert run.find_game_pids(PS_LISTING) == [87663]


def test_find_game_pids_matches_native_linux_build() -> None:
    listing = (
        "  500 /media/steam/steamapps/common/Megabonk/Megabonk.x86_64 -screen-fullscreen 0\n  501 bash -c pkill Megabonk.x86_64\n"
    )
    assert run.find_game_pids(listing) == [500]


def test_find_game_pids_empty_when_not_running() -> None:
    assert run.find_game_pids("  1 /sbin/launchd\n") == []


def test_find_game_pids_tasklist_reads_csv_rows() -> None:
    out = '"Megabonk.exe","4242","Console","1","1,024 K"\nINFO: No tasks are running which match the specified criteria.\n'
    assert run.find_game_pids_tasklist(out) == [4242]
    assert run.find_game_pids_tasklist("INFO: No tasks are running which match the specified criteria.\n") == []


def test_wait_for_exit_true_once_probe_reports_no_pids() -> None:
    probes = iter([[1], [1], []])
    assert run.wait_for_exit(lambda: next(probes), timeout=5, sleep=lambda _: None)


def test_wait_for_exit_false_when_game_outlives_timeout() -> None:
    clock = iter(range(100))
    assert not run.wait_for_exit(lambda: [1], timeout=3, sleep=lambda _: None, now=lambda: next(clock))


def make_harness(tmp: str) -> Path:
    harness = Path(tmp) / "harness"
    for folder in ("commands", "done", "rejected", "results"):
        (harness / folder).mkdir(parents=True)
    return harness


def test_request_result_returns_the_outcome_and_the_parsed_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"state","ok":true,"result":{"editor":true}}')
        outcome, result = run.request_result(game / "harness", {"command": "state"}, timeout=5)
        assert outcome == "done"
        assert result == {"command": "state", "ok": True, "result": {"editor": True}}


def test_request_result_reports_rejected_with_the_result_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"freeze","ok":false,"error":"boom"}', outcome="rejected")
        outcome, result = run.request_result(game / "harness", {"command": "freeze"}, timeout=5)
        assert outcome == "rejected"
        assert result == {"command": "freeze", "ok": False, "error": "boom"}


def test_request_result_times_out_with_no_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        harness = make_harness(tmp)
        outcome, result = run.request_result(harness, {"command": "state"}, timeout=0.2)
        assert outcome == "timeout"
        assert result is None


def test_request_result_prints_nothing(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"freeze","ok":true}')
        run.request_result(game / "harness", {"command": "freeze"}, timeout=5)
        out = capsys.readouterr()
        assert out.out == "" and out.err == ""


def relaunch_stubs(monkeypatch, *, harness_ready=True, steam_ready=True, kill_floor=True, unsupported=False):
    calls = []
    monkeypatch.setattr(run, "quit_game", lambda h, t: calls.append("quit") or True)
    monkeypatch.setattr(run, "launch_game", lambda task: calls.append(("launch", task)) or True)
    monkeypatch.setattr(run, "wait_for_steamworks_ready", lambda probe, timeout: calls.append("steam") or steam_ready)
    monkeypatch.setattr(run, "send", lambda h, payload, t: calls.append(("send", payload["command"])) or True)

    def wait_log(log, line, newer, timeout):
        calls.append(("log", line))
        return harness_ready

    def wait_any_log(log, lines, newer, timeout):
        calls.append(("log", lines[0]))
        if unsupported:
            return run.EDITOR_UNSUPPORTED_LINE
        return run.KILL_FLOOR_ARMED_LINE if kill_floor else None

    monkeypatch.setattr(run, "wait_for_log_line", wait_log)
    monkeypatch.setattr(run, "wait_for_any_log_line", wait_any_log)
    return calls


def test_relaunch_runs_every_step_in_order_and_returns_true(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch)
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/lvl.json"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None)
    assert ok is True
    assert calls == [
        "quit",
        ("launch", "game:run"),
        ("log", "DevHarness: enabled"),
        "steam",
        ("send", "load-level"),
        ("log", "KillFloor: armed"),
        ("send", "invulnerable"),
        ("send", "editor"),
    ]


def test_relaunch_fails_with_the_exact_error_when_the_harness_never_becomes_ready(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, harness_ready=False)
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert "relaunch: harness did not become ready" in errors


def test_relaunch_fails_when_steamworks_never_becomes_ready(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, steam_ready=False)
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert "relaunch: Steamworks did not become ready" in errors


def test_relaunch_retries_the_load_and_gives_up_after_five_attempts(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch, kill_floor=False)
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None)
    assert ok is False
    loads = [c for c in calls if c == ("send", "load-level")]
    assert len(loads) == 5
    assert ("send", "invulnerable") not in calls
    assert ("send", "editor") not in calls


def test_relaunch_stops_at_once_when_the_editor_does_not_support_the_map(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch, unsupported=True)
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert [c for c in calls if c == ("send", "load-level")] == [("send", "load-level")]
    assert ("send", "invulnerable") not in calls
    assert ("send", "editor") not in calls
    assert errors == ["relaunch: the editor does not support this map; see the EditorMode warning in the game log"]


def test_wait_for_any_log_line_returns_the_first_line_found(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text("start\nEditorMode: unsupported map Desert\n")
    found = run.wait_for_any_log_line(log, ["KillFloor: armed", "EditorMode: unsupported map"], 0, 1)
    assert found == "EditorMode: unsupported map"


def test_wait_for_any_log_line_returns_none_on_timeout(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text("nothing relevant\n")
    assert run.wait_for_any_log_line(log, ["KillFloor: armed"], 0, 0) is None


def test_build_key_command_tap_carries_modifiers_only_when_given() -> None:
    assert run.build_key_command("tap", "R") == {"command": "key", "action": "tap", "key": "R"}
    assert run.build_key_command("tap", "R", ["LeftShift"]) == {
        "command": "key",
        "action": "tap",
        "key": "R",
        "modifiers": ["LeftShift"],
    }


def test_key_payload_maps_flags_to_the_action() -> None:
    assert run.key_payload(run.parse_args(["key", "Escape"])) == {"command": "key", "action": "tap", "key": "Escape"}
    assert run.key_payload(run.parse_args(["key", "--down", "W"])) == {"command": "key", "action": "down", "key": "W"}
    assert run.key_payload(run.parse_args(["key", "--up", "W"])) == {"command": "key", "action": "up", "key": "W"}
    args = run.parse_args(["key", "R", "--mod", "LeftShift", "--mod", "LeftControl"])
    assert run.key_payload(args)["modifiers"] == ["LeftShift", "LeftControl"]


def test_key_payload_rejects_modifiers_on_down_and_up() -> None:
    with pytest.raises(SystemExit):
        run.key_payload(run.parse_args(["key", "--down", "W", "--mod", "LeftShift"]))


def test_key_down_and_up_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["key", "--down", "--up", "W"])


def test_build_mouse_command_includes_only_the_given_fields() -> None:
    assert run.build_mouse_command("clear") == {"command": "mouse", "action": "clear"}
    assert run.build_mouse_command("move", (960.0, 540.0)) == {"command": "mouse", "action": "move", "x": 960.0, "y": 540.0}
    assert run.build_mouse_command("click", (1.0, 2.0), 1) == {
        "command": "mouse",
        "action": "click",
        "x": 1.0,
        "y": 2.0,
        "button": 1,
    }
    assert run.build_mouse_command("down", None, 2) == {"command": "mouse", "action": "down", "button": 2}


def test_build_click_widget_command_carries_the_name() -> None:
    assert run.build_click_widget_command("Save") == {"command": "click-widget", "name": "Save"}


def test_build_ui_tree_command_includes_the_point_only_when_given() -> None:
    assert run.build_ui_tree_command() == {"command": "ui-tree"}
    assert run.build_ui_tree_command((10.0, 20.0)) == {"command": "ui-tree", "x": 10.0, "y": 20.0}


def test_widget_payloads_map_the_subcommands() -> None:
    assert run.click_widget_payload(run.parse_args(["click-widget", "Save"])) == {"command": "click-widget", "name": "Save"}
    assert run.ui_tree_payload(run.parse_args(["ui-tree"])) == {"command": "ui-tree"}
    assert run.ui_tree_payload(run.parse_args(["ui-tree", "5", "6"])) == {"command": "ui-tree", "x": 5.0, "y": 6.0}


def test_ui_tree_payload_rejects_half_a_point() -> None:
    with pytest.raises(SystemExit, match="both X and Y"):
        run.ui_tree_payload(run.parse_args(["ui-tree", "5"]))


def test_mouse_payload_maps_the_subcommands() -> None:
    assert run.mouse_payload(run.parse_args(["mouse", "move", "960", "540"])) == {
        "command": "mouse",
        "action": "move",
        "x": 960.0,
        "y": 540.0,
    }
    assert run.mouse_payload(run.parse_args(["mouse", "click"])) == {"command": "mouse", "action": "click"}
    assert run.mouse_payload(run.parse_args(["mouse", "click", "--button", "1", "10", "20"])) == {
        "command": "mouse",
        "action": "click",
        "x": 10.0,
        "y": 20.0,
        "button": 1,
    }
    assert run.mouse_payload(run.parse_args(["mouse", "down"])) == {"command": "mouse", "action": "down"}
    assert run.mouse_payload(run.parse_args(["mouse", "up"])) == {"command": "mouse", "action": "up"}
    assert run.mouse_payload(run.parse_args(["mouse", "clear"])) == {"command": "mouse", "action": "clear"}


@pytest.mark.parametrize(
    "argv",
    [
        ["mouse", "move"],
        ["mouse", "move", "1"],
        ["mouse", "click", "1"],
        ["mouse", "clear", "1", "2"],
        ["mouse", "click", "--button", "3"],
    ],
)
def test_mouse_payload_rejects_bad_coordinates_or_buttons(argv) -> None:
    with pytest.raises(SystemExit):
        run.mouse_payload(run.parse_args(argv))


def test_build_type_command_and_payload() -> None:
    assert run.build_type_command("chest") == {"command": "type", "text": "chest"}
    assert run.type_payload(run.parse_args(["type", "ab\b\n"])) == {"command": "type", "text": "ab\b\n"}


def test_key_mouse_and_type_send_their_payloads() -> None:
    for argv, name in ((("key", "R"), "key"), (("mouse", "move", "1", "2"), "mouse"), (("type", "hi"), "type")):
        with tempfile.TemporaryDirectory() as tmp:
            game = fake_game(tmp, None)
            assert run_main(game, *argv) == 0
            sent = list((game / "harness" / "done").glob(f"*-{name}.json"))
            assert len(sent) == 1


WINE_IDLE_LISTING = (
    "  10 C:\\windows\\system32\\services.exe \n"
    "  11 C:\\windows\\system32\\conhost.exe --server 0x94 \n"
    "  12 C:\\windows\\system32\\explorer.exe /desktop \n"
    "  13 C:\\windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted \n"
    "  14 C:\\windows\\system32\\lsass.exe \n"
    "  99 /sbin/launchd\n"
)


def test_find_wine_leftovers_splits_system_stubs_from_other_windows_processes() -> None:
    listing = WINE_IDLE_LISTING + '  20 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n'
    stubs, others = run.find_wine_leftovers(listing)
    assert stubs == [10, 11, 12, 13, 14]
    assert others == [20]


def test_find_wine_leftovers_ignores_native_processes() -> None:
    assert run.find_wine_leftovers("  1 /sbin/launchd\n") == ([], [])


def test_reap_wine_leftovers_kills_idle_stubs() -> None:
    killed: list[int] = []
    assert run.reap_wine_leftovers(WINE_IDLE_LISTING, killed.append) == 5
    assert killed == [10, 11, 12, 13, 14]


def test_reap_wine_leftovers_leaves_everything_when_a_real_windows_process_runs(capsys) -> None:
    killed: list[int] = []
    listing = WINE_IDLE_LISTING + "  20 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n"
    assert run.reap_wine_leftovers(listing, killed.append) == 0
    assert killed == []
    assert "skipping" in capsys.readouterr().out
