#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Resolves the Megabonk install directory and the paths derived from it
(MelonLoader dir, Mods dir, UserLibs dir, Latest.log).

Precedence: process env > .env file in the repo root > built-in default.
Defaults assume a Steam install, CrossOver bottle on macOS.

Usage: uv run tools/game_paths.py
"""

import json
import os
import platform
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"

DEFAULT_BOTTLE_MACOS = (
    "~/Library/Application Support/CrossOver/Bottles/Steam/drive_c"
)
DEFAULT_GAME_SUBPATH = "Program Files (x86)/Steam/steamapps/common/Megabonk"
DEFAULT_GAME_DIR_WINDOWS = r"C:\Program Files (x86)\Steam\steamapps\common\Megabonk"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _lookup(key: str, env_file_values: dict[str, str]) -> str | None:
    if key in os.environ:
        return os.environ[key]
    if key in env_file_values:
        return env_file_values[key]
    return None


def game_dir(env_file_values: dict[str, str] | None = None) -> Path:
    if env_file_values is None:
        env_file_values = _parse_env_file(ENV_FILE)

    override = _lookup("MEGABONK_GAME_DIR", env_file_values)
    if override:
        return Path(override).expanduser()

    bottle = _lookup("MEGABONK_BOTTLE", env_file_values)
    if bottle:
        return Path(bottle).expanduser() / DEFAULT_GAME_SUBPATH

    if platform.system() == "Windows":
        return Path(DEFAULT_GAME_DIR_WINDOWS)

    return Path(DEFAULT_BOTTLE_MACOS).expanduser() / DEFAULT_GAME_SUBPATH


def melonloader_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "MelonLoader"


def mods_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "Mods"


def userlibs_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "UserLibs"


def latest_log_path(game: Path | None = None) -> Path:
    return melonloader_dir(game) / "Latest.log"


def resolved_paths() -> dict[str, str]:
    game = game_dir()
    return {
        "game_dir": str(game),
        "melonloader_dir": str(melonloader_dir(game)),
        "mods_dir": str(mods_dir(game)),
        "userlibs_dir": str(userlibs_dir(game)),
        "latest_log_path": str(latest_log_path(game)),
    }


def main() -> int:
    print(json.dumps(resolved_paths(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
