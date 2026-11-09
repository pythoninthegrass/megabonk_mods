import json
import pytest
import socket
import tempfile
import threading
from megabonk_harness import menu_input
from pathlib import Path
from types import SimpleNamespace


@pytest.mark.parametrize("command", [
    ["key", "KEY_ENTER"], ["key", "KEY_F12"], ["pad", "BTN_SOUTH"], ["axis", "ABS_HAT0Y", -1],
    ["axis", "ABS_X", 32767], ["axis", "ABS_Z", 255], ["move", 0, 1080], ["click"],
    {"command": "query-objects", "type": "MapSelectionUi", "fields": ["runConfig"]},
    {"command": "state"},
])
def test_valid_menu_commands(command):
    assert menu_input.validate_batch([command]) == [command]


@pytest.mark.parametrize("batch", [
    {}, "[]", [None], [["unknown"]], [["click", "extra"]], [["key", "KEY_UNKNOWN"]],
    [["pad", "KEY_ENTER"]], [["axis", "ABS_Z", -1]], [["axis", "ABS_X", 32768]],
    [["axis", "ABS_HAT0X", 2]], [["axis", "ABS_X", True]], [["move", -1, 2]],
    [["move", 1.5, 2]], [["move", True, 2]], [{"command": "load-level", "path": "x"}],
    [{"command": "query-objects", "type": "Foo", "fields": "name"}],
    [{"command": "state", "unexpected": True}], [["click"]] * 257,
])
def test_invalid_menu_batches_fail_before_input(batch):
    with pytest.raises(ValueError):
        menu_input.validate_batch(batch)


class FakeDevice:
    def __init__(self):
        self.events = []
        self.closed = False

    def write(self, kind, code, value):
        self.events.append((kind, code, value))

    def syn(self):
        self.events.append("syn")

    def close(self):
        self.closed = True


def fake_evdev(fail_after=None):
    names = ["EV_KEY", "EV_REL", "EV_ABS", "REL_X", "REL_Y", *menu_input.KEYS, *menu_input.BUTTONS, *menu_input.AXES, "BTN_LEFT", "BTN_RIGHT"]
    codes = dict(enumerate(dict.fromkeys(names)))
    codes = {name: code for code, name in codes.items()}
    devices = []

    def create(*args, **kwargs):
        if fail_after is not None and len(devices) == fail_after:
            raise PermissionError("uinput")
        device = FakeDevice()
        devices.append(device)
        return device

    return SimpleNamespace(UInput=create, AbsInfo=lambda *args: args, ecodes=SimpleNamespace(**codes)), devices


def test_taps_release_even_when_sleep_is_interrupted():
    evdev, created = fake_evdev()

    def interrupt(_):
        raise KeyboardInterrupt

    devices = menu_input.InputDevices(evdev=evdev, sleep=interrupt)
    with pytest.raises(KeyboardInterrupt):
        devices.perform(["pad", "BTN_SOUTH"])
    assert created[2].events == [
        (evdev.ecodes.EV_KEY, evdev.ecodes.BTN_SOUTH, 1), "syn",
        (evdev.ecodes.EV_KEY, evdev.ecodes.BTN_SOUTH, 0), "syn",
    ]
    devices.close()
    assert all(device.closed for device in created)


def test_partial_device_creation_is_cleaned_up():
    evdev, created = fake_evdev(fail_after=1)
    with pytest.raises(RuntimeError, match="uinput"):
        menu_input.InputDevices(evdev=evdev)
    assert all(device.closed for device in created)


def test_mouse_only_service_rejects_pad_and_warps_absolute_pointer():
    evdev, created = fake_evdev()
    moves = []
    devices = menu_input.InputDevices(evdev=evdev, gamepad=False, pointer=lambda *args: moves.append(args), display=":9")
    devices.perform(["move", 20, 30])
    assert moves == [(":9", 20, 30), (":9", 20, 30)]
    assert created[1].events == [(evdev.ecodes.EV_REL, evdev.ecodes.REL_X, 1), "syn"]
    with pytest.raises(ValueError, match="gamepad"):
        devices.perform(["pad", "BTN_SOUTH"])
    devices.close()
    assert len(created) == 2


@pytest.fixture
def short_socket():
    with tempfile.TemporaryDirectory(prefix="mi-") as directory:
        yield Path(directory) / "input.sock"


def test_socket_service_status_input_errors_and_stop_cleanup(short_socket):
    path = short_socket
    evdev, created = fake_evdev()
    ready = threading.Event()

    def factory(**kwargs):
        return menu_input.InputDevices(evdev=evdev, sleep=lambda _: None, **kwargs)

    worker = threading.Thread(target=menu_input.serve, args=(path,), kwargs={"factory": factory, "on_ready": ready.set})
    worker.start()
    try:
        assert ready.wait(3)
        assert path.stat().st_mode & 0o777 == 0o600
        assert menu_input.request(path, {"command": "status"}, 1)["gamepad"] is True
        with socket.socket(socket.AF_UNIX) as connection:
            connection.connect(str(path))
            connection.sendall(b'not-json\n')
            assert json.loads(connection.recv(4096))["ok"] is False
        menu_input.request(path, ["key", "KEY_ENTER"], 1)
        with pytest.raises(RuntimeError, match="unknown"):
            menu_input.request(path, ["unknown"], 1)
        menu_input.request(path, {"command": "stop"}, 1)
        worker.join(3)
        assert not worker.is_alive()
        assert not path.exists()
        assert all(device.closed for device in created)
    finally:
        if worker.is_alive():
            menu_input.request(path, {"command": "stop"}, 1)
            worker.join(3)


def test_existing_socket_is_not_replaced(tmp_path):
    path = tmp_path / "input.sock"
    path.write_text("not ours")
    with pytest.raises((OSError, RuntimeError)):
        menu_input.serve(path, factory=lambda **kwargs: None)
    assert path.read_text() == "not ours"


def test_axis_pulse_returns_to_neutral():
    evdev, created = fake_evdev()
    devices = menu_input.InputDevices(evdev=evdev, sleep=lambda _: None)
    devices.perform(["axis", "ABS_HAT0Y", -1])
    assert created[2].events == [
        (evdev.ecodes.EV_ABS, evdev.ecodes.ABS_HAT0Y, -1), "syn",
        (evdev.ecodes.EV_ABS, evdev.ecodes.ABS_HAT0Y, 0), "syn",
    ]
    devices.close()


def test_disconnected_service_error_is_actionable(short_socket):
    with pytest.raises(RuntimeError, match="menu start"):
        menu_input.request(short_socket, {"command": "status"}, 0.1)
