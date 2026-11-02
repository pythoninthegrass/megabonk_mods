"""
Self-test for scripts/run.py.
"""

import json
import os
import pytest
import run
import subprocess
import tempfile
import threading
import time
from pathlib import Path


@pytest.mark.parametrize("amount", [1, 5, 10, 37, 90, 99])
def test_damage_integer_amount_and_default_safety(amount) -> None:
    args = run.parse_args(["damage", str(amount)])
    assert run.build_damage_command(args.amount, args.nonlethal) == {"command": "damage", "amount": amount, "nonlethal": True}


def test_damage_explicit_lethal_opt_out() -> None:
    args = run.parse_args(["damage", "99", "--no-nonlethal"])
    assert run.build_damage_command(args.amount, args.nonlethal)["nonlethal"] is False


@pytest.mark.parametrize("amount", [0, -1, 100, 1.5, True, "5", None])
def test_damage_builder_rejects_invalid_amount(amount) -> None:
    with pytest.raises(ValueError, match="integer.*1.*99"):
        run.build_damage_command(amount)


@pytest.mark.parametrize("nonlethal", [None, "false", 0])
def test_damage_builder_rejects_nonboolean_safety(nonlethal) -> None:
    with pytest.raises(ValueError, match="boolean"):
        run.build_damage_command(5, nonlethal)


@pytest.mark.parametrize("amount", ["0", "-1", "100", "1.5", "five"])
def test_damage_cli_rejects_invalid_amount(amount) -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["damage", amount])


@pytest.mark.parametrize(
    "action",
    [
        "status", "play", "decode", "pitch", "lowpass", "detach", "native-info", "native-tone", "native-play",
        "radio-next", "seek", "menu-music", "stage-music",
    ],
)
def test_music_probe_action_does_not_replace_subcommand(action: str) -> None:
    args = run.parse_args(["music-probe", action])
    assert args.action == "music-probe"
    assert run.music_probe_payload(args) == {"command": "music-probe", "action": action}


def test_music_probe_payload_preserves_path_variant_and_zero_value() -> None:
    args = run.parse_args(["music-probe", "play", "06.01 Screamer.mp3", "--variant", "managed", "--value", "0"])
    assert run.music_probe_payload(args) == {
        "command": "music-probe",
        "action": "play",
        "path": "06.01 Screamer.mp3",
        "variant": "managed",
        "value": 0.0,
    }


def test_music_probe_rejects_unknown_action() -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["music-probe", "unknown"])


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


def test_build_command_kill_has_no_payload() -> None:
    assert run.build_command("kill") == {"command": "kill"}


def test_parse_args_kill_subcommand() -> None:
    assert run.parse_args(["kill"]).action == "kill"


def test_parse_args_invulnerable_and_vulnerable_subcommands() -> None:
    assert run.parse_args(["invulnerable"]).action == "invulnerable"
    assert run.parse_args(["vulnerable"]).action == "vulnerable"


def test_build_heartbeat_command_carries_the_enabled_flag() -> None:
    assert run.build_heartbeat_command(True) == {"command": "heartbeat", "enabled": True}
    assert run.build_heartbeat_command(False) == {"command": "heartbeat", "enabled": False}


def test_build_character_screen_command_carries_the_enabled_flag() -> None:
    assert run.build_character_screen_command(True) == {"command": "character-screen", "enabled": True}
    assert run.build_character_screen_command(False) == {"command": "character-screen", "enabled": False}


def test_build_spawns_command_carries_the_enabled_flag() -> None:
    assert run.build_spawns_command(True) == {"command": "spawns", "enabled": True}
    assert run.build_spawns_command(False) == {"command": "spawns", "enabled": False}


def test_spawns_payload_maps_the_state_to_the_wire_command() -> None:
    assert run.spawns_payload(run.parse_args(["spawns", "on"])) == {"command": "spawns", "enabled": True}
    assert run.spawns_payload(run.parse_args(["spawns", "off"])) == {"command": "spawns", "enabled": False}


def test_parse_args_spawns_rejects_other_states_and_a_missing_state() -> None:
    for argv in (["spawns"], ["spawns", "maybe"]):
        with pytest.raises(SystemExit):
            run.parse_args(argv)


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


def test_build_query_objects_command_carries_the_type_and_fields() -> None:
    assert run.build_query_objects_command("MapData", ["eMap"]) == {
        "command": "query-objects",
        "type": "MapData",
        "fields": ["eMap"],
    }
    assert run.build_query_objects_command("MapData") == {"command": "query-objects", "type": "MapData", "fields": []}


def test_build_teleport_command_carries_a_position_or_a_cell() -> None:
    assert run.build_teleport_command(position=(1.5, 0.0, -200.0)) == {"command": "teleport", "position": [1.5, 0.0, -200.0]}
    assert run.build_teleport_command(cell=(3, 12)) == {"command": "teleport", "cell": [3, 12]}


def test_build_item_command_reads_without_an_amount_and_sets_with_one() -> None:
    assert run.build_item_command("Mirror") == {"command": "item", "name": "Mirror"}
    assert run.build_item_command("Mirror", 0) == {"command": "item", "name": "Mirror", "amount": 0}
    assert run.build_item_command("Feathers", 3) == {"command": "item", "name": "Feathers", "amount": 3}


def test_item_payload_takes_a_name_and_an_optional_amount() -> None:
    assert run.item_payload(run.parse_args(["item", "Mirror"])) == {"command": "item", "name": "Mirror"}
    assert run.item_payload(run.parse_args(["item", "Mirror", "0"])) == {"command": "item", "name": "Mirror", "amount": 0}


def test_item_prints_the_result_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"item","ok":true,"result":{"item":"Mirror","before":3,"after":0}}')
        assert run_main(game, "item", "Mirror", "0") == 0
    printed = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(printed) == {"item": "Mirror", "before": 3, "after": 0}


