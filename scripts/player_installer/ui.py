"""Progress reporting that works the same over ssh and on a desktop session.

A desktop session gets a progress dialog: zenity or yad driven over stdin, or KDE's
kdialog driven over D-Bus. Anything else (ssh, a console, no dialog installed) gets
numbered lines on stdout. Everything the installer reports also goes through plain
text, so nothing depends on the dialog.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from typing import IO

DIALOG_BINARIES = ("zenity", "yad", "kdialog")
DIALOG_ARGS = {
    "zenity": ("--progress", "--percentage=0", "--auto-kill", "--time-remaining"),
    "yad": ("--progress", "--percentage=0", "--no-cancel", "--permanent"),
    "kdialog": ("--progressbar",),
}
QDBUS_BINARIES = ("qdbus-qt6", "qdbus")
KDE_PROGRESS = "org.kde.kdialog.ProgressDialog"


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
    def __init__(
        self,
        binary: str | None = None,
        popen=None,
        title: str = "MegabonkLevels",
        run=None,
        qdbus: str | None = None,
    ) -> None:
        self.binary = str(binary or DIALOG_BINARIES[0])
        self.name = self.binary.rsplit("/", 1)[-1]
        self.popen = popen or subprocess.Popen
        self.run = run or subprocess.run
        self.qdbus = str(qdbus or QDBUS_BINARIES[0])
        self.title = title
        self.process: IO | None = None
        self.reference: tuple[str, str] | None = None
        self.total = 0
        self.done = 0
        self.fallback_writer: Callable[[str], None] | None = None

    @property
    def uses_dbus(self) -> bool:
        return self.name == "kdialog"

    def _argv(self, label: str) -> list[str]:
        if self.uses_dbus:
            return [self.binary, "--title", self.title, "--progressbar", label, "100"]
        caption = f"# {label}" if self.name == "zenity" else label
        return [self.binary, *DIALOG_ARGS.get(self.name, DIALOG_ARGS["zenity"]), f"--text={caption}", f"--title={self.title}"]

    def start(self, total: int, label: str) -> None:
        self.total = max(int(total), 1)
        self.done = 0
        self.reference = None
        try:
            if self.uses_dbus:
                self.process = self.popen(self._argv(label), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                self.reference = self._read_reference()
                if self.reference is None:
                    self._close()
            else:
                self.process = self.popen(self._argv(label), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        except OSError:
            self.process = None

    def step(self, label: str) -> None:
        self.done += 1
        if self.uses_dbus:
            if self._dbus("value", str(self._percentage())) and self._dbus("setLabelText", label):
                return
            self._close()
            if self.fallback_writer:
                self.fallback_writer(label)
            return
        self._write(f"{self._percentage()}")
        self._write(f"# {label}")

    def finish(self, message: str, ok: bool = True) -> None:
        if self.uses_dbus:
            reported = self._dbus("value", "100") and self._dbus("setLabelText", message) and self._dbus("close")
            self._close()
            if not reported and self.fallback_writer:
                self.fallback_writer(message)
            return
        self._write("100")
        self._write(f"# {message}")
        self._close()

    def _percentage(self) -> int:
        return min(100, max(0, int(100 * self.done / self.total)))

    def _read_reference(self) -> tuple[str, str] | None:
        stream = getattr(self.process, "stdout", None)
        if stream is None:
            return None
        try:
            tokens = str(stream.readline()).split()
        except (OSError, ValueError):
            return None
        return (tokens[0], tokens[1]) if len(tokens) >= 2 else None

    def _dbus(self, method: str, *arguments: str) -> bool:
        if self.process is None or self.reference is None:
            return False
        service, path = self.reference
        try:
            completed = self.run(
                [self.qdbus, service, path, f"{KDE_PROGRESS}.{method}", *arguments],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return False
        return getattr(completed, "returncode", 1) == 0

    def _close(self) -> None:
        if self.process is not None:
            try:
                self.process.terminate()
            except OSError:
                pass
        self.process = None
        self.reference = None

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


def _kdialog_usable(locate: Callable[[str], str | None], env: dict) -> bool:
    return bool(env.get("DBUS_SESSION_BUS_ADDRESS")) and any(locate(tool) for tool in QDBUS_BINARIES)


def find_dialog_binary(find_binary: Callable[[str], str | None] | None = None, env: dict | None = None) -> str | None:
    locate = find_binary or shutil.which
    environ = dict(env if env is not None else os.environ)
    for name in DIALOG_BINARIES:
        found = locate(name)
        if not found:
            continue
        if name == "kdialog" and not _kdialog_usable(locate, environ):
            continue
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
        binary = find_dialog_binary(find_binary, env=env)
        if binary:
            locate = find_binary or shutil.which
            return GuiProgress(binary, title=title, qdbus=locate(QDBUS_BINARIES[0]) or locate(QDBUS_BINARIES[1]))
    return TextProgress(writer=writer)
