"""Linux device input for stock Rewired menus, separate from editor input injection."""

import ctypes
import importlib
import json
import os
import socket
import time
from contextlib import ExitStack
from pathlib import Path

KEYS = ("KEY_ENTER", "KEY_ESC", "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_TAB", "KEY_SPACE", "KEY_F12")
BUTTONS = ("BTN_SOUTH", "BTN_EAST", "BTN_NORTH", "BTN_WEST", "BTN_START", "BTN_SELECT", "BTN_TL", "BTN_TR", "BTN_THUMBL", "BTN_THUMBR")
AXES = {
    "ABS_X": (-32768, 32767), "ABS_Y": (-32768, 32767),
    "ABS_RX": (-32768, 32767), "ABS_RY": (-32768, 32767),
    "ABS_HAT0X": (-1, 1), "ABS_HAT0Y": (-1, 1), "ABS_Z": (0, 255), "ABS_RZ": (0, 255),
}
MAX_MESSAGE = 65536


def validate_batch(commands: object) -> list:
    if not isinstance(commands, list) or len(commands) > 256:
        raise ValueError("menu: expected a JSON array of at most 256 commands")
    for command in commands:
        if isinstance(command, dict):
            kind = command.get("command")
            if kind in ("state", "steam-ready") and set(command) == {"command"}:
                continue
            if (kind == "query-objects" and set(command) <= {"command", "type", "fields"}
                    and isinstance(command.get("type"), str) and command["type"].strip()
                    and isinstance(command.get("fields", []), list)
                    and all(isinstance(field, str) and field for field in command.get("fields", []))):
                continue
            raise ValueError("menu: diagnostic must be state, steam-ready or query-objects with a type and fields array")
        if not isinstance(command, list) or not command:
            raise ValueError("menu: expected an input command array")
        match command:
            case ["key", str(name)] if name in KEYS:
                pass
            case ["pad", str(name)] if name in BUTTONS:
                pass
            case ["axis", str(name), value] if name in AXES and type(value) is int and AXES[name][0] <= value <= AXES[name][1]:
                pass
            case ["move", x, y] if type(x) is int and type(y) is int and x >= 0 and y >= 0:
                pass
            case ["click"]:
                pass
            case _:
                raise ValueError(f"menu: unknown or invalid input command {command!r}")
    if len(json.dumps(commands).encode()) > MAX_MESSAGE - 1:
        raise ValueError("menu: command batch exceeds 64 KiB")
    return commands


def move_pointer(display: str | None, x: int, y: int) -> None:
    if not display:
        raise RuntimeError("menu: mouse move needs --display or DISPLAY from the game's graphical session")
    try:
        lib = ctypes.CDLL("libX11.so.6")
    except OSError as error:
        raise RuntimeError("menu: mouse positioning requires libX11.so.6 on the Linux target") from error
    lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    lib.XOpenDisplay.restype = ctypes.c_void_p
    lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    lib.XDefaultRootWindow.restype = ctypes.c_ulong
    lib.XDisplayWidth.argtypes = lib.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.XWarpPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_int]
    lib.XFlush.argtypes = lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    connection = lib.XOpenDisplay(display.encode())
    if not connection:
        raise RuntimeError(f"menu: cannot open X11 display {display!r}; check the game's DISPLAY and XAUTHORITY")
    try:
        width, height = lib.XDisplayWidth(connection, 0), lib.XDisplayHeight(connection, 0)
        if x >= width or y >= height:
            raise ValueError(f"menu: pointer ({x}, {y}) outside X11 display ({width} x {height})")
        lib.XWarpPointer(connection, 0, lib.XDefaultRootWindow(connection), 0, 0, 0, 0, x, y)
        lib.XFlush(connection)
    finally:
        lib.XCloseDisplay(connection)