def test_build_grind_slide_command_omits_held_when_the_device_is_read() -> None:
    assert run.build_grind_slide_command(True) == {"command": "grind-slide", "held": True}
    assert run.build_grind_slide_command(False) == {"command": "grind-slide", "held": False}
    assert run.build_grind_slide_command() == {"command": "grind-slide"}


def test_build_fall_damage_command_sends_the_bare_read() -> None:
    assert run.build_fall_damage_command() == {"command": "fall-damage"}


def test_parse_args_accepts_fall_damage_without_arguments() -> None:
    assert run.parse_args(["fall-damage"]).action == "fall-damage"
    with pytest.raises(SystemExit):
        run.parse_args(["fall-damage", "calcium"])


def test_grind_slide_payload_maps_the_state_to_the_wire_command() -> None:
    assert run.grind_slide_payload(run.parse_args(["grind-slide", "on"])) == {"command": "grind-slide", "held": True}
    assert run.grind_slide_payload(run.parse_args(["grind-slide", "off"])) == {"command": "grind-slide", "held": False}
    assert run.grind_slide_payload(run.parse_args(["grind-slide", "auto"])) == {"command": "grind-slide"}


def test_parse_args_grind_slide_rejects_other_states_and_a_missing_state() -> None:
    for argv in (["grind-slide"], ["grind-slide", "maybe"]):
        with pytest.raises(SystemExit):
            run.parse_args(argv)


def test_grind_slide_prints_the_result_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = fake_game(tmp, '{"command":"grind-slide","ok":true,"result":{"held":true,"slideHeld":true}}')
        assert run_main(game, "grind-slide", "on") == 0
    printed = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(printed) == {"held": True, "slideHeld": True}


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


def test_build_dismiss_offers_command_carries_the_choice_and_skip() -> None:
    assert run.build_dismiss_offers_command(None, False) == {"command": "dismiss-offers"}
    assert run.build_dismiss_offers_command(0, False) == {"command": "dismiss-offers", "choice": 0}
    assert run.build_dismiss_offers_command(2, False) == {"command": "dismiss-offers", "choice": 2}
    assert run.build_dismiss_offers_command(None, True) == {"command": "dismiss-offers", "skip": True}


def test_dismiss_offers_payload_defaults_to_closing_without_choosing() -> None:
    assert run.dismiss_offers_payload(run.parse_args(["dismiss-offers"])) == {"command": "dismiss-offers"}
    assert run.dismiss_offers_payload(run.parse_args(["dismiss-offers", "--choice", "2"])) == {
        "command": "dismiss-offers",
        "choice": 2,
    }
    assert run.dismiss_offers_payload(run.parse_args(["dismiss-offers", "--skip"])) == {
        "command": "dismiss-offers",
        "skip": True,
    }


def test_build_interact_command_carries_the_optional_filters() -> None:
    assert run.build_interact_command(None, None, False) == {"command": "interact"}
    assert run.build_interact_command("Magnet", None, False) == {"command": "interact", "type": "Magnet"}
    assert run.build_interact_command(None, 4.5, False) == {"command": "interact", "maxDistance": 4.5}
    assert run.build_interact_command("Magnet", 4.5, True) == {
        "command": "interact",
        "type": "Magnet",
        "maxDistance": 4.5,
        "force": True,
    }


def test_interact_payload_reads_the_cli_flags() -> None:
    assert run.interact_payload(run.parse_args(["interact"])) == {"command": "interact"}
    assert run.interact_payload(run.parse_args(["interact", "--type", "Magnet"])) == {
        "command": "interact",
        "type": "Magnet",
    }
    assert run.interact_payload(run.parse_args(["interact", "--max-distance", "4"])) == {
        "command": "interact",
        "maxDistance": 4.0,
    }
    assert run.interact_payload(run.parse_args(["interact", "--force"])) == {"command": "interact", "force": True}


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


def test_parse_args_relaunch_no_level_flag() -> None:
    assert run.parse_args(["relaunch", "--no-level"]).no_level is True
    assert run.parse_args(["relaunch"]).no_level is False


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
    results = iter(["not-ready", "not-ready", "ready"])
    assert run.wait_for_steamworks_ready(lambda: next(results), timeout=5, sleep=lambda _: None) == "ready"


def test_wait_for_steamworks_ready_times_out_without_an_answer() -> None:
    clock = iter(range(100))
    assert run.wait_for_steamworks_ready(lambda: None, timeout=3, sleep=lambda _: None, now=lambda: next(clock)) == "timeout"


def test_wait_for_steamworks_ready_reports_offline_after_the_grace_period() -> None:
    clock = iter(range(100))
    assert run.wait_for_steamworks_ready(lambda: "not-ready", timeout=60, sleep=lambda _: None, now=lambda: next(clock)) == "offline"


def test_wait_for_steamworks_ready_still_becomes_ready_within_the_grace() -> None:
    results = iter(["not-ready", "ready"])
    assert run.wait_for_steamworks_ready(lambda: next(results), timeout=60, sleep=lambda _: None) == "ready"


def test_wait_for_steamworks_ready_reports_dead_when_the_game_exits() -> None:
    assert run.wait_for_steamworks_ready(lambda: "not-ready", timeout=60, alive=lambda: False, sleep=lambda _: None) == "dead"


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


