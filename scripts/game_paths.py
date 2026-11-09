#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Resolves the Megabonk install directory and the paths derived from it
(BepInEx dir, plugins dir, plugin deploy dir, LogOutput.log, Wine log).

Precedence: process env > .env file in the repo root > built-in default.
The Wine prefix holds the Steam install: MEGABONK_WINE_PREFIX names it, MEGABONK_GAME_DIR overrides the game
directory directly, and MEGABONK_BOTTLE (a prefix's drive_c) is the older spelling of the prefix setting.
Without any of them the prefix is ~/.local/share/megabonk/wine for plain Wine (MEGABONK_MACOS_RUNTIME=wine) and the
CrossOver Steam bottle for CrossOver (crossover). MEGABONK_WINE points at the plain Wine binary.

Usage: uv run scripts/game_paths.py
"""

import json
import os
import platform
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"

DEFAULT_WINE_PREFIX = "~/.local/share/megabonk/wine"
DEFAULT_CROSSOVER_PREFIX = "~/Library/Application Support/CrossOver/Bottles/Steam"
DEFAULT_WINE_BIN = "~/Applications/wine11/Wine Devel.app/Contents/Resources/wine/bin/wine"
MACOS_RUNTIMES = ("wine", "crossover")
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


def _env_lookup(env_file_values: dict[str, str] | None) -> Callable[[str], str | None]:
    values = _parse_env_file(ENV_FILE) if env_file_values is None else env_file_values
    return lambda key: _lookup(key, values)


def resolve_game_dir(lookup: Callable[[str], str | None], system: str | None = None) -> Path:
    system = system or platform.system()

    override = lookup("MEGABONK_GAME_DIR")
    if override:
        return Path(override).expanduser()

    prefix = lookup("MEGABONK_WINE_PREFIX")
    if prefix:
        return Path(prefix).expanduser() / "drive_c" / DEFAULT_GAME_SUBPATH

    bottle = lookup("MEGABONK_BOTTLE")
    if bottle:
        return Path(bottle).expanduser() / DEFAULT_GAME_SUBPATH

    if system == "Windows":
        return Path(DEFAULT_GAME_DIR_WINDOWS)

    default_prefix = DEFAULT_CROSSOVER_PREFIX if lookup("MEGABONK_MACOS_RUNTIME") == "crossover" else DEFAULT_WINE_PREFIX
    return Path(default_prefix).expanduser() / "drive_c" / DEFAULT_GAME_SUBPATH


def game_dir(env_file_values: dict[str, str] | None = None) -> Path:
    return resolve_game_dir(_env_lookup(env_file_values))


def to_game_path(path: Path, system: str | None = None) -> str:
    """Path as the game process sees it; CrossOver's Wine exposes the host filesystem as Z:."""
    system = system or platform.system()
    if system == "Darwin":
        return "Z:" + str(path).replace("/", "\\")
    return str(path)


def evidence_dir() -> Path:
    """The repo's gitignored folder where screenshots land by default."""
    return Path(__file__).resolve().parent.parent / ".tools" / "evidence"


def macos_runtime(env_file_values: dict[str, str] | None = None) -> str:
    if env_file_values is None:
        env_file_values = _parse_env_file(ENV_FILE)
    runtime = _lookup("MEGABONK_MACOS_RUNTIME", env_file_values) or "wine"
    if runtime not in MACOS_RUNTIMES:
        raise ValueError(f"MEGABONK_MACOS_RUNTIME must be one of {MACOS_RUNTIMES}, got {runtime!r}")
    return runtime


def wine_bin(env_file_values: dict[str, str] | None = None) -> Path:
    if env_file_values is None:
        env_file_values = _parse_env_file(ENV_FILE)
    return Path(_lookup("MEGABONK_WINE", env_file_values) or DEFAULT_WINE_BIN).expanduser()


def wine_prefix(game: Path, env_file_values: dict[str, str] | None = None) -> Path | None:
    explicit = _env_lookup(env_file_values)("MEGABONK_WINE_PREFIX")
    if explicit:
        return Path(explicit).expanduser()
    for parent in game.parents:
        if parent.name == "drive_c":
            return parent.parent
    return None


def melonloader_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "MelonLoader"


def mods_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "Mods"


def userlibs_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "UserLibs"


def latest_log_path(game: Path | None = None) -> Path:
    return bepinex_dir(game) / "LogOutput.log"


def bepinex_dir(game: Path | None = None) -> Path:
    return (game or game_dir()) / "BepInEx"


def plugins_dir(game: Path | None = None) -> Path:
    return bepinex_dir(game) / "plugins"


def plugin_dir(game: Path | None = None) -> Path:
    return plugins_dir(game) / "MegabonkLevels"


def wine_log_path(game: Path | None = None) -> Path:
    return bepinex_dir(game) / "wine-latest.log"


def resolved_paths() -> dict[str, str]:
    game = game_dir()
    prefix = wine_prefix(game)
    return {
        "game_dir": str(game),
        "wine_prefix": str(prefix) if prefix else None,
        "bepinex_dir": str(bepinex_dir(game)),
        "plugins_dir": str(plugins_dir(game)),
        "plugin_dir": str(plugin_dir(game)),
        "latest_log_path": str(latest_log_path(game)),
        "wine_log_path": str(wine_log_path(game)),
    }


def main() -> int:
    print(json.dumps(resolved_paths(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
