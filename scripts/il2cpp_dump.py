"""
Wraps the Il2CppDumper invocation proven manually against the Megabonk
install: Il2CppDumper's net7 build run under the mise-managed dotnet 10 SDK
with roll-forward, since the system has no standalone net7 runtime.

  mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll \
      <GameAssembly.dll or GameAssembly.so> <global-metadata.dat> <outdir>
  (with DOTNET_ROLL_FORWARD=LatestMajor in the environment)

Usage: uv run scripts/il2cpp_dump.py [--game DIR] [--out DIR]
"""

import argparse
import os
import subprocess
import sys
from megabonk_harness import game_paths as gp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DUMPER_DLL = REPO_ROOT / ".tools" / "Il2CppDumper" / "Il2CppDumper.dll"
OUTPUT_DIR = REPO_ROOT / ".tools" / "il2cpp_dump"
DOTNET_SDK = "dotnet@10.0.108"


ASSEMBLY_NAMES = ("GameAssembly.dll", "GameAssembly.so")


def game_assembly_path(game: Path | None = None) -> Path:
    base = game or gp.game_dir()
    for name in ASSEMBLY_NAMES:
        if (base / name).is_file():
            return base / name
    return base / ASSEMBLY_NAMES[0]


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
        raise FileNotFoundError(f"Il2CppDumper.dll not found at {dumper_dll}; download it into .tools/Il2CppDumper/ first")

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Il2CppDumper over a GameAssembly/metadata pair.")
    parser.add_argument(
        "--game",
        type=Path,
        help="game directory holding GameAssembly.dll/.so and <name>_Data/il2cpp_data/Metadata",
    )
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR, help="directory for dump.cs and friends")
    args = parser.parse_args(argv)
    run_dump(game=args.game, outdir=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