def relaunch_stubs(monkeypatch, *, harness_ready=True, steam_verdict="ready", kill_floor=True, unsupported=False, load_failed=False):
    calls = []
    monkeypatch.setattr(run, "quit_game", lambda h, t: calls.append("quit") or True)
    monkeypatch.setattr(run, "launch_game", lambda task: calls.append(("launch", task)) or True)
    monkeypatch.setattr(run, "force_kill_games", lambda context="quit": calls.append("force_kill") or 0)
    monkeypatch.setattr(run, "wait_for_wineserver_to_exit", lambda timeout=15.0: calls.append("wineserver") or True)
    monkeypatch.setattr(run, "clear_harness_queue", lambda h: calls.append("clear") or None)
    monkeypatch.setattr(run, "reap_wine_leftovers_on_host", lambda **kwargs: calls.append("reap") or None)
    monkeypatch.setattr(run, "wait_for_steamworks_ready", lambda probe, timeout, alive=None: calls.append("steam") or steam_verdict)
    monkeypatch.setattr(run, "send", lambda h, payload, t: calls.append(("send", payload["command"])) or True)

    def wait_log(log, line, newer, timeout, alive=None):
        calls.append(("log", line))
        return harness_ready

    def wait_any_log(log, lines, newer, timeout):
        calls.append(("log", lines[0]))
        if unsupported:
            return run.EDITOR_UNSUPPORTED_LINE
        if load_failed:
            return run.LOAD_FAILED_LINE
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
        "wineserver",
        "clear",
        ("launch", "game:run"),
        ("log", "DevHarness: enabled"),
        "steam",
        ("send", "load-level"),
        ("log", "KillFloor: armed"),
        ("send", "item"),
        ("send", "editor"),
    ]


def test_relaunch_without_a_level_stops_at_the_main_menu(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch)
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=lambda m: None)
    assert ok is True
    assert calls == ["quit", "wineserver", "clear", ("launch", "game:run"), ("log", "DevHarness: enabled"), "steam"]


def test_relaunch_without_a_level_still_fails_when_steamworks_never_answers(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, steam_verdict="timeout")
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert errors == ["relaunch: Steamworks did not become ready"]


def test_relaunch_continues_past_a_not_ready_steamworks_on_an_offline_run(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch, steam_verdict="offline")
    steps, errors = [], []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/lvl.json"), 5, "game:run", on_step=steps.append, on_error=errors.append)
    assert ok is True
    assert errors == []
    assert "relaunch: Steamworks not ready (offline run); continuing" in steps
    assert calls == ["quit", "wineserver", "clear", ("launch", "game:run"), ("log", "DevHarness: enabled"), "steam", ("send", "load-level"), ("log", "KillFloor: armed"), ("send", "item"), ("send", "editor")]


def test_relaunch_fails_when_the_wineserver_never_exits(monkeypatch) -> None:
    relaunch_stubs(monkeypatch)
    monkeypatch.setattr(run, "wait_for_wineserver_to_exit", lambda timeout=15.0: False)
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert errors == ["relaunch: wineserver did not exit before launch"]


def test_relaunch_reports_the_game_exiting_during_startup(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, harness_ready=False)
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=errors.append, is_alive=lambda: False)
    assert ok is False
    assert errors == ["relaunch: game exited during startup (see /g/MelonLoader/Latest.log)"]


def test_game_exited_error_appends_the_wine_log_tail(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_EVIDENCE_DIR", str(tmp_path / "evidence"))
    log = tmp_path / "MelonLoader" / "wine-latest.log"
    log.parent.mkdir(parents=True)
    log.write_text(
        "0024:err:module:import_dll Library foo.dll not found\n"
        "\n"
        "wine: game process exited with status -11\n",
        encoding="utf-8",
    )
    message = run.game_exited_error(tmp_path)
    assert message.startswith("relaunch: game exited during startup (see")
    assert "  wine: game process exited with status -11" in message
    assert "  0024:err:module:import_dll Library foo.dll not found" in message


def test_game_exited_error_without_a_wine_log_is_unchanged(tmp_path) -> None:
    assert run.game_exited_error(tmp_path) == f"relaunch: game exited during startup (see {tmp_path}/MelonLoader/Latest.log)"


def evidence_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("MEGABONK_EVIDENCE_DIR", str(tmp_path / "evidence"))
    game = tmp_path / "game"
    (game / "MelonLoader").mkdir(parents=True)
    (game / "MelonLoader" / "wine-latest.log").write_text("wine log\n", encoding="utf-8")
    (game / "MelonLoader" / "Latest.log").write_text("melon log\n", encoding="utf-8")
    players = tmp_path / "prefix" / "drive_c/users/crossover/AppData/LocalLow/Ved/Megabonk"
    players.mkdir(parents=True)
    (players / "Player.log").write_text("player log\n", encoding="utf-8")
    monkeypatch.setattr(run, "wine_prefix", lambda game_dir: tmp_path / "prefix")
    return game


def test_save_failure_evidence_copies_every_launch_log(tmp_path, monkeypatch) -> None:
    game = evidence_tree(tmp_path, monkeypatch)
    saved = run.save_failure_evidence(game)
    assert saved is not None
    assert saved.parent == tmp_path / "evidence"
    assert sorted(path.name for path in saved.iterdir()) == ["Latest.log", "Player.log", "wine-latest.log"]
    assert (saved / "wine-latest.log").read_text(encoding="utf-8") == "wine log\n"


def test_save_failure_evidence_returns_none_when_nothing_was_written(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEGABONK_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setattr(run, "wine_prefix", lambda game_dir: None)
    assert run.save_failure_evidence(tmp_path / "game") is None
    assert not (tmp_path / "evidence").exists()


def test_game_exited_error_names_the_saved_evidence_folder(tmp_path, monkeypatch) -> None:
    game = evidence_tree(tmp_path, monkeypatch)
    message = run.game_exited_error(game)
    assert "evidence saved to " in message
    assert str(tmp_path / "evidence") in message


def test_unity_crash_handler_diag_hides_and_restores_the_handler(tmp_path, monkeypatch) -> None:
    game = tmp_path / "game"
    game.mkdir()
    handler = game / "UnityCrashHandler64.exe"
    handler.write_text("exe", encoding="utf-8")
    runs = []
    monkeypatch.setattr(run, "wine_bin", lambda: Path("/w/wine"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: tmp_path / "prefix")
    monkeypatch.setattr(run.subprocess, "run", lambda cmd, **kwargs: runs.append(cmd))
    monkeypatch.delenv("MEGABONK_WINEDEBUG_EXTRA", raising=False)
    run.unity_crash_handler_diag(game, True)
    assert not handler.exists()
    assert (game / "UnityCrashHandler64.exe.disabled").read_text(encoding="utf-8") == "exe"
    assert os.environ["MEGABONK_WINEDEBUG_EXTRA"] == "+seh"
    assert runs[0][:3] == ["/w/wine", "reg", "add"]
    assert "ShowCrashDialog" in runs[0]
    run.unity_crash_handler_diag(game, False)
    assert handler.read_text(encoding="utf-8") == "exe"
    assert not (game / "UnityCrashHandler64.exe.disabled").exists()
    assert "MEGABONK_WINEDEBUG_EXTRA" not in os.environ


def test_relaunch_diag_prepares_the_crash_handler_before_launching(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch)
    monkeypatch.setattr(run, "unity_crash_handler_diag", lambda game_dir, diag: calls.append(("diag", diag)))
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=lambda m: None, diag=True)
    assert ok is True
    assert calls[:5] == ["quit", "wineserver", "clear", ("diag", True), ("launch", "game:run")]


def test_resolve_relaunch_diag_defaults_to_off() -> None:
    assert run.resolve_relaunch_diag({}.get) is False


def test_resolve_relaunch_diag_reads_the_setting() -> None:
    for value in ("1", "true", "YES", "on"):
        assert run.resolve_relaunch_diag({"MEGABONK_RELAUNCH_DIAG": value}.get) is True
    for value in ("0", "false", "no", "off"):
        assert run.resolve_relaunch_diag({"MEGABONK_RELAUNCH_DIAG": value}.get) is False


def test_relaunch_leaves_no_game_or_wine_processes_after_a_failure(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch, harness_ready=False)
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=lambda m: None, is_alive=lambda: False)
    assert ok is False
    assert calls[-2:] == ["force_kill", "reap"]


def test_relaunch_reports_a_game_dying_while_steamworks_is_awaited(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, steam_verdict="dead")
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), None, 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert errors == ["relaunch: game exited during startup (see /g/MelonLoader/Latest.log)"]


