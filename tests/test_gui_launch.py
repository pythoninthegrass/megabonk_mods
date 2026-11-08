import ctypes
import launch_game as lg
import plistlib
import pytest
from pathlib import Path
from types import SimpleNamespace


@pytest.mark.parametrize(("status", "attributes", "expected"), [(0, 0x6030, True), (0, 0x6000, False)])
def test_graphical_session_checks_security_attributes(monkeypatch, status, attributes, expected):
    class Query:
        def __call__(self, caller, session, bits):
            assert caller == 0xFFFFFFFF
            ctypes.cast(bits, ctypes.POINTER(ctypes.c_uint32))[0] = attributes
            return status

    monkeypatch.setattr(lg.ctypes, "CDLL", lambda name: SimpleNamespace(SessionGetInfo=Query()))
    assert lg.has_graphical_session() is expected


def test_failed_session_query_is_not_treated_as_graphical(monkeypatch):
    class Query:
        def __call__(self, *args):
            return -50

    monkeypatch.setattr(lg.ctypes, "CDLL", lambda name: SimpleNamespace(SessionGetInfo=Query()))
    with pytest.raises(RuntimeError, match="SessionGetInfo.*-50"):
        lg.has_graphical_session()


def test_non_graphical_spawn_hands_off_without_spawning_locally(monkeypatch, tmp_path):
    launch = lg.Launch(["/wine", "Megabonk.exe"], {"WINEPREFIX": "/prefix"}, tmp_path)
    seen = []
    monkeypatch.setattr(lg.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(lg, "has_graphical_session", lambda: False)
    monkeypatch.setattr(lg, "spawn_in_gui", lambda target, env: seen.append((target, env)))
    monkeypatch.setattr(lg.subprocess, "Popen", lambda *a, **kw: pytest.fail("headless launch"))
    lg.spawn(launch)
    assert seen[0][0] == launch
    assert seen[0][1]["WINEPREFIX"] == "/prefix"


def test_non_macos_spawn_does_not_query_security_framework(monkeypatch):
    monkeypatch.setattr(lg.platform, "system", lambda: "Linux")
    monkeypatch.setattr(lg, "has_graphical_session", lambda: pytest.fail("macOS API on Linux"))
    seen = []
    monkeypatch.setattr(lg.subprocess, "Popen", lambda *args, **kwargs: seen.append(args))
    lg.spawn(lg.Launch(["wine", "game.exe"], {}, None))
    assert len(seen) == 1


def test_graphical_spawn_keeps_the_direct_launch(monkeypatch):
    monkeypatch.setattr(lg.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(lg, "has_graphical_session", lambda: True)
    monkeypatch.setattr(lg, "spawn_in_gui", lambda *args: pytest.fail("unnecessary GUI handoff"))
    seen = []
    monkeypatch.setattr(lg.subprocess, "Popen", lambda *args, **kwargs: seen.append(args))
    lg.spawn(lg.Launch(["wine", "game.exe"], {}, None))
    assert len(seen) == 1


def launchctl_stubs(monkeypatch, tmp_path, *, gui=True, job=None, bootstrap=0, bootout=0):
    calls = []
    monkeypatch.setattr(lg.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(lg.os, "getuid", lambda: 501)

    def run(argv, **kwargs):
        calls.append(argv)
        assert kwargs["timeout"] == 10
        if argv == ["launchctl", "print", "gui/501"]:
            return SimpleNamespace(returncode=0 if gui else 113, stdout="", stderr="domain unavailable")
        if argv[1] == "print":
            return SimpleNamespace(returncode=0 if job is not None else 113, stdout=job or "", stderr="")
        if argv[1] == "bootout":
            return SimpleNamespace(returncode=bootout, stdout="", stderr="bootout error")
        return SimpleNamespace(returncode=bootstrap, stdout="", stderr="bootstrap error")

    monkeypatch.setattr(lg.subprocess, "run", run)
    return calls


def test_gui_handoff_uses_resolved_watcher_and_private_runtime_environment(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path)
    log = tmp_path / "game" / "MelonLoader" / "wine-latest.log"
    log.parent.mkdir(parents=True)
    log.write_text("previous boot")
    launch = lg.Launch(["/Wine App/wine", "C:\\Game\\Megabonk.exe"], {"WINEPREFIX": "/prefix"}, log.parent.parent, log)
    lg.spawn_in_gui(launch, {"WINEPREFIX": "/prefix", "PATH": "/bin", "MEGABONK_DEV": "true", "SSH_AUTH_SOCK": "/secret", "API_TOKEN": "secret"})
    assert calls[-1][1:3] == ["bootstrap", "gui/501"]
    path = Path(calls[-1][3])
    config = plistlib.loads(path.read_bytes())
    assert config["ProgramArguments"] == lg.watcher_argv(launch)
    assert config["WorkingDirectory"] == str(launch.cwd)
    assert config["EnvironmentVariables"] == {"WINEPREFIX": "/prefix", "PATH": "/bin", "MEGABONK_DEV": "true"}
    assert config["RunAtLoad"] is True
    assert not config.get("KeepAlive")
    assert config["LimitLoadToSessionType"] == "Aqua"
    assert str(log) == config["StandardErrorPath"] == config["StandardOutPath"]
    assert path.stat().st_mode & 0o777 == 0o600
    assert "LaunchAgents" not in path.parts
    assert log.with_name("wine-latest.prev.log").read_text() == "previous boot"


def test_gui_handoff_steam_launch_needs_no_working_directory(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path)
    launch = lg.Launch(["/wine", "steam.exe", "-silent"], {}, None)
    lg.spawn_in_gui(launch, {})
    config = plistlib.loads(Path(calls[-1][3]).read_bytes())
    assert config["ProgramArguments"] == launch.argv
    assert "WorkingDirectory" not in config


def test_gui_handoff_preserves_opt_in_stage_measurement_switch(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path)
    lg.spawn_in_gui(lg.Launch(["/wine", "game.exe"], {}, None), {"MEGABONK_DEV_STAGE_OVERRIDE": "true"})
    config = plistlib.loads(Path(calls[-1][3]).read_bytes())
    assert config["EnvironmentVariables"]["MEGABONK_DEV_STAGE_OVERRIDE"] == "true"


def test_missing_gui_session_fails_without_bootstrap_or_log_rotation(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path, gui=False)
    log = tmp_path / "wine-latest.log"
    log.write_text("evidence")
    with pytest.raises(RuntimeError, match="Log in.*desktop"):
        lg.spawn_in_gui(lg.Launch(["/wine", "game.exe"], {}, None, log), {})
    assert calls == [["launchctl", "print", "gui/501"]]
    assert log.read_text() == "evidence"


def test_stopped_gui_job_is_removed_before_reuse(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path, job="state = not running\nlast exit code = 1\n")
    lg.spawn_in_gui(lg.Launch(["/wine", "game.exe"], {}, None), {})
    assert [argv[1] for argv in calls] == ["print", "print", "bootout", "bootstrap"]


def test_running_gui_job_is_not_removed(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path, job="state = running\n\tpid = 1234\n")
    with pytest.raises(RuntimeError, match="already running"):
        lg.spawn_in_gui(lg.Launch(["/wine", "game.exe"], {}, None), {})
    assert all(argv[1] == "print" for argv in calls)


def test_pending_gui_job_without_pid_is_not_removed(monkeypatch, tmp_path):
    calls = launchctl_stubs(monkeypatch, tmp_path, job="state = spawn scheduled\n")
    with pytest.raises(RuntimeError, match="pending"):
        lg.spawn_in_gui(lg.Launch(["/wine", "game.exe"], {}, None), {})
    assert all(argv[1] == "print" for argv in calls)


@pytest.mark.parametrize("operation", ["bootstrap", "bootout"])
def test_failed_launchctl_operation_is_reported(monkeypatch, tmp_path, operation):
    options = {operation: 5}
    if operation == "bootout":
        options["job"] = "state = not running\n"
    launchctl_stubs(monkeypatch, tmp_path, **options)
    with pytest.raises(RuntimeError, match=f"{operation}.*error"):
        lg.spawn_in_gui(lg.Launch(["/wine", "game.exe"], {}, None), {})


def test_job_identity_is_shared_across_worktrees_but_not_prefixes():
    one = lg.Launch(["/wine", "game.exe"], {"WINEPREFIX": "/one"}, Path("/one/game"))
    two = lg.Launch(["/wine", "game.exe"], {"WINEPREFIX": "/two"}, Path("/two/game"))
    assert lg.gui_job_label(one) == lg.gui_job_label(one)
    assert lg.gui_job_label(one) != lg.gui_job_label(two)


def test_main_reports_handoff_failure_without_traceback(monkeypatch, tmp_path, capsys):
    wine = tmp_path / "wine"
    wine.touch()
    monkeypatch.setattr(lg.gp, "game_dir", lambda: tmp_path)
    monkeypatch.setattr(lg.gp, "wine_bin", lambda: wine)
    monkeypatch.setattr(lg, "prefix_for", lambda game: tmp_path)

    def fail(launch):
        raise RuntimeError("Log in to the desktop first")

    monkeypatch.setattr(lg, "spawn", fail)
    assert lg.main(["game"]) == 1
    assert capsys.readouterr().err == "launch: Log in to the desktop first\n"