class InputDevices:
    def __init__(self, display=None, gamepad=True, *, evdev=None, sleep=time.sleep, pointer=move_pointer):
        self.display, self.gamepad = display, gamepad
        self.sleep, self.pointer = sleep, pointer
        self.resources = ExitStack()
        try:
            evdev = evdev or importlib.import_module("evdev")
            self.codes = evdev.ecodes
            e = self.codes

            def create(capabilities, **kwargs):
                device = evdev.UInput(capabilities, **kwargs)
                self.resources.callback(device.close)
                return device

            self.keyboard = create({e.EV_KEY: [getattr(e, name) for name in KEYS]}, name="Megabonk menu keyboard")
            self.mouse = create({e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT], e.EV_REL: [e.REL_X, e.REL_Y]}, name="Megabonk menu mouse")
            self.pad = None
            if gamepad:
                axes = [(getattr(e, name), evdev.AbsInfo(0, low, high, 16 if low == -32768 else 0,
                                                        128 if low == -32768 else 0, 0)) for name, (low, high) in AXES.items()]
                self.pad = create({e.EV_KEY: [getattr(e, name) for name in BUTTONS], e.EV_ABS: axes},
                                  name="Microsoft X-Box 360 pad", vendor=0x045e, product=0x028e, version=0x0114)
        except (ImportError, OSError) as error:
            self.close()
            raise RuntimeError(f"menu: cannot create uinput devices: {error}; install Linux evdev and grant this user /dev/uinput access") from error
        except BaseException:
            self.close()
            raise

    def perform(self, command):
        validate_batch([command])
        kind = command[0]
        if kind == "move":
            self.pointer(self.display, command[1], command[2])
            # Rewired needs real device motion to switch from controller to mouse input.
            self.mouse.write(self.codes.EV_REL, self.codes.REL_X, 1)
            self.mouse.syn()
            self.sleep(0.05)
            self.pointer(self.display, command[1], command[2])
            return
        if kind in ("pad", "axis") and self.pad is None:
            raise ValueError("menu: gamepad is disabled; stop and start without --no-gamepad")
        e = self.codes
        device = {"key": self.keyboard, "click": self.mouse, "pad": self.pad, "axis": self.pad}[kind]
        code = e.BTN_LEFT if kind == "click" else getattr(e, command[1])
        event = e.EV_ABS if kind == "axis" else e.EV_KEY
        value = command[2] if kind == "axis" else 1
        try:
            device.write(event, code, value)
            device.syn()
            self.sleep(0.12)
        finally:
            device.write(event, code, 0)
            device.syn()

    def close(self):
        self.resources.close()


def read_message(connection: socket.socket) -> object:
    data = bytearray()
    while b"\n" not in data:
        block = connection.recv(min(4096, MAX_MESSAGE - len(data)))
        if not block:
            raise ValueError("menu: incomplete socket message")
        data.extend(block)
        if len(data) >= MAX_MESSAGE:
            raise ValueError("menu: socket message exceeds 64 KiB")
    return json.loads(data.partition(b"\n")[0])


def request(path: Path, command: object, timeout: float) -> dict:
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(timeout)
        try:
            connection.connect(str(path))
            connection.sendall(json.dumps(command).encode() + b"\n")
            reply = read_message(connection)
        except OSError as error:
            raise RuntimeError(f"menu: input service unavailable at {path}: {error}; run 'run.py menu start' on the target") from error
    if not isinstance(reply, dict) or reply.get("ok") is not True:
        raise RuntimeError(f"menu: {reply.get('error') if isinstance(reply, dict) else 'invalid service reply'}")
    return reply.get("result", {})


def serve(path: Path, display=None, gamepad=True, *, factory=InputDevices, on_ready=lambda: None):
    if path.exists():
        raise RuntimeError(f"menu: socket already exists at {path}; stop its service first (do not remove a live socket)")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    bound = False
    try:
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(path))
            bound = True
            os.chmod(path, 0o600)
            devices = factory(display=display, gamepad=gamepad)
            try:
                server.listen(4)
                on_ready()
                stopping = False
                while not stopping:
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(2)
                        try:
                            command = read_message(connection)
                            if command in ({"command": "status"}, {"command": "stop"}):
                                stopping = command["command"] == "stop"
                            elif isinstance(command, list):
                                devices.perform(command)
                            else:
                                raise ValueError("unknown service command")
                            reply = {"ok": True, "result": {"pid": os.getpid(), "gamepad": gamepad, "display": display}}
                        except (OSError, ValueError, RuntimeError) as error:
                            reply = {"ok": False, "error": str(error)}
                        try:
                            connection.sendall(json.dumps(reply).encode() + b"\n")
                        except OSError:
                            pass
            finally:
                devices.close()
    finally:
        if bound:
            path.unlink(missing_ok=True)