def test_wait_for_any_log_line_gives_up_when_the_game_exits(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text("nothing useful yet\n", encoding="utf-8")
    started = time.time()
    assert run.wait_for_any_log_line(log, ["DevHarness: enabled"], started, 30, alive=lambda: False) is None


def test_steam_ready_verdict_classifies_the_result(monkeypatch) -> None:
    cases = [
        ((True, {"result": {"ready": False}}), "not-ready"),
        ((True, {"result": {"ready": True, "buildId": "21750826"}}), "ready"),
        ((True, {"result": None}), "ready"),
        ((True, None), "ready"),
        ((False, None), None),
    ]
    for (ok, result), expected in cases:
        monkeypatch.setattr(run, "send_for_result", lambda harness, payload, timeout, ok=ok, result=result: (ok, result))
        assert run.steam_ready_verdict(Path("/h"), 5) == expected


def test_run_main_exits_130_on_keyboard_interrupt(monkeypatch) -> None:
    def interrupted(argv=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(run, "main", interrupted)
    assert run.run_main([]) == 130


def test_relaunch_sets_two_feathers_before_entering_the_editor(monkeypatch) -> None:
    sent = []
    relaunch_stubs(monkeypatch)
    monkeypatch.setattr(run, "send", lambda h, payload, t: sent.append(payload) or True)
    run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None)
    assert sent[-2:] == [{"command": "item", "name": "Feathers", "amount": 2}, {"command": "editor", "enabled": True}]


def test_relaunch_with_zero_feathers_sends_no_item_command(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch)
    run.relaunch(
        Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None, feathers=0
    )
    assert ("send", "item") not in calls


def test_resolve_relaunch_feathers_defaults_to_two() -> None:
    assert run.resolve_relaunch_feathers({}.get) == 2


def test_resolve_relaunch_feathers_reads_the_setting() -> None:
    assert run.resolve_relaunch_feathers({"MEGABONK_RELAUNCH_FEATHERS": "5"}.get) == 5
    assert run.resolve_relaunch_feathers({"MEGABONK_RELAUNCH_FEATHERS": "0"}.get) == 0


def test_resolve_relaunch_feathers_rejects_a_bad_value() -> None:
    for value in ("many", "-1", "1000"):
        with pytest.raises(SystemExit):
            run.resolve_relaunch_feathers({"MEGABONK_RELAUNCH_FEATHERS": value}.get)


def test_relaunch_with_invulnerable_sends_it_before_entering_the_editor(monkeypatch) -> None:
    sent = []
    relaunch_stubs(monkeypatch)
    monkeypatch.setattr(run, "send", lambda h, payload, t: sent.append(payload) or True)
    run.relaunch(
        Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None, invulnerable=True
    )
    assert sent[-3:] == [
        {"command": "invulnerable"},
        {"command": "item", "name": "Feathers", "amount": 2},
        {"command": "editor", "enabled": True},
    ]


def test_relaunch_with_spawns_disabled_sends_spawns_off_before_entering_the_editor(monkeypatch) -> None:
    sent = []
    relaunch_stubs(monkeypatch)
    monkeypatch.setattr(run, "send", lambda h, payload, t: sent.append(payload) or True)
    run.relaunch(
        Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None, spawns=False
    )
    assert sent[-3:] == [
        {"command": "item", "name": "Feathers", "amount": 2},
        {"command": "spawns", "enabled": False},
        {"command": "editor", "enabled": True},
    ]
    assert {"command": "invulnerable"} not in sent


def test_relaunch_leaves_spawns_and_damage_at_the_game_default(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch)
    run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=lambda m: None)
    assert ("send", "spawns") not in calls
    assert ("send", "invulnerable") not in calls


