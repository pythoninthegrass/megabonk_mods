"""Progress reporting that works the same over ssh and on a desktop session.

A desktop session gets a zenity/yad progress dialog driven over its stdin; anything else
(ssh, a console, no dialog binary installed) gets numbered lines on stdout. Everything the
installer reports also goes through plain text, so nothing depends on the dialog.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from typing import IO

DIALOG_BINARIES = ("zenity", "yad")
DIALOG_ARGS = {
    "zenity": ("--progress", "--percentage=0", "--auto-kill", "--time-remaining"),
    "yad": ("--progress", "--percentage=0", "--no-cancel", "--permanent"),
}


class Progress:
    def start(self, total: int, label: str) -> None:
        pass

    def step(self, label: str) -> None:
        pass

    def finish(self, message: str, ok: bool = True) -> None:
        pass


class TextProgress(Progress):
    def __init__(self, writer: Callable[[str], None] | None = None) -> None:
        self.writer = writer or (lambda line: print(line, flush=True))
        self.total = 0
        self.done = 0

    def start(self, total: int, label: str) -> None:
        self.total = max(int(total), 1)
        self.done = 0

    def step(self, label: str) -> None:
        self.done += 1
        self.writer(f"{self.done}/{self.total} {label}")

    def finish(self, message: str, ok: bool = True) -> None:
        self.writer(message)


class GuiProgress(Progress):
    def __init__(self, binary: str | None = None, popen=None, title: str = "MegabonkLevels") -> None:
        self.binary = str(binary or DIALOG_BINARIES[0])
        self.popen = popen or subprocess.Popen
        self.title = title
        self.process: IO | None = None
        self.total = 0
        self.done = 0
        self.fallback_writer: Callable[[str], None] | None = None

    def _argv(self, label: str) -> list[str]:
        name = self.binary.rsplit("/", 1)[-1]
        flavour = DIALOG_ARGS.get(name, DIALOG_ARGS["zenity"])
        caption = f"# {label}" if name == "zenity" else label
        return [self.binary, *flavour, f"--text={caption}", f"--title={self.title}"]

    def start(self, total: int, label: str) -> None:
        self.total = max(int(total), 1)
        self.done = 0
        try:
            self.process = self.popen(self._argv(label), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        except OSError:
            self.process = None

    def step(self, label: str) -> None:
        self.done += 1
        self._write(f"{self._percentage()}")
        self._write(f"# {label}")

    def finish(self, message: str, ok: bool = True) -> None:
        self._write("100")
        self._write(f"# {message}")
        if self.process is not None:
            try:
                self.process.terminate()
            except OSError:
                pass
            self.process = None

    def _percentage(self) -> int:
        return min(100, max(0, int(100 * self.done / self.total)))

    def _write(self, line: str) -> None:
        if self._dialog_alive():
            try:
                self.process.write(line + "\n")
                self.process.flush()
                return
            except (OSError, ValueError):
                self.process = None
        if self.fallback_writer:
            self.fallback_writer(line)

    def _dialog_alive(self) -> bool:
        if self.process is None:
            return False
        try:
            return self.process.poll() is None
        except (OSError, ValueError):
            self.process = None
            return False


def has_display(env: dict) -> bool:
    if env.get("SSH_TTY") or env.get("SSH_CONNECTION"):
        return bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))
    return bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))


def find_dialog_binary(find_binary: Callable[[str], str | None] | None = None) -> str | None:
    locate = find_binary or shutil.which
    for name in DIALOG_BINARIES:
        found = locate(name)
        if found:
            return found
    return None


def pick_progress(
    env: dict | None = None,
    *,
    find_binary: Callable[[str], str | None] | None = None,
    writer: Callable[[str], None] | None = None,
    force_text: bool = False,
    title: str = "MegabonkLevels",
) -> Progress:
    """A dialog when this is a desktop session with a dialog tool, plain text otherwise."""
    env = dict(env if env is not None else {})
    if not force_text and has_display(env):
        binary = find_dialog_binary(find_binary)
        if binary:
            return GuiProgress(binary, title=title)
    return TextProgress(writer=writer)
