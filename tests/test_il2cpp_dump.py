"""
Self-test for scripts/il2cpp_dump.py.

Covers path derivation and command construction without invoking dotnet or
touching a real game install.
"""

import il2cpp_dump as dump
from pathlib import Path


def test_game_assembly_path() -> None:
    game = Path("/tmp/Megabonk")
    assert dump.game_assembly_path(game) == game / "GameAssembly.dll"


def test_game_assembly_path_finds_the_linux_elf(tmp_path: Path) -> None:
    (tmp_path / "GameAssembly.so").write_bytes(b"\x7fELF")
    assert dump.game_assembly_path(tmp_path) == tmp_path / "GameAssembly.so"


def test_game_assembly_path_prefers_the_dll_when_both_exist(tmp_path: Path) -> None:
    (tmp_path / "GameAssembly.so").write_bytes(b"\x7fELF")
    (tmp_path / "GameAssembly.dll").write_bytes(b"MZ")
    assert dump.game_assembly_path(tmp_path) == tmp_path / "GameAssembly.dll"


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


def test_main_passes_game_and_out(monkeypatch) -> None:
    seen = {}

    def fake_run_dump(game=None, outdir=None, dumper_dll=dump.DUMPER_DLL):
        seen["game"] = game
        seen["outdir"] = outdir

    monkeypatch.setattr(dump, "run_dump", fake_run_dump)
    code = dump.main(["--game", "/tmp/Megabonk", "--out", "/tmp/out"])
    assert code == 0
    assert seen["game"] == Path("/tmp/Megabonk")
    assert seen["outdir"] == Path("/tmp/out")