def test_resolve_relaunch_spawns_defaults_to_on() -> None:
    assert run.resolve_relaunch_spawns({}.get) is True


def test_resolve_relaunch_spawns_reads_the_setting() -> None:
    for value in ("false", "0", "no", "off", "FALSE"):
        assert run.resolve_relaunch_spawns({"MEGABONK_RELAUNCH_SPAWNS": value}.get) is False
    for value in ("true", "1", "yes", "on"):
        assert run.resolve_relaunch_spawns({"MEGABONK_RELAUNCH_SPAWNS": value}.get) is True


def test_resolve_relaunch_invulnerable_defaults_to_off() -> None:
    assert run.resolve_relaunch_invulnerable({}.get) is False


def test_resolve_relaunch_invulnerable_reads_the_setting() -> None:
    for value in ("true", "1", "yes", "on", "TRUE"):
        assert run.resolve_relaunch_invulnerable({"MEGABONK_RELAUNCH_INVULNERABLE": value}.get) is True
    for value in ("false", "0", "no", "off"):
        assert run.resolve_relaunch_invulnerable({"MEGABONK_RELAUNCH_INVULNERABLE": value}.get) is False


def test_relaunch_fails_with_the_exact_error_when_the_harness_never_becomes_ready(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, harness_ready=False)
    errors = []
    ok = run.relaunch(
        Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append, is_alive=lambda: True
    )
    assert ok is False
    assert "relaunch: harness did not become ready" in errors


def test_relaunch_fails_when_steamworks_never_becomes_ready(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, steam_verdict="timeout")
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


def test_log_line_containing_returns_the_full_matching_line(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text("DevHarness: enabled\n[12:00:01] LevelLoader: load failed: no MapData found for map=32\n")
    assert (
        run.log_line_containing(log, run.LOAD_FAILED_LINE) == "[12:00:01] LevelLoader: load failed: no MapData found for map=32"
    )


def test_log_line_containing_uses_only_the_last_session_and_its_first_match(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text(
        "LevelLoader: load failed: old session\n"
        "DevHarness: enabled\n"
        "LevelLoader: load failed: first\n"
        "DevHarness: enabled\n"
        "LevelLoader: load failed: second\n"
        "LevelLoader: load failed: third\n"
    )
    assert run.log_line_containing(log, run.LOAD_FAILED_LINE) == "LevelLoader: load failed: second"


def test_log_line_containing_ignores_matches_before_the_last_launch_marker(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text("LevelLoader: load failed: old\nDevHarness: enabled\n")
    assert run.log_line_containing(log, run.LOAD_FAILED_LINE) is None


def test_log_line_containing_searches_the_whole_log_without_a_launch_marker(tmp_path) -> None:
    log = tmp_path / "Latest.log"
    log.write_text("EditorMode: unsupported map Desert\n")
    assert run.log_line_containing(log, run.EDITOR_UNSUPPORTED_LINE) == "EditorMode: unsupported map Desert"


def test_log_line_containing_returns_none_for_a_missing_log(tmp_path) -> None:
    assert run.log_line_containing(tmp_path / "absent.log", run.LOAD_FAILED_LINE) is None


def test_relaunch_load_failure_error_includes_the_log_line(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, load_failed=True)
    monkeypatch.setattr(run, "log_line_containing", lambda log, marker: f"seen {marker}: no MapData found for map=32")
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert errors == ["relaunch: the level failed to load: seen LevelLoader: load failed: no MapData found for map=32"]


def test_relaunch_unsupported_map_error_includes_the_log_line(monkeypatch) -> None:
    relaunch_stubs(monkeypatch, unsupported=True)
    monkeypatch.setattr(run, "log_line_containing", lambda log, marker: "EditorMode: unsupported map Desert")
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert errors == ["relaunch: the editor does not support this map: EditorMode: unsupported map Desert"]


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


def test_material_dump_command_carries_the_optional_object() -> None:
    assert run.build_material_dump_command() == {"command": "material-dump"}
    assert run.build_material_dump_command("Warehouse") == {"command": "material-dump", "object": "Warehouse"}
    assert run.material_dump_payload(run.parse_args(["material-dump"])) == {"command": "material-dump"}
    assert run.material_dump_payload(run.parse_args(["material-dump", "Warehouse"])) == {"command": "material-dump", "object": "Warehouse"}


def test_level_commands_carry_the_optional_level() -> None:
    assert run.build_save_level_command() == {"command": "save-level"}
    assert run.build_save_level_command("my level") == {"command": "save-level", "level": "my level"}
    assert run.build_command("list-levels") == {"command": "list-levels"}
    assert run.save_level_payload(run.parse_args(["save-level"])) == {"command": "save-level"}
    assert run.save_level_payload(run.parse_args(["save-level", "my"])) == {"command": "save-level", "level": "my"}


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
    stubs, others, orphans = run.find_wine_leftovers(listing)
    assert stubs == [10, 11, 12, 13, 14]
    assert others == [20]
    assert orphans == []


def test_find_wine_leftovers_splits_orphaned_game_helpers_from_steam() -> None:
    listing = '  21 C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\UnityCrashHandler64.exe 32 28839936\n'
    listing += '  20 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n'
    stubs, others, orphans = run.find_wine_leftovers(listing)
    assert stubs == []
    assert others == [20]
    assert orphans == [21]


def test_find_wine_leftovers_ignores_native_processes() -> None:
    assert run.find_wine_leftovers("  1 /sbin/launchd\n") == ([], [], [])


def test_reap_wine_leftovers_kills_idle_stubs() -> None:
    killed: list[int] = []
    assert run.reap_wine_leftovers(WINE_IDLE_LISTING, killed.append) == 5
    assert killed == [10, 11, 12, 13, 14]


def test_reap_wine_leftovers_kills_orphaned_game_helpers_with_the_stubs() -> None:
    killed: list[int] = []
    listing = WINE_IDLE_LISTING + "  21 C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\UnityCrashHandler64.exe 32 28839936\n"
    assert run.reap_wine_leftovers(listing, killed.append) == 6
    assert killed == [10, 11, 12, 13, 14, 21]


def test_reap_wine_leftovers_leaves_everything_when_a_real_windows_process_runs(capsys) -> None:
    killed: list[int] = []
    listing = WINE_IDLE_LISTING + "  20 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n"
    assert run.reap_wine_leftovers(listing, killed.append) == 0
    assert killed == []
    assert "skipping" in capsys.readouterr().out


def test_reap_wine_leftovers_leaves_orphans_when_steam_runs(capsys) -> None:
    killed: list[int] = []
    listing = WINE_IDLE_LISTING + "  20 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n"
    listing += "  21 C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\UnityCrashHandler64.exe 32 28839936\n"
    assert run.reap_wine_leftovers(listing, killed.append) == 0
    assert killed == []
    assert "skipping" in capsys.readouterr().out


def test_force_kill_wine_leftovers_sigkills_stubs_and_orphans(monkeypatch, capsys) -> None:
    listing = WINE_IDLE_LISTING + "  21 " + CRASH_HANDLER_PS_LINE + "\n"
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=listing))
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
    assert run.force_kill_wine_leftovers() == 6
    assert killed == [(10, 9), (11, 9), (12, 9), (13, 9), (14, 9), (21, 9)]
    assert "force-killed 6 stubborn Wine processes" in capsys.readouterr().out


def test_force_kill_wine_leftovers_skips_while_steam_runs(monkeypatch) -> None:
    listing = WINE_IDLE_LISTING + "  20 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n"
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=listing))
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
    assert run.force_kill_wine_leftovers() == 0
    assert killed == []


