"""Build the player-facing package (Linux or Windows): installer, mod, MelonLoader, .NET, content."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asset_download  # noqa: E402
from build_thps_level import GAME_BUILD_ID  # noqa: E402
from install_melonloader import ASSET_WINDOWS, MELONLOADER_VERSION, release_asset  # noqa: E402
from player_installer import manifest as manifest_mod  # noqa: E402
from player_installer.content import LEVEL_PACKS_DIR_NAME, LEVELS_DIR_NAME, validate_pack_source  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_OUTPUT_DIR = REPO_ROOT / "src/MegabonkLevels.Mod/bin/Release/net6.0"
DEFAULT_LEVELS_DIR = REPO_ROOT / "levels"
DEFAULT_BUNDLES_DIR = REPO_ROOT / ".tools/bundles"
DEFAULT_PACKS_SRC = REPO_ROOT / "unity/pack-authoring/packs"
DEFAULT_CACHE = REPO_ROOT / ".tools/vendor-cache"
INSTALLER_SOURCE = Path(__file__).resolve().parent / "player_installer"

PACKAGE_ID = "megabonk-levels"
PACKAGE_MANIFEST_NAME = "manifest.json"

MOD_DLL = "MegabonkLevels.Mod.dll"
USERLIBS = ["NLayer.dll"]
MOD_SKIP = {MOD_DLL, "MegabonkLevels.Mod.pdb", "MegabonkLevels.Mod.deps.json", "MegabonkLevels.Mod.runtimeconfig.json", *USERLIBS}

DOTNET_VERSION = "6.0.36"
DOTNET_WINDOWS_ASSET = f"dotnet-runtime-{DOTNET_VERSION}-win-x64.zip"
DOTNET_WINDOWS_URL = (
    f"https://dotnetcli.azureedge.net/dotnet/Runtime/{DOTNET_VERSION}/{DOTNET_WINDOWS_ASSET}"
)
DOTNET_WINDOWS_SHA256 = "c077ccc342c5571ceb7a3c06d1dfbc99b989ed5a6e0f3a0b0b450531c1259615"
MELONLOADER_ASSET = "MelonLoader.x64.zip"

PLATFORMS = ("linux", "windows")
WINDOWS_INSTALLER_NAME = "install.exe"

MIN_PYTHON = (3, 11)
_MIN_PYTHON_TEXT = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"

# f-string template: a literal shell brace has to be doubled.
INSTALL_SH = f"""#!/bin/sh
# Installs the Megabonk Levels mod on Linux. Requires Python {_MIN_PYTHON_TEXT} or newer.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

PYTHON=${{MEGABONK_PYTHON:-}}
EXPLICIT=0
if [ -n "$PYTHON" ]; then
  EXPLICIT=1
else
  PYTHON=python3
fi
after_python=0
for argument in "$@"; do
  if [ "$after_python" = 1 ]; then
    PYTHON=$argument
    EXPLICIT=1
    after_python=0
    continue
  fi
  case "$argument" in
    --python) after_python=1 ;;
    --python=*) PYTHON=${{argument#--python=}}; EXPLICIT=1 ;;
  esac
done

if [ ! -x "$PYTHON" ] && ! command -v "$PYTHON" >/dev/null 2>&1; then
  if [ "$EXPLICIT" = 1 ]; then
    echo "no interpreter at $PYTHON, given by --python or MEGABONK_PYTHON." >&2
    echo "Pass the full path of a Python {_MIN_PYTHON_TEXT} interpreter, for example --python /usr/bin/python{_MIN_PYTHON_TEXT}." >&2
    exit 2
  fi
  echo "python3 is required but was not found on PATH." >&2
  echo "Install Python {_MIN_PYTHON_TEXT} (for example: sudo dnf install python{_MIN_PYTHON_TEXT}), or point this script at one you have: --python /path/to/python{_MIN_PYTHON_TEXT}." >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= {MIN_PYTHON!r} else 1)' 2>/dev/null; then
  PY_VERSION=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "unknown")
  echo "This installer needs Python {_MIN_PYTHON_TEXT} or newer; found $PY_VERSION ($PYTHON)." >&2
  echo "Install Python {_MIN_PYTHON_TEXT} (for example: sudo dnf install python{_MIN_PYTHON_TEXT}), or run this with one you already have:" >&2
  echo "  --python /path/to/python{_MIN_PYTHON_TEXT}   (or MEGABONK_PYTHON=/path/to/python{_MIN_PYTHON_TEXT} ./install.sh)" >&2
  exit 1
fi

