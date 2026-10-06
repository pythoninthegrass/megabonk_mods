#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""
Self-test for tools/install_melonloader.py.

Covers idempotency checking and checksum verification without touching the
network or a real game install.

Usage: uv run tools/test_install_melonloader.py
"""

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


def main() -> int:
    tests = [
        (n, f)
        for n, f in sorted(globals().items())
        if n.startswith("test_") and callable(f)
    ]
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