def test_reap_wine_leftovers_on_host_escalates_survivors_after_the_grace(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=WINE_IDLE_LISTING))
    signaled: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: signaled.append((pid, sig)))
    forced: list[str] = []
    monkeypatch.setattr(run, "force_kill_wine_leftovers", lambda context="quit": forced.append(context) or 0)
    run.reap_wine_leftovers_on_host("Darwin", sleep=lambda _: None)
    assert [sig for _, sig in signaled] == [15] * 5
    assert forced == ["quit"]


def test_reap_wine_leftovers_on_host_skips_the_grace_when_nothing_runs(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="  99 /sbin/launchd\n"))
    slept: list[float] = []
    forced: list[str] = []
    monkeypatch.setattr(run, "force_kill_wine_leftovers", lambda context="quit": forced.append(context) or 0)
    run.reap_wine_leftovers_on_host("Darwin", sleep=slept.append)
    assert slept == []
    assert forced == []


GAME_DIR_PS_LINE = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\Megabonk.exe"
CRASH_HANDLER_PS_LINE = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megabonk\\UnityCrashHandler64.exe 32 28839936"


def test_find_harness_pids_matches_game_dir_processes() -> None:
    listing = (
        f"  5 {GAME_DIR_PS_LINE} \n"
        f"  6 {CRASH_HANDLER_PS_LINE} \n"
        "  7 C:\\windows\\system32\\services.exe \n"
        "  8 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n"
        "  9 /sbin/launchd\n"
    )
    assert run.find_harness_pids(listing) == [5, 6]


def test_force_kill_games_kills_only_game_dir_processes(monkeypatch) -> None:
    listing = f"  5 {GAME_DIR_PS_LINE} \n  6 {CRASH_HANDLER_PS_LINE} \n  8 C:\\Program Files (x86)\\Steam\\steam.exe -silent\n"
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=listing))
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
    assert run.force_kill_games() == 2
    assert killed == [(5, 9), (6, 9)]


def test_quit_game_force_kills_a_wedged_game(monkeypatch, capsys) -> None:
    state = {"alive": True}
    monkeypatch.setattr(run, "running_game_pids", lambda: [5] if state["alive"] else [])
    monkeypatch.setattr(run, "send", lambda h, payload, t: False)
    monkeypatch.setattr(run, "wait_for_exit", lambda timeout: not state["alive"])
    monkeypatch.setattr(run, "reap_wine_leftovers_on_host", lambda: None)
    killed: list[int] = []

    def force_kill() -> int:
        state["alive"] = False
        killed.append(1)
        return 1

    ok = run.quit_game(Path("/h"), 5, force_kill=force_kill)
    assert ok is True
    assert killed == [1]
    assert "game exited" in capsys.readouterr().out


def test_quit_game_reports_a_game_that_survives_the_force_kill(monkeypatch, capsys) -> None:
    monkeypatch.setattr(run, "running_game_pids", lambda: [5])
    monkeypatch.setattr(run, "send", lambda h, payload, t: False)
    monkeypatch.setattr(run, "wait_for_exit", lambda timeout: False)
    monkeypatch.setattr(run, "reap_wine_leftovers_on_host", lambda: None)
    ok = run.quit_game(Path("/h"), 5, force_kill=lambda: 1)
    assert ok is False
    assert "force kill" in capsys.readouterr().err


def test_quit_game_clears_nothing_and_force_kills_nothing_when_the_harness_answers(monkeypatch) -> None:
    monkeypatch.setattr(run, "running_game_pids", lambda: [5])
    monkeypatch.setattr(run, "send", lambda h, payload, t: True)
    monkeypatch.setattr(run, "wait_for_exit", lambda timeout: True)
    reaped: list[int] = []
    monkeypatch.setattr(run, "reap_wine_leftovers_on_host", lambda: reaped.append(1))
    killed: list[int] = []
    assert run.quit_game(Path("/h"), 5, force_kill=lambda: killed.append(1) or 1) is True
    assert killed == []
    assert reaped == [1]


