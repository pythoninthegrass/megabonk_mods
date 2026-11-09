import io
import json
import pytest
import run
import shlex
import subprocess
from pathlib import Path


@pytest.fixture(autouse=True)
def linux(monkeypatch):
    monkeypatch.setattr(run.platform, "system", lambda: "Linux")


def test_menu_parse_does_not_replace_editor_input():
    assert run.parse_args(["key", "Return"]).action == "key"
    args = run.parse_args(["menu", "drive", '[["pad","BTN_SOUTH"]]', "--out", "shot.png"])
    assert args.menu_action == "drive"
    assert args.out == Path("shot.png")


def test_menu_input_without_harness(monkeypatch, tmp_path):
    monkeypatch.setattr(run, "resolve_game_dir", lambda _: tmp_path)
    calls = []
    monkeypatch.setattr(run, "menu_request", lambda path, payload, timeout: calls.append(payload) or {"gamepad": True})
    monkeypatch.setattr(run.time, "sleep", lambda _: None)
    assert run.main(["menu", "drive", '[["key","KEY_ENTER"]]']) == 0
    assert calls[-1] == ["key", "KEY_ENTER"]


def test_menu_validates_whole_batch_before_contacting_service(monkeypatch):
    monkeypatch.setattr(run, "menu_request", lambda *args: pytest.fail("invalid batch contacted service"))
    assert run.run_main(["menu", "drive", '[["click"],["axis","ABS_HAT0Y",9]]']) == 1


def test_harness_requirement_is_checked_before_any_input(monkeypatch, tmp_path):
    monkeypatch.setattr(run, "resolve_game_dir", lambda _: tmp_path)
    monkeypatch.setattr(run, "menu_request", lambda *args: pytest.fail("input before harness preflight"))
    assert run.run_main(["menu", "drive", '[["click"]]', "--out", str(tmp_path / "shot.png")]) == 1


def test_rejected_diagnostic_aborts_batch_and_screenshot(monkeypatch, tmp_path):
    (tmp_path / "harness").mkdir()
    (tmp_path / "harness/enabled").touch()
    monkeypatch.setattr(run, "resolve_game_dir", lambda _: tmp_path)
    monkeypatch.setattr(run, "menu_request", lambda *args: {"gamepad": True})
    monkeypatch.setattr(run, "send_for_result", lambda *args: (False, {"ok": False, "error": "rejected"}))
    monkeypatch.setattr(run, "send_screenshot", lambda *args: pytest.fail("screenshot after rejection"))
    assert run.main(["menu", "drive", '[{"command":"state"}]', "--out", str(tmp_path / "shot.png")]) == 1


def test_remote_quoting_stdin_and_failed_ssh_no_download(monkeypatch):
    calls = []

    def invoke(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 23)

    monkeypatch.setattr(run.subprocess, "run", invoke)
    args = run.parse_args(["menu", "drive", '[["key","KEY_ENTER"]]', "--host", "wm2",
                           "--remote-repo", "/home/test/repo with 'quotes'", "--remote-python", "/venv with spaces/python",
                           "--game-dir", "/game; echo bad", "--out", "shot.png"])
    assert run.menu_remote(args, [["key", "KEY_ENTER"]]) == 23
    command, options = calls[0]
    assert command[:4] == ["ssh", "-oBatchMode=yes", "--", "wm2"]
    assert "cd '/home/test/repo with" in command[4]
    assert shlex.quote("/game; echo bad") in command[4]
    assert json.loads(options["input"]) == [["key", "KEY_ENTER"]]
    assert len(calls) == 1


def test_remote_requires_explicit_repository_and_safe_host():
    for options in [["--host", "wm2"], ["--host=-oProxyCommand=evil", "--remote-repo", "/repo"]]:
        args = run.parse_args(["menu", "status", *options])
        with pytest.raises(ValueError):
            run.menu_remote(args, None)


@pytest.mark.parametrize("data", [b"not an image", run.PNG_SIGNATURE + b"test image"])
def test_remote_screenshot_download_validates_before_replacing(monkeypatch, tmp_path, data):
    out = tmp_path / "local shot.png"
    out.write_bytes(b"existing image")
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=data)

    monkeypatch.setattr(run.subprocess, "run", invoke)
    args = run.parse_args(["menu", "drive", "[]", "--host", "wm2", "--remote-repo", "~/git/repo spaces", "--out", str(out)])
    if data.startswith(run.PNG_SIGNATURE):
        assert run.menu_remote(args, []) == 0
        assert out.read_bytes() == data
    else:
        with pytest.raises(RuntimeError, match="PNG"):
            run.menu_remote(args, [])
        assert out.read_bytes() == b"existing image"
    assert 'cd "$HOME"/' in calls[0][-1]
    assert "cat -- .tools/menu-" in calls[1][-1]
    assert not list(tmp_path.glob("*.tmp"))