exec env PYTHONPATH="$SCRIPT_DIR/installer${{PYTHONPATH:+:$PYTHONPATH}}" "$PYTHON" -m player_installer --package "$SCRIPT_DIR" "$@"
"""


class BuildError(Exception):
    """A package cannot be built."""


class MissingInput(BuildError):
    """A required input (the mod build, a cached archive) is not there yet."""


def say(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(f"error: {message}", file=sys.stderr, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, destination: Path, allow_download: bool, expected_sha256: str | None = None) -> Path:
    if destination.exists():
        return destination
    if not allow_download:
        raise MissingInput(
            f"{destination.name} is not cached. Pass --allow-download to fetch "
            f"{url}, or place the file at {destination}."
        )
    say(f"Downloading {url}")
    try:
        return asset_download.download_to(url, destination, expected_sha256=expected_sha256)
    except asset_download.MissingAsset as exc:
        raise MissingInput(f"{exc}. Place the file at {destination} to build without downloading.") from exc
    except asset_download.DownloadError as exc:
        raise BuildError(str(exc)) from exc


def verify_sha256(path: Path, expected: str | None, label: str) -> str:
    actual = sha256_file(path)
    if expected and actual != expected:
        raise BuildError(
            f"{label} has sha256 {actual}, expected {expected}. Delete {path} and run again "
            "with --allow-download."
        )
    return actual


def install_sh_content() -> str:
    return INSTALL_SH


def mod_file_entries(mod_source: Path) -> list[tuple[str, str, str]]:
    """Return (name in the mod output dir, path in the package, dest under the game dir)."""
    entries = [(MOD_DLL, MOD_DLL, f"Mods/{MOD_DLL}")]
    entries += [(name, name, f"UserLibs/{name}") for name in USERLIBS]
    for name in sorted(
        p.name
        for p in mod_source.iterdir()
        if p.is_file() and p.suffix.lower() in {".dll", ".json"} and p.name not in MOD_SKIP
    ):
        entries.append((name, name, f"Mods/{name}"))
    return entries


def check_mod_source(mod_source: Path) -> None:
    if not mod_source.is_dir() or not (mod_source / MOD_DLL).is_file():
        raise MissingInput(f"No mod build found at {mod_source}. Run `task mod:build` first.")
    for name in USERLIBS:
        if not (mod_source / name).is_file():
            raise MissingInput(
                f"{mod_source} has no {name}. The mod project must copy its local assemblies; "
                "check CopyLocalLockFileAssemblies."
            )


def add_vendors(staging: Path, cache: Path, allow_download: bool) -> list[dict]:
    melonloader_url, melonloader_sha = release_asset("Windows", MELONLOADER_VERSION)
    entries = []
    for kind, version, url, asset, expected in [
        ("melonloader", MELONLOADER_VERSION, melonloader_url, ASSET_WINDOWS, melonloader_sha),
        ("dotnet", DOTNET_VERSION, DOTNET_WINDOWS_URL, DOTNET_WINDOWS_ASSET, DOTNET_WINDOWS_SHA256),
    ]:
        archive = fetch(url, cache / asset, allow_download, expected)
        digest = verify_sha256(archive, expected, asset)
        shutil.copy2(archive, staging / "vendor" / asset)
        entries.append({"name": asset, "url": url, "sha256": digest, "kind": kind, "version": version})
    return entries


def add_mod(staging: Path, mod_source: Path) -> list[dict]:
    entries = []
    for name, package_path, dest in mod_file_entries(mod_source):
        target = staging / package_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mod_source / name, target)
        entries.append({"path": package_path, "sha256": sha256_file(target), "dest": dest})
    return entries


def add_levels(staging: Path, levels_root: Path, names: list[str]) -> list[dict]:
    """Copy the named levels into the package. Dev scratch maps are never bundled."""
    entries = []
    for name in sorted(names):
        if name_is_local_scratch(name):
            say(f"skipping {name}: a .local map is a working file, not player content")
            continue
        source = levels_root / name
        if not source.is_file():
            raise MissingInput(f"{name} is not in {levels_root}.")
        target = staging / "content/levels" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries.append(
            {
                "path": f"content/levels/{name}",
                "sha256": sha256_file(target),
                "dest": f"UserData/{LEVELS_DIR_NAME}/{name}",
            }
        )
    return entries


def name_is_local_scratch(name: str) -> bool:
    return name.endswith(".local.mblevel.json")


def add_packs(staging: Path, bundles_dir: Path, packs_src: Path, platform: str, names: list[str]) -> list[dict]:
    """Stage each named pack the way `task pack:install` does, then refuse an invalid one.

    A pack is three files from two places: the AssetBundle at
    ``bundles_dir/<platform>/<pack>`` and the manifest (plus optional attachments) under
    ``packs_src/<pack>/``. Windows bundles are the right ones on Linux: the game runs the
    Windows build under Proton.
    """
    entries = []
    for pack in sorted(names):
        bundle = bundles_dir / platform / pack
        manifest = packs_src / pack / "manifest.json"
        if not bundle.is_file():
            raise MissingInput(
                f"No {platform} AssetBundle for pack {pack} at {bundle}. Run `task pack:{pack}` or `task pack:build`."
            )
        if not manifest.is_file():
            raise MissingInput(f"No manifest for pack {pack} at {manifest}.")
        target = staging / "content/packs" / pack
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundle, target / pack)
        shutil.copy2(manifest, target / "manifest.json")
        attachments = packs_src / pack / "attachments.json"
        if attachments.is_file():
            shutil.copy2(attachments, target / "attachments.json")
        errors = validate_pack_source(target)
        if errors:
            raise BuildError(f"Pack {pack} is not valid: {'; '.join(errors)}")
        for member in sorted(p for p in target.rglob("*") if p.is_file()):
            relative = member.relative_to(target).as_posix()
            entries.append(
                {
                    "path": f"content/packs/{pack}/{relative}",
                    "sha256": sha256_file(member),
                    "dest": f"UserData/{LEVEL_PACKS_DIR_NAME}/{pack}/{relative}",
                }
            )
    return entries


def add_windows_installer(staging: Path, binary: Path | None) -> None:
    if binary is None:
        raise BuildError("A Windows package needs the installer binary: pass --installer-binary.")
    if not binary.is_file():
        raise MissingInput(f"No installer binary at {binary}. Run `task installer:build` first.")
    shutil.copy2(binary, staging / WINDOWS_INSTALLER_NAME)


def add_installer(staging: Path) -> None:
    target = staging / "installer/player_installer"
    target.mkdir(parents=True, exist_ok=True)
    for module in sorted(INSTALLER_SOURCE.glob("*.py")):
        shutil.copy2(module, target / module.name)


def generated_stamp(now: datetime | None = None) -> str:
    """UTC timestamp for the manifest, pinned by SOURCE_DATE_EPOCH when set."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        return datetime.fromtimestamp(int(epoch), UTC).isoformat(timespec="seconds")
    return (now or datetime.now(UTC)).isoformat(timespec="seconds")