def test_clear_harness_queue_empties_the_queue_folders(tmp_path) -> None:
    harness = tmp_path / "harness"
    for folder in ("commands", "processing", "done", "rejected", "results"):
        (harness / folder).mkdir(parents=True)
        (harness / folder / "179-quit.json").write_text("{}", encoding="utf-8")
    run.clear_harness_queue(harness)
    for folder in ("commands", "processing", "done", "rejected", "results"):
        assert list((harness / folder).iterdir()) == []


def test_wait_for_wineserver_to_exit_returns_immediately_when_none_runs(monkeypatch) -> None:
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: [])
    assert run.wait_for_wineserver_to_exit() is True


def test_wait_for_wineserver_to_exit_waits_for_the_server(monkeypatch) -> None:
    servers = iter([[7], []])
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: next(servers))
    monkeypatch.setattr(run, "running_game_pids", lambda: [])
    monkeypatch.setattr(run, "wineserver_binary", lambda: run.Path("/wine/bin/wineserver"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: run.Path("/prefix"))
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert run.wait_for_wineserver_to_exit() is True
    assert calls == [["/wine/bin/wineserver", "-w"]]


def test_wait_for_wineserver_to_exit_fails_when_the_server_survives(monkeypatch) -> None:
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: [7])
    monkeypatch.setattr(run, "wineserver_binary", lambda: run.Path("/wine/bin/wineserver"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: run.Path("/prefix"))
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0))
    monkeypatch.setattr(run, "force_kill_wine_leftovers", lambda context="quit": 0)
    assert run.wait_for_wineserver_to_exit() is False


def test_wait_for_wineserver_to_exit_fails_when_the_timeout_expires(monkeypatch) -> None:
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: [7])
    monkeypatch.setattr(run, "wineserver_binary", lambda: run.Path("/wine/bin/wineserver"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: run.Path("/prefix"))

    def expire(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(subprocess, "run", expire)
    monkeypatch.setattr(run, "force_kill_wine_leftovers", lambda context="quit": 0)
    monkeypatch.setattr(run.time, "sleep", lambda _: None)
    assert run.wait_for_wineserver_to_exit() is False


def test_wait_for_wineserver_to_exit_kills_a_server_that_outlives_the_wait(monkeypatch, capsys) -> None:
    servers = iter([[7], [7], [7], []])
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: next(servers))
    monkeypatch.setattr(run, "running_game_pids", lambda: [])
    monkeypatch.setattr(run, "wineserver_binary", lambda: run.Path("/wine/bin/wineserver"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: run.Path("/prefix"))
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0))
    killed: list[int] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append(pid))
    forced: list[str] = []
    monkeypatch.setattr(run, "force_kill_wine_leftovers", lambda context="quit": forced.append(context) or 0)
    monkeypatch.setattr(run.time, "sleep", lambda _: None)
    assert run.wait_for_wineserver_to_exit() is True
    assert killed == [7]
    assert forced == ["relaunch"]
    assert "force-killed 1 lingering wineserver(s)" in capsys.readouterr().out


def test_wait_for_wineserver_to_exit_fails_when_a_killed_server_survives(monkeypatch) -> None:
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: [7])
    monkeypatch.setattr(run, "running_game_pids", lambda: [])
    monkeypatch.setattr(run, "wineserver_binary", lambda: run.Path("/wine/bin/wineserver"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: run.Path("/prefix"))
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0))
    monkeypatch.setattr(os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(run, "force_kill_wine_leftovers", lambda context="quit": 0)
    monkeypatch.setattr(run.time, "sleep", lambda _: None)
    assert run.wait_for_wineserver_to_exit() is False


def test_wait_for_wineserver_to_exit_fails_when_a_game_appears(monkeypatch) -> None:
    servers = iter([[7], []])
    monkeypatch.setattr(run, "running_wineserver_pids", lambda: next(servers))
    monkeypatch.setattr(run, "running_game_pids", lambda: [5])
    monkeypatch.setattr(run, "wineserver_binary", lambda: run.Path("/wine/bin/wineserver"))
    monkeypatch.setattr(run, "resolve_wine_prefix", lambda: run.Path("/prefix"))
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0))
    assert run.wait_for_wineserver_to_exit() is False


def test_relaunch_fails_fast_when_the_level_fails_to_load(monkeypatch) -> None:
    calls = relaunch_stubs(monkeypatch, load_failed=True)
    errors = []
    ok = run.relaunch(Path("/h"), Path("/g"), Path("/l"), 5, "game:run", on_step=lambda m: None, on_error=errors.append)
    assert ok is False
    assert len([c for c in calls if c == ("send", "load-level")]) == 1
    assert errors == ["relaunch: the level failed to load; see the LevelLoader line in the game log"]


def test_build_load_level_command_adds_the_character_when_named() -> None:
    assert run.build_load_level_command("p", character="calcium") == {**run.build_command("load-level", "p"), "character": "calcium"}


def test_build_load_level_command_without_overrides_matches_the_plain_command() -> None:
    assert run.build_load_level_command("Z:\\a.json") == run.build_command("load-level", "Z:\\a.json")


def test_build_load_level_command_adds_only_the_supplied_overrides() -> None:
    assert run.build_load_level_command("p", map=64, stage=1, seed=0) == {
        "command": "load-level",
        "path": "p",
        "map": 64,
        "stageIndex": 1,
        "seed": 0,
    }


def test_parse_args_load_and_relaunch_take_integer_overrides() -> None:
    for action in ("load", "relaunch"):
        args = run.parse_args([action, "a.json", "--map", "64", "--stage", "1", "--tier", "2", "--seed", "7"])
        assert (args.map, args.stage, args.tier, args.seed) == (64, 1, 2, 7)


def test_parse_args_overrides_default_to_none() -> None:
    args = run.parse_args(["load", "a.json"])
    assert (args.map, args.stage, args.tier, args.seed) == (None, None, None, None)


