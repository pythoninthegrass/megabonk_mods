"""
Self-test for scripts/player_installer/ui.py.

Covers choosing between the GUI progress dialog and plain text, which is how
the same script behaves on a desktop session and over ssh.
"""

import player_installer.ui as ui


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


def test_force_text_overrides_a_desktop_session() -> None:
    progress = ui.pick_progress({"DISPLAY": ":0"}, find_binary=_found("zenity"), force_text=True, writer=lambda s: None)
    assert isinstance(progress, ui.TextProgress)


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