def assemble(
    staging: Path,
    cache: Path,
    mod_source: Path,
    levels_root: Path,
    level_names: list[str],
    bundles_dir: Path,
    packs_src: Path,
    pack_platform: str,
    pack_names: list[str],
    allow_download: bool,
    mod_version: str,
    platform: str = "linux",
    installer_binary: Path | None = None,
) -> manifest_mod.PackageManifest:
    """Fill a staging directory with the package tree and return the manifest it was written from."""
    directories = ["vendor", "content/levels", "content/packs"]
    if platform == "linux":
        directories.append("installer")
    for directory in directories:
        (staging / directory).mkdir(parents=True, exist_ok=True)
    vendors = add_vendors(staging, cache, allow_download)
    files = []
    files += add_mod(staging, mod_source)
    files += add_levels(staging, levels_root, level_names)
    files += add_packs(staging, bundles_dir, packs_src, pack_platform, pack_names)
    if platform == "windows":
        add_windows_installer(staging, installer_binary)
    else:
        add_installer(staging)
        (staging / "install.sh").write_text(install_sh_content(), encoding="utf-8")
        (staging / "install.sh").chmod(0o755)
    melonloader_version = next(v["version"] for v in vendors if v["kind"] == "melonloader")
    manifest = manifest_mod.PackageManifest(
        schema=manifest_mod.PACKAGE_SCHEMA,
        platform=platform,
        package_id=PACKAGE_ID,
        mod_version=mod_version,
        melonloader_version=melonloader_version,
        game_buildid=GAME_BUILD_ID,
        generated=generated_stamp(),
        verified_on=(),
        vendors=tuple(manifest_mod.Vendor(**vendor) for vendor in vendors),
        files=tuple(manifest_mod.FileEntry(**entry) for entry in files),
    )
    manifest_mod.save_manifest(staging / PACKAGE_MANIFEST_NAME, manifest)
    return manifest


