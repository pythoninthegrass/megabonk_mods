#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#     "python-decouple>=3.8",
# ]
# ///

"""
Self-test for scripts/run.py.

Usage: uv run scripts/test_run.py
"""

import json
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run


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


def test_game_dir_macos_default_bottle() -> None:
    game = run.resolve_game_dir({}.get, system="Darwin")
    assert str(game).endswith("CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")


def test_game_dir_windows_default() -> None:
    game = run.resolve_game_dir({}.get, system="Windows")
    assert str(game) == r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk"


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


def main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
        except Exception:
            failed += 1
            print(f"FAIL {name}", file=sys.stderr)
            traceback.print_exc()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
