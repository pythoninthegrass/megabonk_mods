"""Telling the Windows Megabonk build from the Linux native one, and what to say when it is the latter.

MelonLoader 0.7.3 crashes the native Linux build during Il2Cpp assembly generation (the
upstream fix is unreleased), so the installer supports only the Windows build running under
Steam Play / Proton and steers the player there instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

WINDOWS = "windows"
NATIVE_LINUX = "native-linux"
MIXED = "mixed"
UNKNOWN = "unknown"

WINDOWS_EXE = "Megabonk.exe"
NATIVE_EXE = "Megabonk.x86_64"
DATA_DIR = "Megabonk_Data"
GAME_ASSEMBLY = "GameAssembly.dll"
UNITY_PLAYER = "UnityPlayer.dll"


@dataclass(frozen=True)
class GameBuild:
    game_dir: Path
    build: str
    has_windows_exe: bool
    has_native_exe: bool
    has_data_dir: bool

    @property
    def supported(self) -> bool:
        return is_supported(self.build)


def classify_game_dir(game_dir: Path | str) -> GameBuild:
    game_dir = Path(game_dir)
    has_windows_exe = (game_dir / WINDOWS_EXE).is_file()
    has_native_exe = (game_dir / NATIVE_EXE).is_file()
    has_data_dir = (game_dir / DATA_DIR).is_dir()
    if not (game_dir / DATA_DIR).exists():
        has_data_dir = False
    if has_windows_exe and has_native_exe:
        build = MIXED
    elif has_windows_exe or (has_data_dir and (game_dir / GAME_ASSEMBLY).is_file()):
        build = WINDOWS
    elif has_native_exe:
        build = NATIVE_LINUX
    else:
        build = UNKNOWN
    return GameBuild(
        game_dir=game_dir,
        build=build,
        has_windows_exe=has_windows_exe,
        has_native_exe=has_native_exe,
        has_data_dir=has_data_dir,
    )


def is_supported(build: str) -> bool:
    """The Windows layout is the only one MelonLoader can hook on Linux today."""
    return build in (WINDOWS, MIXED)


def launch_binary(build: str) -> str:
    return NATIVE_EXE if build == NATIVE_LINUX else WINDOWS_EXE


def native_build_message(melonloader_version: str = "0.7.3", game_dir: Path | str | None = None) -> str:
    where = f" in {game_dir}" if game_dir else ""
    return "\n".join(
        [
            f"This is the Linux native build of Megabonk{where}: it runs Megabonk.x86_64, not Megabonk.exe.",
            f"MelonLoader {melonloader_version} crashes that build while it generates the Il2Cpp assemblies "
            "(the upstream fix is not in a release yet), so the map editor cannot be installed on it.",
            "",
            "Install the Windows build instead and let Steam run it under Proton:",
            "  1. Steam > Library > Megabonk > right-click > Properties > Installed Files:",
            "     remove the checkmark from 'Only download on my OS for this game' (or untick the",
            "     Steam Play 'Use the Linux version when available' option), then let it redownload.",
            "  2. Properties > Compatibility > tick 'Force the use of a specific Steam Play",
            "     compatibility tool' and pick a Proton version.",
            "  3. Launch the game once so Steam creates its Proton prefix, then quit it.",
            "  4. Run this installer again.",
        ]
    )


def unknown_build_message(game_dir: Path | str) -> str:
    game_dir = Path(game_dir)
    return "\n".join(
        [
            f"{game_dir} does not look like a Megabonk install: there is no {WINDOWS_EXE} and no {DATA_DIR}/ next to it.",
            "",
            "Point the installer at the folder Steam put the game in, the one holding",
            f"{WINDOWS_EXE}, {GAME_ASSEMBLY} and {DATA_DIR}/, for example:",
            "  <steam library>/steamapps/common/Megabonk",
            "",
            "If Megabonk is not installed yet, install it in Steam first and start it once.",
        ]
    )


def unsupported_build_message(game_dir: Path | str, build: str, melonloader_version: str = "0.7.3") -> str:
    if build == NATIVE_LINUX:
        return native_build_message(melonloader_version, game_dir)
    return unknown_build_message(game_dir)