def build_package(
    output: Path,
    cache: Path = DEFAULT_CACHE,
    *,
    mod_dir: Path | None = None,
    levels_dir: Path | None = None,
    level_names: list[str] | None = None,
    bundles_dir: Path | None = None,
    packs_src: Path | None = None,
    pack_platform: str = "windows",
    pack_names: list[str] | None = None,
    allow_download: bool = False,
    mod_version: str = "dev",
    platform: str = "linux",
    installer_binary: Path | None = None,
) -> manifest_mod.PackageManifest:
    """Assemble the package at output, replacing it. Nothing is changed on failure."""
    if platform not in PLATFORMS:
        raise BuildError(f"Unknown package platform {platform!r}; expected one of {', '.join(PLATFORMS)}.")
    mod_source = mod_dir or MOD_OUTPUT_DIR
    check_mod_source(mod_source)
    if ASSET_WINDOWS != MELONLOADER_ASSET:
        raise BuildError(f"The MelonLoader pin names {ASSET_WINDOWS}, expected {MELONLOADER_ASSET}.")

    staging = output.parent / f".{output.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        record = assemble(
            staging,
            cache,
            mod_source,
            levels_dir if levels_dir is not None else DEFAULT_LEVELS_DIR,
            level_names or [],
            bundles_dir if bundles_dir is not None else DEFAULT_BUNDLES_DIR,
            packs_src if packs_src is not None else DEFAULT_PACKS_SRC,
            pack_platform,
            pack_names or [],
            allow_download,
            mod_version,
            platform,
            installer_binary,
        )
        if output.exists():
            shutil.rmtree(output)
        staging.rename(output)
    except OSError as exc:
        raise BuildError(f"Could not write {output}: {exc}") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return record


def make_zip(package_dir: Path, zip_path: Path) -> Path:
    """Write a deterministic zip of the package: sorted entries, fixed timestamps."""
    members = sorted(
        (p for p in package_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts),
        key=lambda p: p.relative_to(package_dir).as_posix(),
    )
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = zip_path.with_name(zip_path.name + ".part")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            info = zipfile.ZipInfo(member.relative_to(package_dir).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if member.name == "install.sh" else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, member.read_bytes())
    temporary.rename(zip_path)
    return zip_path


def package_zip_name(mod_version: str, melonloader_version: str, platform: str = "linux") -> str:
    return f"megabonk-levels-{mod_version}-ml{melonloader_version}-{platform}.zip"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Megabonk Levels player package.")
    parser.add_argument("--platform", choices=PLATFORMS, default="linux", help="Which player package to build.")
    parser.add_argument(
        "--installer-binary",
        type=Path,
        default=None,
        help="The windows/amd64 installer (task installer:build); required for --platform windows.",
    )
    parser.add_argument("--output", type=Path, default=REPO_ROOT / ".tools/player-package")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="Where vendor archives are kept.")
    parser.add_argument("--mod-dir", type=Path, default=None, help="Directory holding the built mod DLL.")
    parser.add_argument("--levels-dir", type=Path, default=None, help="Directory the named levels live in.")
    parser.add_argument(
        "--level",
        action="append",
        dest="levels",
        metavar="NAME",
        help="Bundle this level file, e.g. example-forest.mblevel.json. Repeatable; nothing is bundled by default.",
    )
    parser.add_argument(
        "--pack",
        action="append",
        dest="packs",
        metavar="ID",
        help="Bundle this level pack, e.g. thps. Repeatable; nothing is bundled by default.",
    )
    parser.add_argument("--bundles-dir", type=Path, default=None, help="Directory of built AssetBundles.")
    parser.add_argument("--packs-src", type=Path, default=None, help="Directory of pack manifests.")
    parser.add_argument(
        "--pack-platform",
        choices=("windows", "linux"),
        default="windows",
        help="Which built bundles to take. The game runs the Windows build, so windows is right on Linux too.",
    )
    parser.add_argument("--allow-download", action="store_true", help="Fetch missing vendor archives.")
    parser.add_argument("--skip-zip", action="store_true", help="Do not write the distributable zip.")
    parser.add_argument("--mod-version", default="dev", help="Version recorded in the manifest and zip name.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        record = build_package(
            args.output,
            cache=args.cache,
            mod_dir=args.mod_dir,
            levels_dir=args.levels_dir,
            level_names=args.levels,
            bundles_dir=args.bundles_dir,
            packs_src=args.packs_src,
            pack_platform=args.pack_platform,
            pack_names=args.packs,
            allow_download=args.allow_download,
            mod_version=args.mod_version,
            platform=args.platform,
            installer_binary=args.installer_binary,
        )
        zip_path = None
        if not args.skip_zip:
            zip_path = make_zip(
                args.output,
                args.output.parent / package_zip_name(record.mod_version, record.melonloader_version, args.platform),
            )
    except MissingInput as exc:
        warn(str(exc))
        return 3
    except BuildError as exc:
        warn(str(exc))
        return 1
    say(f"Package built at {args.output}")
    say(f"{record.label}: {len(record.files)} files, {len(record.vendors)} vendor archives.")
    if zip_path:
        say(f"Distributable written to {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
