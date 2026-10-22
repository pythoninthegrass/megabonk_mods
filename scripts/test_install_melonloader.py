#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""
Self-test for scripts/install_melonloader.py.

Covers idempotency checking and checksum verification without touching the
network or a real game install.

Usage: uv run scripts/test_install_melonloader.py
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import install_melonloader as im


def test_is_installed_false_when_no_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp)
        assert im.is_installed("0.7.3", game) is False


def test_is_installed_true_when_marker_matches() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp)
        (game / "MelonLoader").mkdir()
        im._version_marker_path(game).write_text("0.7.3")
        assert im.is_installed("0.7.3", game) is True


def test_is_installed_false_when_marker_is_different_version() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp)
        (game / "MelonLoader").mkdir()
        im._version_marker_path(game).write_text("0.6.0")
        assert im.is_installed("0.7.3", game) is False


def test_verify_sha256_passes_on_match() -> None:
    data = b"hello world"
    import hashlib

    digest = hashlib.sha256(data).hexdigest()
    im._verify_sha256(data, digest)  # should not raise


def test_verify_sha256_raises_on_mismatch() -> None:
    try:
        im._verify_sha256(b"hello world", "deadbeef")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on checksum mismatch")


def test_lookup_bottle_name_finds_drive_c_parent_dirname() -> None:
    game = Path("/tmp/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    assert im._lookup_bottle_name(game) == "Steam"


def test_lookup_bottle_name_none_when_absent() -> None:
    game = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk")
    assert im._lookup_bottle_name(game) is None


REG_ADD_TAIL = ["reg", "add", r"HKCU\Software\Wine\DllOverrides", "/v", "version", "/d", "native,builtin", "/f"]


def test_crossover_override_command_selects_bottle_by_name() -> None:
    argv = im._crossover_override_command(Path("/cx/wine"), "Steam")
    assert argv == ["/cx/wine", "--bottle", "Steam", *REG_ADD_TAIL]


def test_wine_override_command_uses_prefix_and_crossover_user() -> None:
    argv, env = im._wine_override_command(Path("/w/wine"), Path("/b/Steam"))
    assert argv == ["/w/wine", *REG_ADD_TAIL]
    assert env == {"WINEPREFIX": "/b/Steam", "USER": "crossover", "LOGNAME": "crossover", "WINEDEBUG": "-all"}


def test_apply_dll_override_runs_plain_wine_for_the_wine_runtime() -> None:
    game = Path("/b/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    calls = []
    original = im.subprocess.run
    im.subprocess.run = lambda argv, **kw: calls.append((argv, kw))
    with tempfile.TemporaryDirectory() as tmp:
        fake_wine = Path(tmp) / "wine"
        fake_wine.touch()
        os.environ["MEGABONK_WINE"] = str(fake_wine)
        try:
            im.apply_dll_override("wine", game)
        finally:
            im.subprocess.run = original
            del os.environ["MEGABONK_WINE"]
    ((argv, kw),) = calls
    assert argv == [str(fake_wine), *REG_ADD_TAIL]
    assert kw["env"]["WINEPREFIX"] == "/b/Steam" and kw["check"] is True


def test_apply_dll_override_runs_crossover_wine_for_the_crossover_runtime() -> None:
    game = Path("/b/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk")
    calls = []
    original = im.subprocess.run
    im.subprocess.run = lambda argv, **kw: calls.append((argv, kw))
    os.environ["CROSSOVER_WINE_BIN"] = "/cx/wine"
    try:
        im.apply_dll_override("crossover", game)
    finally:
        im.subprocess.run = original
        del os.environ["CROSSOVER_WINE_BIN"]
    ((argv, kw),) = calls
    assert argv == ["/cx/wine", "--bottle", "Steam", *REG_ADD_TAIL]


def test_release_asset_linux_uses_linux_zip_and_sha() -> None:
    url, sha = im.release_asset("Linux", "0.7.3")
    assert url.endswith("/v0.7.3/MelonLoader.Linux.x64.zip")
    assert sha == im.DEFAULT_SHA256_LINUX


def test_release_asset_darwin_and_windows_use_windows_zip_and_sha() -> None:
    for system in ("Darwin", "Windows"):
        url, sha = im.release_asset(system, "0.7.3")
        assert url.endswith("/v0.7.3/MelonLoader.x64.zip")
        assert sha == im.DEFAULT_SHA256_WINDOWS


def test_release_asset_sha_overridable_via_env() -> None:
    os.environ["MELONLOADER_SHA256_LINUX"] = "cafe"
    try:
        assert im.release_asset("Linux", "0.7.3")[1] == "cafe"
    finally:
        del os.environ["MELONLOADER_SHA256_LINUX"]


def test_release_asset_url_overridable_via_env() -> None:
    os.environ["MELONLOADER_URL_LINUX"] = "https://example.invalid/ml.zip"
    try:
        assert im.release_asset("Linux", "0.7.3")[0] == "https://example.invalid/ml.zip"
    finally:
        del os.environ["MELONLOADER_URL_LINUX"]


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
