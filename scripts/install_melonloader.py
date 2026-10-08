#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""
Downloads a pinned MelonLoader release (the Linux build on Linux, the Windows
build elsewhere), verifies its checksum, and extracts it into the resolved
Megabonk game directory. On macOS (CrossOver), also
applies the Wine DLL override MelonLoader's installer normally sets for you
(version.dll -> native,builtin) so Il2Cpp hooking works under Wine.

Idempotent: install() skips the download/extract when the pinned version is
already present.

Usage:
  uv run scripts/install_melonloader.py --check   # prints whether the pinned version is installed
  uv run scripts/install_melonloader.py           # installs if not already present
"""

import argparse
import hashlib
import io
import os
import platform
import subprocess
import sys
import urllib.request
import zipfile
from decouple import config
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import game_paths as gp

CROSSOVER_WINE_CANDIDATES = [
    Path("/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine"),
]

# Every pin below is overridable via the environment or .env (env > .env > default).
MELONLOADER_VERSION = config("MELONLOADER_VERSION", default="0.7.3")
RELEASE_URL_TEMPLATE = (
    "https://github.com/LavaGang/MelonLoader/releases/download/v{version}/{asset}"
)
ASSET_WINDOWS = "MelonLoader.x64.zip"
ASSET_LINUX = "MelonLoader.Linux.x64.zip"
DEFAULT_SHA256_WINDOWS = "5b2b2f3d1cd42b59ec886c5bdc2663edae87a0097a4f4a8f58c0965a99dda416"
DEFAULT_SHA256_LINUX = "519f25639cde796a749ea0670daedfa251a45d0217608ac6e12c1bc6aa9e114f"

VERSION_MARKER_NAME = "MegabonkLevels.melonloader_version"


def release_asset(system: str, version: str = MELONLOADER_VERSION) -> tuple[str, str]:
    """Returns the (url, sha256) of the release archive for the given platform.system() value."""
    if system == "Linux":
        suffix, asset, sha = "LINUX", ASSET_LINUX, DEFAULT_SHA256_LINUX
    else:
        suffix, asset, sha = "WINDOWS", ASSET_WINDOWS, DEFAULT_SHA256_WINDOWS
    url = config(
        f"MELONLOADER_URL_{suffix}",
        default=RELEASE_URL_TEMPLATE.format(version=version, asset=asset),
    )
    return url, config(f"MELONLOADER_SHA256_{suffix}", default=sha)


def _version_marker_path(game: Path) -> Path:
    return gp.melonloader_dir(game) / VERSION_MARKER_NAME


def is_installed(version: str, game: Path | None = None) -> bool:
    game = game or gp.game_dir()
    marker = _version_marker_path(game)
    if not marker.is_file():
        return False
    return marker.read_text().strip() == version


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:  # noqa: S310
        return response.read()


def _verify_sha256(data: bytes, expected: str) -> None:
    digest = hashlib.sha256(data).hexdigest()
    if not expected:
        print(
            f"warning: the archive sha256 is not pinned, skipping verification. "
            f"Downloaded archive sha256: {digest} - pin it via MELONLOADER_SHA256_WINDOWS or "
            f"MELONLOADER_SHA256_LINUX once you've confirmed it against a trusted source.",
            file=sys.stderr,
        )
        return
    if digest != expected:
        raise ValueError(f"checksum mismatch: expected {expected}, got {digest}")


def _find_crossover_wine() -> Path | None:
    override = os.environ.get("CROSSOVER_WINE_BIN")
    if override:
        return Path(override)
    for candidate in CROSSOVER_WINE_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _apply_crossover_dll_override(bottle_name: str) -> None:
    """Sets version.dll = native,builtin in the bottle's Wine registry.

    MelonLoader's own installer documents this override as required for
    Il2Cpp hooking under Wine/CrossOver. CrossOver's own `wine` is a Perl
    wrapper that resolves a bottle by *name* via `--bottle` (or $CX_BOTTLE),
    not by WINEPREFIX path - passing WINEPREFIX directly makes it look for a
    bottle named "default" instead.
    """
    wine_bin = _find_crossover_wine()
    if wine_bin is None:
        print(
            "warning: could not locate CrossOver's wine binary; skipping the "
            "version.dll override. Set CROSSOVER_WINE_BIN or apply it manually.",
            file=sys.stderr,
        )
        return

    subprocess.run(
        [
            str(wine_bin),
            "--bottle",
            bottle_name,
            "reg",
            "add",
            r"HKCU\Software\Wine\DllOverrides",
            "/v",
            "version",
            "/d",
            "native,builtin",
            "/f",
        ],
        check=True,
    )


def install(version: str = MELONLOADER_VERSION, game: Path | None = None) -> None:
    game = game or gp.game_dir()
    if is_installed(version, game):
        print(f"MelonLoader {version} already installed at {game}")
    else:
        print(f"Downloading MelonLoader {version}...")
        url, sha256 = release_asset(platform.system(), version)
        data = _download(url)
        _verify_sha256(data, sha256)

        game.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(game)

        _version_marker_path(game).write_text(version)
        print(f"MelonLoader {version} installed to {game}")

    # Re-applied every run, even when already installed: idempotent (wine reg
    # add overwrites the same value) and needs to succeed on its own retry if
    # it failed on a prior run (e.g. wine wasn't found yet).
    if platform.system() == "Darwin":
        bottle_name = _lookup_bottle_name(game)
        if bottle_name is not None:
            _apply_crossover_dll_override(bottle_name)


def _lookup_bottle_name(game: Path) -> str | None:
    """Returns the CrossOver bottle's name (e.g. "Steam"), i.e. drive_c's parent dir name."""
    for parent in game.parents:
        if parent.name == "drive_c":
            return parent.parent.name
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="print whether the pinned version is installed and exit",
    )
    args = parser.parse_args()

    if args.check:
        installed = is_installed(MELONLOADER_VERSION)
        print(f"MelonLoader {MELONLOADER_VERSION} installed: {installed}")
        return 0 if installed else 1

    install()
    return 0


if __name__ == "__main__":
    sys.exit(main())
