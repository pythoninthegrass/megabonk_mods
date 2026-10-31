"""Where the installer's files live inside the game, what it validates before copying, and the record it leaves behind.

The game reads player levels from UserData/Levels and asset packs from
UserData/LevelPacks/<id>/ (docs/asset-bundles.md). The record file is what makes
uninstall safe: it names exactly what this installer placed, so nothing of the
player's own is touched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

USER_DATA = "UserData"
LEVELS_DIR_NAME = "Levels"
LEVEL_PACKS_DIR_NAME = "LevelPacks"
RUNTIME_SUBDIR = "dotnet6-win"
RECORD_NAME = "MegabonkLevels.installer.json"
LOADER_DIR = "MelonLoader"
MODS_DIR = "Mods"
USERLIBS_DIR = "UserLibs"
VERSION_MARKER_NAME = "MegabonkLevels.melonloader_version"
LEVEL_SUFFIXES = (".mblevel.json", ".level.json")
MANIFEST_NAME = "manifest.json"
ATTACHMENTS_NAME = "attachments.json"
ATTACHMENTS_SCHEMA = "pack-attachments/1"
PREFAB_SUFFIX = ".bundle"
PACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REQUIRED_MANIFEST_FIELDS = ("id", "name", "author", "version")
MAX_FILE_BYTES = 256 * 1024 * 1024


def user_data(game_dir: Path | str) -> Path:
    return Path(game_dir) / USER_DATA


def levels_dir(game_dir: Path | str) -> Path:
    return user_data(game_dir) / LEVELS_DIR_NAME


def level_packs_dir(game_dir: Path | str) -> Path:
    return user_data(game_dir) / LEVEL_PACKS_DIR_NAME


def pack_dest(game_dir: Path | str, pack_id: str) -> Path:
    return level_packs_dir(game_dir) / pack_id


def runtime_dir(game_dir: Path | str) -> Path:
    return Path(game_dir) / RUNTIME_SUBDIR


def version_marker(game_dir: Path | str) -> Path:
    return Path(game_dir) / LOADER_DIR / VERSION_MARKER_NAME


def record_path(game_dir: Path | str) -> Path:
    return Path(game_dir) / RECORD_NAME


def load_record(game_dir: Path | str) -> dict | None:
    path = record_path(game_dir)
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def save_record(game_dir: Path | str, record: dict) -> Path:
    path = record_path(game_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def clear_record(game_dir: Path | str) -> None:
    record_path(game_dir).unlink(missing_ok=True)


def installed_loader_version(game_dir: Path | str) -> str | None:
    marker = version_marker(game_dir)
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8", errors="replace").strip()


def is_bundle_name(name: str) -> bool:
    """Pack bundles are built without an extension; .bundle is the explicit form (pack_catalog.cs)."""
    return Path(name).suffix in ("", PREFAB_SUFFIX)


def pack_files(source: Path | str) -> list[Path]:
    """The files that make up a pack: its manifest, the optional attachments sidecar, and its bundles."""
    source = Path(source)
    if not source.is_dir():
        return []
    files = []
    for name in (MANIFEST_NAME, ATTACHMENTS_NAME):
        candidate = source / name
        if candidate.is_file():
            files.append(candidate)
    files.extend(sorted(child for child in source.iterdir() if child.is_file() and is_bundle_name(child.name) and child not in files))
    return files


def validate_level_file(path: Path | str) -> list[str]:
    """What the level file must satisfy to be worth installing."""
    path = Path(path)
    if not path.exists():
        return [f"{path}: no such file"]
    if not path.is_file():
        return [f"{path}: not a file"]
    problems: list[str] = []
    if not path.name.endswith(LEVEL_SUFFIXES):
        problems.append(f"{path.name}: expected a {LEVEL_SUFFIXES[0]} file")
    if path.stat().st_size > MAX_FILE_BYTES:
        problems.append(f"{path.name}: larger than the {MAX_FILE_BYTES // (1024 * 1024)}MB limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return problems + [f"{path.name}: cannot be read as text: {exc}"]
    except json.JSONDecodeError as exc:
        return problems + [f"{path.name}: invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        problems.append(f"{path.name}: the top level must be a JSON object")
    elif "schema" in payload and not isinstance(payload["schema"], int):
        problems.append(f"{path.name}: 'schema' must be an integer")
    return problems


def validate_pack_source(source: Path | str) -> list[str]:
    """Check a pack directory the way the game will, so a broken pack never reaches the Warehouse."""
    source = Path(source)
    if not source.exists():
        return [f"{source}: no such directory"]
    if not source.is_dir():
        return [f"{source}: not a directory"]

    problems: list[str] = []
    manifest_path = source / MANIFEST_NAME
    pack_id = source.name
    if not manifest_path.is_file():
        problems.append(f"{source}/{MANIFEST_NAME}: a pack directory needs a {MANIFEST_NAME}")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return problems + [f"{MANIFEST_NAME}: {exc}"]
        if not isinstance(manifest, dict):
            return problems + [f"{MANIFEST_NAME}: the top level must be a JSON object"]
        for field in REQUIRED_MANIFEST_FIELDS:
            value = manifest.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{MANIFEST_NAME}: missing required string field '{field}'")
        assets = manifest.get("assets")
        if not isinstance(assets, list) or not all(isinstance(asset, str) for asset in assets or []):
            problems.append(f"{MANIFEST_NAME}: missing required array field 'assets'")
        declared = manifest.get("id")
        if isinstance(declared, str) and declared.strip() and declared.strip() != pack_id:
            problems.append(f"{MANIFEST_NAME}: manifest id '{declared}' does not match its pack folder '{pack_id}'")
        attachments = manifest.get("attachments")
        if attachments is not None and not isinstance(attachments, str):
            problems.append(f"{MANIFEST_NAME}: 'attachments' must be a string when present")

    if not PACK_ID_PATTERN.match(pack_id):
        problems.append(f"pack folder name '{pack_id}': use a lowercase id of a-z, 0-9, '.', '_' or '-'")

    bundles = [child for child in source.iterdir() if child.is_file() and is_bundle_name(child.name) and child.suffix == PREFAB_SUFFIX] or [
        child
        for child in source.iterdir()
        if child.is_file() and child.suffix == "" and child.name not in {MANIFEST_NAME, ATTACHMENTS_NAME}
    ]
    if not bundles:
        problems.append(f"{source}: no AssetBundle file — expected the bundle named after the pack id (or a .bundle file)")

    sidecar = source / ATTACHMENTS_NAME
    if sidecar.is_file():
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{ATTACHMENTS_NAME}: {exc}")
        else:
            if not isinstance(payload, dict) or payload.get("schema") != ATTACHMENTS_SCHEMA:
                problems.append(f"{ATTACHMENTS_NAME}: expected a {ATTACHMENTS_SCHEMA} document")

    for file in source.rglob("*"):
        if file.is_file() and file.stat().st_size > MAX_FILE_BYTES:
            problems.append(f"{file.relative_to(source)}: larger than the {MAX_FILE_BYTES // (1024 * 1024)}MB limit")
    return problems


def describe_record(record: dict) -> list[str]:
    """Human-readable lines describing an install record, for --check and uninstall output."""
    lines = [
        f"package {record.get('package_id', 'unknown')}",
        f"mod {record.get('mod_version', '?')} / MelonLoader {record.get('melonloader_version', '?')}",
    ]
    if record.get("installed_at"):
        lines.append(f"installed {record['installed_at']}")
    runtime = record.get("runtime") or {}
    if runtime:
        lines.append(f".NET {runtime.get('version', '?')} in {runtime.get('mode', '?')} at {runtime.get('path', '?')}")
    override = record.get("dll_override") or {}
    if override:
        if override.get("applied"):
            lines.append(f"version.dll override: {override.get('value', '?')} via {override.get('via') or 'unknown'}")
        else:
            lines.append("version.dll override: not set")
    lines.append(f"{len(record.get('files', []))} mod file(s)")
    packs = record.get("packs") or {}
    if packs:
        lines.append("packs: " + ", ".join(sorted(packs)))
    levels = record.get("levels") or []
    if levels:
        lines.append(f"{len(levels)} level file(s)")
    return lines
