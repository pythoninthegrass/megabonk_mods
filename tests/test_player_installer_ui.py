"""
Self-test for scripts/player_installer/ui.py.

Covers choosing between the GUI progress dialog and plain text, which is how
the same script behaves on a desktop session and over ssh.
"""

import os
import player_installer.ui as ui
import pytest
import subprocess
import sys
from pathlib import Path


@pytest.fixture(autouse=True)
def attached_tty(monkeypatch, request):
    if not request.node.name.startswith("test_tty_detection"):
        monkeypatch.setattr(ui, "has_tty", lambda: True, raising=False)


class FakePopen:
    def __init__(self) -> None:
        self.written: list[str] = []
        self.argv: list[str] = []
        self.terminated = False

    def __call__(self, argv, **kwargs) -> "FakePopen":
        self.argv = list(argv)
        return self

    @property
    def stdin(self) -> "FakePopen":
        return self

    def write(self, text: str) -> None:
        self.written.append(text)

    def flush(self) -> None:
        pass

    def poll(self) -> int | None:
        return None

    def terminate(self) -> None:
        self.terminated = True


def _found(*names: str):
    return lambda name: f"/usr/bin/{name}" if name in names else None


DESKTOP = {"DISPLAY": ":0", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}


class FakeRun:
    def __init__(self, returncode: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.returncode = returncode

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        return type("Done", (), {"returncode": self.returncode})()

    def flat(self) -> str:
        return " ".join(" ".join(call) for call in self.calls)


class KDialogPopen(FakePopen):
    def __call__(self, argv, **kwargs) -> "KDialogPopen":
        self.argv = list(argv)
        return self

    @property
    def stdout(self):
        return type("Out", (), {"readline": lambda self=None: "org.kde.kdialog-4242 /ProgressDialog\n"})()


def test_kdialog_is_chosen_when_kde_has_no_zenity_or_yad() -> None:
    progress = ui.pick_progress(DESKTOP, find_binary=_found("kdialog", "qdbus-qt6"))
    assert isinstance(progress, ui.GuiProgress)
    assert progress.binary.endswith("kdialog")


def test_kdialog_is_skipped_without_a_session_bus() -> None:
    progress = ui.pick_progress({"DISPLAY": ":0"}, find_binary=_found("kdialog", "qdbus-qt6"), writer=lambda s: None)
    assert isinstance(progress, ui.TextProgress)


def test_kdialog_is_skipped_when_no_qdbus_tool_can_reach_it() -> None:
    progress = ui.pick_progress(DESKTOP, find_binary=_found("kdialog"), writer=lambda s: None)
    assert isinstance(progress, ui.TextProgress)


def test_gui_progress_drives_kdialog_over_dbus() -> None:
    popen, run = KDialogPopen(), FakeRun()
    progress = ui.GuiProgress("/usr/bin/kdialog", popen=popen, run=run)
    progress.start(4, "install")
    assert popen.argv[:2] == ["/usr/bin/kdialog", "--title"]
    assert "--progressbar" in popen.argv and "100" in popen.argv
    progress.step("MelonLoader")
    progress.step("runtime")
    progress.finish("done")
    assert "org.kde.kdialog-4242 /ProgressDialog" in run.flat()
    assert run.flat().count("ProgressDialog.value") >= 3
    assert "org.kde.kdialog.ProgressDialog.setLabelText MelonLoader" in run.flat()
    assert "org.kde.kdialog.ProgressDialog.close" in run.flat()
    assert popen.terminated is True


def test_gui_progress_falls_back_to_text_when_dbus_calls_fail() -> None:
    popen, run = KDialogPopen(), FakeRun(returncode=1)
    progress = ui.GuiProgress("/usr/bin/kdialog", popen=popen, run=run)
    lines: list[str] = []
    progress.fallback_writer = lines.append
    progress.start(2, "install")
    progress.step("MelonLoader")
    assert any("MelonLoader" in line for line in lines)


def test_gui_progress_falls_back_to_text_when_kdialog_never_answers() -> None:
    class Silent(FakePopen):
        @property
        def stdout(self):
            return type("Out", (), {"readline": lambda self=None: ""})()

    progress = ui.GuiProgress("/usr/bin/kdialog", popen=Silent(), run=FakeRun())
    lines: list[str] = []
    progress.fallback_writer = lines.append
    progress.start(2, "install")
    progress.step("MelonLoader")
    assert any("MelonLoader" in line for line in lines)


def test_plain_text_when_there_is_no_display_session() -> None:
    progress = ui.pick_progress({}, find_binary=_found("zenity"), writer=lambda s: None)
    assert isinstance(progress, ui.TextProgress)


def test_plain_text_over_ssh_without_a_wayland_display() -> None:
    env = {"SSH_CONNECTION": "10.0.0.1 5000 10.0.0.2 22", "DISPLAY": "", "WAYLAND_DISPLAY": ""}
    assert isinstance(ui.pick_progress(env, find_binary=_found("zenity"), writer=lambda s: None), ui.TextProgress)


def test_gui_when_x11_is_available_and_zenity_is_installed() -> None:
    progress = ui.pick_progress({"DISPLAY": ":0"}, find_binary=_found("zenity"))
    assert isinstance(progress, ui.GuiProgress)


def test_gui_when_only_wayland_is_available() -> None:
    progress = ui.pick_progress({"WAYLAND_DISPLAY": "wayland-0"}, find_binary=_found("zenity"))
    assert isinstance(progress, ui.GuiProgress)


def test_plain_text_when_no_dialog_binary_exists() -> None:
    progress = ui.pick_progress({"DISPLAY": ":0"}, find_binary=_found(), writer=lambda s: None)
    assert isinstance(progress, ui.TextProgress)


def test_no_skip_note_when_there_is_no_display_session() -> None:
    assert ui.dialog_skip_note({}, find_binary=_found()) is None


def test_no_skip_note_when_the_run_has_no_controlling_tty(monkeypatch) -> None:
    monkeypatch.setattr(ui, "has_tty", lambda: False)
    assert ui.dialog_skip_note({"DISPLAY": ":0"}, find_binary=_found()) is None


def test_no_skip_note_when_a_backend_exists() -> None:
    assert ui.dialog_skip_note({"DISPLAY": ":0"}, find_binary=_found("zenity")) is None


def test_skip_note_names_a_missing_backend_and_how_to_install_one() -> None:
    note = ui.dialog_skip_note({"DISPLAY": ":0"}, find_binary=_found())
    assert note is not None
    assert "zenity" in note and "--no-gui" in note and "sudo" in note


def test_force_text_overrides_a_desktop_session() -> None:
    progress = ui.pick_progress({"DISPLAY": ":0"}, find_binary=_found("zenity"), force_text=True, writer=lambda s: None)
    assert isinstance(progress, ui.TextProgress)


def test_display_without_controlling_tty_is_headless(monkeypatch) -> None:
    monkeypatch.setattr(ui, "has_tty", lambda: False)
    assert isinstance(ui.pick_progress(DESKTOP, find_binary=_found("zenity")), ui.TextProgress)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_non_interactive_environment_forces_text(value) -> None:
    env = {**DESKTOP, "MEGABONK_NON_INTERACTIVE": value}
    assert isinstance(ui.pick_progress(env, find_binary=_found("zenity")), ui.TextProgress)


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_false_non_interactive_environment_preserves_desktop(value) -> None:
    env = {**DESKTOP, "MEGABONK_NON_INTERACTIVE": value}
    assert isinstance(ui.pick_progress(env, find_binary=_found("zenity")), ui.GuiProgress)


def test_tty_detection_uses_dev_tty_without_reading_stdin(monkeypatch) -> None:
    import builtins

    calls = []
    monkeypatch.setattr(os, "open", lambda path, flags: calls.append(path) or 42)
    monkeypatch.setattr(os, "isatty", lambda fd: fd == 42)
    monkeypatch.setattr(os, "close", lambda fd: calls.append(fd))
    monkeypatch.setattr(builtins, "input", lambda *args: pytest.fail("read stdin"))
    assert ui.has_tty() is True
    assert calls == ["/dev/tty", 42]


def test_tty_detection_handles_an_unavailable_terminal(monkeypatch) -> None:
    def unavailable(*args):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(os, "open", unavailable)
    assert ui.has_tty() is False


def test_tty_detection_closes_a_non_terminal_descriptor(monkeypatch) -> None:
    closed = []
    monkeypatch.setattr(os, "open", lambda *args: 42)
    monkeypatch.setattr(os, "isatty", lambda fd: False)
    monkeypatch.setattr(os, "close", closed.append)
    assert ui.has_tty() is False
    assert closed == [42]


def test_piped_stdin_with_and_without_a_controlling_tty() -> None:
    import fcntl
    import pty
    import termios

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    code = (
        "import sys; from player_installer import ui; "
        "p = ui.pick_progress({'DISPLAY': ':0'}, find_binary=lambda name: '/usr/bin/zenity'); "
        "print(type(p).__name__); print(sys.stdin.read())"
    )
    env = {**os.environ, "PYTHONPATH": str(scripts)}
    result = subprocess.run([sys.executable, "-c", code], input="untouched", capture_output=True, text=True, env=env, start_new_session=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["TextProgress", "untouched"]

    master, slave = pty.openpty()
    try:
        def attach_tty():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        result = subprocess.run(
            [sys.executable, "-c", code], input="untouched", capture_output=True, text=True,
            env=env, pass_fds=(slave,), preexec_fn=attach_tty, timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == ["GuiProgress", "untouched"]
    finally:
        os.close(master)
        os.close(slave)


def test_yad_is_accepted_when_zenity_is_absent() -> None:
    progress = ui.pick_progress({"DISPLAY": ":0"}, find_binary=_found("yad"))
    assert isinstance(progress, ui.GuiProgress)
    assert progress.binary.endswith("yad")


def test_text_progress_numbers_the_steps() -> None:
    lines: list[str] = []
    progress = ui.TextProgress(writer=lines.append)
    progress.start(3, "install")
    progress.step("MelonLoader")
    progress.step("mod DLL")
    progress.finish("done")
    assert "MelonLoader" in lines[0] and "1/3" in lines[0]
    assert "2/3" in lines[1]
    assert "done" in lines[2]


def test_gui_progress_drives_the_dialog_over_stdin() -> None:
    popen = FakePopen()
    progress = ui.GuiProgress("/usr/bin/zenity", popen=popen)
    progress.start(4, "install")
    progress.step("MelonLoader")
    progress.step("runtime")
    progress.finish("done")
    assert "--progress" in popen.argv
    assert popen.written[:2] == ["25\n", "# MelonLoader\n"]
    assert popen.written[-2:] == ["100\n", "# done\n"]
    assert popen.terminated is True


def test_gui_progress_stays_usable_if_the_dialog_dies() -> None:
    class Dead(FakePopen):
        def poll(self) -> int | None:
            return 1

    progress = ui.GuiProgress("/usr/bin/zenity", popen=Dead())
    lines: list[str] = []
    progress.fallback_writer = lines.append
    progress.start(2, "install")
    progress.step("x")
    assert any("x" in line for line in lines)