def test_batch_file_stdin_and_oversize(monkeypatch, tmp_path):
    path = tmp_path / "actions.json"
    path.write_text('[["click"]]')
    assert run.read_menu_batch("@" + str(path)) == [["click"]]
    monkeypatch.setattr(run.sys, "stdin", io.StringIO("[]"))
    assert run.read_menu_batch("-") == []
    with pytest.raises(ValueError, match="64 KiB"):
        run.read_menu_batch("[]" + " " * 65536)


def test_service_start_failure_terminates_only_the_child(monkeypatch, tmp_path):
    class Child:
        killed = False

        def poll(self):
            return None

        def terminate(self):
            self.killed = True

        def wait(self, **kwargs):
            return 0

    child = Child()
    monkeypatch.setattr(run.shutil, "which", lambda _: None)
    monkeypatch.setattr(run.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(run.time, "monotonic", iter([0, 2]).__next__)
    args = run.parse_args(["--timeout", "1", "menu", "start"])
    with pytest.raises(RuntimeError, match="did not start"):
        run.start_menu_service(args, tmp_path / "input.sock")
    assert child.killed


def test_stop_waits_for_socket_cleanup(monkeypatch, tmp_path):
    path = tmp_path / "input.sock"
    path.touch()
    monkeypatch.setattr(run, "menu_request", lambda *args: {})
    monkeypatch.setattr(run.time, "sleep", lambda _: path.unlink())
    assert run.main(["menu", "stop", "--socket", str(path)]) == 0
    assert not path.exists()


def test_menu_screenshot_uses_existing_png_completion_check(monkeypatch, tmp_path):
    harness = tmp_path / "harness"
    harness.mkdir()
    (harness / "enabled").touch()
    monkeypatch.setattr(run, "resolve_game_dir", lambda _: tmp_path)
    monkeypatch.setattr(run, "menu_request", lambda *args: {"gamepad": True})
    monkeypatch.setattr(run, "send", lambda *args: True)
    monkeypatch.setattr(run, "wait_for_png", lambda *args: False)
    assert run.main(["menu", "drive", "[]", "--out", str(tmp_path / "missing.png")]) == 1


def test_start_uses_user_service_to_survive_ssh_logout(monkeypatch, tmp_path):
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stderr="")

    monkeypatch.setattr(run.shutil, "which", lambda _: "/usr/bin/systemd-run")
    monkeypatch.setattr(run.subprocess, "run", invoke)
    monkeypatch.setattr(run.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("systemd must own the detached process"))
    monkeypatch.setattr(run, "menu_request", lambda *args: {"pid": 42})
    args = run.parse_args(["menu", "start", "--display", ":9", "--no-gamepad"])
    assert run.start_menu_service(args, tmp_path / "input.sock")
    assert calls[0][:4] == ["systemd-run", "--user", "--collect", "--quiet"]
    assert calls[0][-3:] == ["--display", ":9", "--no-gamepad"]


def test_refused_user_service_is_reported_without_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(run.shutil, "which", lambda _: "/usr/bin/systemd-run")
    monkeypatch.setattr(run.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 1, stderr="No user bus"))
    monkeypatch.setattr(run.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not silently fall back"))
    args = run.parse_args(["menu", "start"])
    with pytest.raises(RuntimeError, match="No user bus"):
        run.start_menu_service(args, tmp_path / "input.sock")


def test_uncertain_user_service_launch_stops_its_named_unit(monkeypatch, tmp_path):
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        if command[0] == "systemd-run":
            raise subprocess.TimeoutExpired(command, 1)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run.shutil, "which", lambda _: "/usr/bin/systemd-run")
    monkeypatch.setattr(run.subprocess, "run", invoke)
    args = run.parse_args(["menu", "start"])
    with pytest.raises(subprocess.TimeoutExpired):
        run.start_menu_service(args, tmp_path / "input.sock")
    unit = next(arg.removeprefix("--unit=") for arg in calls[0] if arg.startswith("--unit="))
    assert calls[1] == ["systemctl", "--user", "stop", unit]


def test_remote_options_never_silently_target_the_local_machine():
    assert run.run_main(["menu", "drive", "[]", "--remote-repo", "/repo"]) == 1