def test_parse_args_rejects_a_non_integer_override(capsys) -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["load", "a.json", "--stage", "one"])
    assert "--stage" in capsys.readouterr().err


def test_load_sends_the_overrides_and_leaves_the_level_file_alone() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        level = Path(tmp) / "level.mblevel.json"
        level.write_text('{"map":1}')
        game = fake_game(tmp, '{"command":"load-level","ok":true}')
        assert run_main(game, "load", str(level), "--map", "64", "--seed", "9") == 0
        sent = json.loads(next((game / "harness" / "done").glob("*.json")).read_text())
        assert (sent["map"], sent["seed"]) == (64, 9)
        assert "stageIndex" not in sent and "tier" not in sent
        assert level.read_text() == '{"map":1}'
        assert sorted(p.name for p in Path(tmp).glob("*.json")) == ["level.mblevel.json"]


def test_relaunch_forwards_the_overrides_to_the_load(monkeypatch) -> None:
    relaunch_stubs(monkeypatch)
    sent = []
    monkeypatch.setattr(run, "send", lambda h, payload, t: sent.append(payload) or True)
    ok = run.relaunch(
        Path("/h"),
        Path("/g"),
        Path("/l"),
        5,
        "game:run",
        on_step=lambda m: None,
        on_error=lambda m: None,
        overrides={"map": 64, "stage": 1},
    )
    assert ok is True
    load = next(p for p in sent if p["command"] == "load-level")
    assert (load["map"], load["stageIndex"]) == (64, 1)


@pytest.mark.parametrize(
    "verb",
    ["report", "status", "start", "reset", "spawn", "timescale", "toggle", "vsync", "health"],
)
def test_perf_verb_is_a_subcommand_argument(verb: str) -> None:
    args = run.parse_args(["perf", verb])
    assert args.action == "perf"
    assert args.perf_action == verb
    assert run.build_perf_command(verb) == {"command": "perf", "action": verb}


def test_perf_rejects_an_unknown_verb() -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["perf", "profile"])


def test_perf_spawn_payload_carries_the_count() -> None:
    args = run.parse_args(["perf", "spawn", "--count", "120"])
    assert run.perf_payload(args) == {"command": "perf", "action": "spawn", "count": 120}


@pytest.mark.parametrize("count", ["0", "301", "-1", "many", "1.5"])
def test_perf_spawn_rejects_counts_outside_the_range(count: str) -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["perf", "spawn", "--count", count])


def test_perf_spawn_without_a_count_stops() -> None:
    args = run.parse_args(["perf", "spawn"])
    with pytest.raises(SystemExit, match="count"):
        run.perf_payload(args)


def test_perf_timescale_payload_carries_the_value() -> None:
    args = run.parse_args(["perf", "timescale", "--value", "3.5"])
    assert run.perf_payload(args) == {"command": "perf", "action": "timescale", "value": 3.5}


def test_perf_timescale_without_a_value_releases_the_hold() -> None:
    args = run.parse_args(["perf", "timescale"])
    assert run.perf_payload(args) == {"command": "perf", "action": "timescale"}


@pytest.mark.parametrize("value", ["0", "-1", "20.5", "abc"])
def test_perf_timescale_rejects_values_outside_the_range(value: str) -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["perf", "timescale", "--value", value])


def test_perf_toggle_payload_carries_target_and_state() -> None:
    args = run.parse_args(["perf", "toggle", "--target", "EnemyHpBar.Update", "--disable"])
    assert run.perf_payload(args) == {
        "command": "perf",
        "action": "toggle",
        "target": "EnemyHpBar.Update",
        "enabled": False,
    }


def test_perf_toggle_needs_a_target() -> None:
    args = run.parse_args(["perf", "toggle", "--enable"])
    with pytest.raises(SystemExit, match="target"):
        run.perf_payload(args)


def test_perf_health_payload_carries_the_hp() -> None:
    args = run.parse_args(["perf", "health", "--hp", "250000"])
    assert run.perf_payload(args) == {"command": "perf", "action": "health", "hp": 250000}


def test_perf_health_without_hp_leaves_the_choice_to_the_profiler() -> None:
    assert run.perf_payload(run.parse_args(["perf", "health"])) == {"command": "perf", "action": "health"}


@pytest.mark.parametrize("hp", ["0", "-3", "100000001", "plenty"])
def test_perf_health_rejects_hp_outside_the_range(hp: str) -> None:
    with pytest.raises(SystemExit):
        run.parse_args(["perf", "health", "--hp", hp])


@pytest.mark.parametrize("flags", [[], ["--enable", "--disable"]])
def test_perf_toggle_needs_exactly_one_state_flag(flags: list[str]) -> None:
    args = run.parse_args(["perf", "toggle", "--target", "KillFloor", *flags])
    with pytest.raises(SystemExit, match="enable"):
        run.perf_payload(args)


def test_perf_report_and_reset_carry_no_arguments() -> None:
    assert run.perf_payload(run.parse_args(["perf", "report"])) == {"command": "perf", "action": "report"}
    assert run.perf_payload(run.parse_args(["perf", "reset"])) == {"command": "perf", "action": "reset"}


def test_perf_vsync_payload_carries_the_state() -> None:
    args = run.parse_args(["perf", "vsync", "--disable"])
    assert run.perf_payload(args) == {"command": "perf", "action": "vsync", "enabled": False}
    args = run.parse_args(["perf", "vsync", "--enable"])
    assert run.perf_payload(args) == {"command": "perf", "action": "vsync", "enabled": True}


@pytest.mark.parametrize("flags", [[], ["--enable", "--disable"]])
def test_perf_vsync_needs_exactly_one_state_flag(flags: list[str]) -> None:
    args = run.parse_args(["perf", "vsync", *flags])
    with pytest.raises(SystemExit, match="vsync"):
        run.perf_payload(args)
