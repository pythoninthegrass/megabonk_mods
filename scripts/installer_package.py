"""Build and verify the thin distributable for one platform: the Go installer binary and a README, nothing else."""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

PLATFORMS = ("linux", "windows", "macos")
README_NAME = "README.txt"
EXECUTABLE_NAMES = {"linux": "megabonk-installer", "windows": "megabonk-installer.exe", "macos": "megabonk-installer"}
FALLBACK_STAMP = (1980, 1, 1, 0, 0, 0)

SITE = "https://megabonkmod.party"


class ZipError(Exception):
    """A distributable cannot be built or is not the one this task would have written."""


PLATFORM_LABELS = {"linux": "Linux", "windows": "Windows", "macos": "macOS"}


def zip_name(version: str, platform: str) -> str:
    if platform not in PLATFORMS:
        raise ZipError(f"Unknown package platform {platform!r}; expected one of {', '.join(PLATFORMS)}.")
    return f"megabonk-installer-{version}-{platform}.zip"


def readme_text(platform: str) -> str:
    """The README a player reads next to the binary: how to run it, and what it pulls down."""
    if platform not in PLATFORMS:
        raise ZipError(f"Unknown package platform {platform!r}; expected one of {', '.join(PLATFORMS)}.")
    binary_name = EXECUTABLE_NAMES[platform]
    lines = [
        "Megabonk Levels installer",
        "",
        f"Platform: {PLATFORM_LABELS[platform]}",
        "",
        "Run the installer from a terminal in this folder:",
        "",
    ]
    if platform == "macos":
        lines += [
            "  xattr -d com.apple.quarantine megabonk-installer",
            "  ./megabonk-installer",
            "",
            "The clear Extended Attribute step is only needed when the binary was downloaded and",
            "macOS has quarantined it; a notarized build can be run directly with a double-click.",
        ]
    elif platform == "windows":
        lines += ["  megabonk-installer.exe"]
    else:
        lines += ["  chmod +x megabonk-installer", "  ./megabonk-installer"]
    lines += [
        "",
        "What it installs:",
        "",
        "  * the level editor mod and the loader pack it runs on,",
        "  * levels and their art, and the packs those levels need,",
        "  * characters, in a later release.",
        "",
        "Nothing else is in this zip. The installer fetches every file above at run time from",
        f"{SITE} and from the Thunderstore mod site, so what you get is always the current",
        "release; it needs an internet connection and no other tooling, no Python and no repo checkout.",
        "",
        "It finds the game through Steam, asks which install to use when there is more than one,",
        "and records what it put where so a later run can update or remove it.",
        "",
        f"Level gallery and downloads: {SITE}",
        "",
    ]
    return "\n".join(lines)


def zip_stamp(env: Mapping[str, str] | None = None) -> tuple[int, int, int, int, int, int]:
    """The timestamp every member gets: SOURCE_DATE_EPOCH when it is a real epoch."""
    epoch = (os.environ if env is None else env).get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        return datetime.fromtimestamp(int(epoch), UTC).timetuple()[:6]
    return FALLBACK_STAMP


def build_zip(
    installer_binary: Path,
    zip_path: Path,
    *,
    platform: str,
    version: str = "dev",
    env: Mapping[str, str] | None = None,
) -> Path:
    """Write the distributable: exactly the installer binary and the README, byte-reproducible for a fixed epoch."""
    if platform not in PLATFORMS:
        raise ZipError(f"Unknown package platform {platform!r}; expected one of {', '.join(PLATFORMS)}.")
    if not installer_binary.is_file():
        raise FileNotFoundError(
            f"No {platform} installer binary at {installer_binary}. Run `task installer:build` first.",
        )
    members = [
        (EXECUTABLE_NAMES[platform], installer_binary.read_bytes(), 0o755),
        (README_NAME, readme_text(platform).encode(), 0o644),
    ]
    stamp = zip_stamp(env)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = zip_path.with_name(zip_path.name + ".part")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body, mode in members:
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, body)
    temporary.replace(zip_path)
    return zip_path


def expected_members(platform: str) -> tuple[str, ...]:
    return (EXECUTABLE_NAMES[platform], README_NAME)


def zip_members(zip_path: Path) -> list[str]:
    """The file entries of a zip, sorted; directory entries are not members."""
    with zipfile.ZipFile(zip_path) as archive:
        return sorted(info.filename for info in archive.infolist() if not info.is_dir())


def check_zip(zip_path: Path, *, platform: str) -> list[str]:
    """One message per way a zip is not the thin distributable; empty when it is exactly the binary and the README."""
    if platform not in PLATFORMS:
        raise ZipError(f"Unknown package platform {platform!r}; expected one of {', '.join(PLATFORMS)}.")
    if not zip_path.is_file():
        return [f"{zip_path} does not exist."]
    try:
        found = zip_members(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        return [f"{zip_path} is not a readable zip: {exc}"]
    expected = list(expected_members(platform))
    problems = [f"{zip_path.name} is missing {name}" for name in expected if name not in found]
    problems += [f"{zip_path.name} has unexpected entry {name}" for name in found if name not in expected]
    return problems


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, help="The distributable zip to check.")
    parser.add_argument("--platform", choices=PLATFORMS, required=True, help="Which platform the zip claims to be.")
    return parser.parse_args(argv)


def build_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the thin distributable zip for one platform.")
    parser.add_argument("--installer-binary", type=Path, required=True, help="The binary task installer:build produced.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Where to write the zip.")
    parser.add_argument("--platform", choices=PLATFORMS, required=True, help="Which platform the binary is for.")
    parser.add_argument("--version", default="dev", help="Version carried in the zip name.")
    args = parser.parse_args(argv)
    try:
        path = build_zip(
            args.installer_binary,
            args.out_dir / zip_name(args.version, args.platform),
            platform=args.platform,
            version=args.version,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except ZipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Distributable written to {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "build":
        return build_main(argv[1:])
    args = parse_args(argv)
    problems = check_zip(args.zip, platform=args.platform)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"{args.zip.name}: {', '.join(expected_members(args.platform))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
