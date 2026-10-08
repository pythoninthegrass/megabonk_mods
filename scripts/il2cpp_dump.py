#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Wraps the Il2CppDumper invocation proven manually against the Megabonk
install: Il2CppDumper's net7 build run under the mise-managed dotnet 10 SDK
with roll-forward, since the system has no standalone net7 runtime.

  mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll \
      <GameAssembly.dll> <global-metadata.dat> <outdir>
  (with DOTNET_ROLL_FORWARD=LatestMajor in the environment)

Usage: uv run scripts/il2cpp_dump.py
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import game_paths as gp

REPO_ROOT = Path(__file__).resolve().parents[1]
DUMPER_DLL = REPO_ROOT / ".tools" / "Il2CppDumper" / "Il2CppDumper.dll"
OUTPUT_DIR = REPO_ROOT / ".tools" / "il2cpp_dump"
DOTNET_SDK = "dotnet@10.0.108"


def game_assembly_path(game: Path | None = None) -> Path:
    return (game or gp.game_dir()) / "GameAssembly.dll"


def global_metadata_path(game: Path | None = None) -> Path:
    game = game or gp.game_dir()
    return game / f"{game.name}_Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat"


def build_command(
    game_assembly: Path,
    global_metadata: Path,
    outdir: Path,
    dumper_dll: Path = DUMPER_DLL,
) -> list[str]:
    return [
        "mise",
        "exec",
        DOTNET_SDK,
        "--",
        "dotnet",
        str(dumper_dll),
        str(game_assembly),
        str(global_metadata),
        str(outdir),
    ]


def run_dump(
    game: Path | None = None,
    outdir: Path = OUTPUT_DIR,
    dumper_dll: Path = DUMPER_DLL,
) -> None:
    if not dumper_dll.is_file():
        raise FileNotFoundError(
            f"Il2CppDumper.dll not found at {dumper_dll}; download it into .tools/Il2CppDumper/ first"
        )

    game_assembly = game_assembly_path(game)
    global_metadata = global_metadata_path(game)
    if not game_assembly.is_file():
        raise FileNotFoundError(f"GameAssembly.dll not found at {game_assembly}")
    if not global_metadata.is_file():
        raise FileNotFoundError(f"global-metadata.dat not found at {global_metadata}")

    outdir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}
    subprocess.run(
        build_command(game_assembly, global_metadata, outdir, dumper_dll),
        env=env,
        check=True,
    )


def main() -> int:
    run_dump()
    return 0


if __name__ == "__main__":
    sys.exit(main())
