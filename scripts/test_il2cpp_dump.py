#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Self-test for scripts/il2cpp_dump.py.

Covers path derivation and command construction without invoking dotnet or
touching a real game install.

Usage: uv run scripts/test_il2cpp_dump.py
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import il2cpp_dump as dump


def test_game_assembly_path() -> None:
    game = Path("/tmp/Megabonk")
    assert dump.game_assembly_path(game) == game / "GameAssembly.dll"


def test_global_metadata_path() -> None:
    game = Path("/tmp/Megabonk")
    expected = game / "Megabonk_Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    assert dump.global_metadata_path(game) == expected


def test_build_command() -> None:
    cmd = dump.build_command(
        Path("/tmp/GameAssembly.dll"),
        Path("/tmp/global-metadata.dat"),
        Path("/tmp/out"),
        Path("/tmp/Il2CppDumper.dll"),
    )
    assert cmd == [
        "mise",
        "exec",
        "dotnet@10.0.108",
        "--",
        "dotnet",
        "/tmp/Il2CppDumper.dll",
        "/tmp/GameAssembly.dll",
        "/tmp/global-metadata.dat",
        "/tmp/out",
    ]


def test_run_dump_raises_when_dumper_missing() -> None:
    try:
        dump.run_dump(game=Path("/tmp/nonexistent_game"), dumper_dll=Path("/tmp/nonexistent_dumper.dll"))
    except FileNotFoundError as e:
        assert "Il2CppDumper.dll" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError when dumper is missing")


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
