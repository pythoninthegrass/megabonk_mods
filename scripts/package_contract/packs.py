"""What the package builder checks about a pack before bundling it, and the folder names a package puts content under.

The game reads player levels from UserData/Levels and asset packs from
UserData/LevelPacks/<id>/ (docs/asset-bundles.md). Standard library only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LEVELS_DIR_NAME = "Levels"
LEVEL_PACKS_DIR_NAME = "LevelPacks"
MANIFEST_NAME = "manifest.json"
ATTACHMENTS_NAME = "attachments.json"
ATTACHMENTS_SCHEMA = "pack-attachments/1"
PREFAB_SUFFIX = ".bundle"
PACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REQUIRED_MANIFEST_FIELDS = ("id", "name", "author", "version")
MAX_FILE_BYTES = 256 * 1024 * 1024


def is_bundle_name(name: str) -> bool:
    """Pack bundles are built without an extension; .bundle is the explicit form (pack_catalog.cs)."""
    return Path(name).suffix in ("", PREFAB_SUFFIX)


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
