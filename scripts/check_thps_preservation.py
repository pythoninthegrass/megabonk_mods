#!/usr/bin/env python3
"""Check the shipped Warehouse against its deliberately refreshed preservation baseline."""

import argparse
import build_thps_level as b
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVEL_PATH = ROOT / "levels/thps.mblevel.json"
BASELINE_PATH = ROOT / "tests/fixtures/thps-preservation.json"
PACK_ASSETS = Path("unity/pack-authoring/Assets/Thps")


def fingerprints(root: Path, paths: list[str]) -> dict:
    result = {}
    for name in sorted(paths):
        path = root / name
        if not path.is_file():
            result[name] = None
            continue
        data = path.read_bytes()
        result[name] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return result


def legacy_paths() -> list[str]:
    extraction = ROOT / ".tools/thps1/warehouse"
    source = [extraction / name for name in ("warehouse.obj", "warehouse.mtl", "warehouse_nodes.json")]
    textures = sorted(extraction.glob("*.png"))
    generated = [ROOT / PACK_ASSETS / name for name in ("Warehouse.prefab", "Warehouse.asset", "WarehouseCollision.asset", "04_Superman.mp3")]
    generated += sorted((ROOT / PACK_ASSETS).glob("Warehouse_*.mat"))
    generated += sorted((ROOT / PACK_ASSETS / "WarehouseTextures").glob("*.png"))
    paths = source + textures + generated + [Path(str(path) + ".meta") for path in generated]
    paths += [ROOT / "tools/ost/04 Superman.mp3", b.OVERRIDES_PATH]
    return sorted({path.relative_to(ROOT).as_posix() for path in paths})


def pack_inventory(manifest: dict, references: list[str]) -> dict:
    return {ref: "AudioClip" if ref == "bundle:thps/04_Superman" else ref.split("/", 1)[1] in manifest["assets"] for ref in references}


def snapshot(paths: list[str]) -> dict:
    for function in (b.obj_mesh, b.warehouse_triangles, b.anchored_collectibles, b.collectibles):
        function.cache_clear()
    text = LEVEL_PATH.read_bytes().decode("utf-8")
    level = json.loads(text)
    references = {level["music"]}
    references.update(json.loads(edit["payload"])["catalogId"] for edit in level["edits"] if edit["opType"] == "object.place")
    references = sorted(ref for ref in references if ref.startswith("bundle:"))
    manifest = json.loads(b.MANIFEST_PATH.read_text())
    return {
        "level": text,
        "derived": {
            "footprint": b.warehouse_footprint(),
            "placement": b.warehouse_placement()._asdict(),
            "bossSpawnPosition": b.boss_spawn_position(),
            "keptCells": b.kept_cells(),
            "copingRails": b.COPING_RAILS,
            "collectibles": [item._asdict() for item in b.collectibles()],
        },
        "pack": {"id": manifest["id"], "version": manifest["version"], "references": pack_inventory(manifest, references)},
        "assets": fingerprints(ROOT, paths),
    }


def differences(expected, actual, path: str = "") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(expected.keys() | actual.keys()):
            field = f"{path}.{key}" if path else key
            if key not in actual:
                result.append(f"{field}: missing")
            elif key not in expected:
                result.append(f"{field}: added")
            else:
                result.extend(differences(expected[key], actual[key], field))
        return result
    if isinstance(expected, list) and isinstance(actual, list):
        result = []
        for index in range(max(len(expected), len(actual))):
            field = f"{path}[{index}]"
            if index >= len(actual):
                result.append(f"{field}: missing")
            elif index >= len(expected):
                result.append(f"{field}: added")
            else:
                result.extend(differences(expected[index], actual[index], field))
        return result
    if expected == actual and type(expected) is type(actual):
        return []
    if path.endswith("level"):
        import difflib

        return [f"{path}: bytes changed\n" + "".join(difflib.unified_diff(expected.splitlines(keepends=True), actual.splitlines(keepends=True), fromfile="baseline", tofile=path))]
    return [f"{path}: {expected!r} -> {actual!r}"]


def regenerate() -> str:
    with tempfile.TemporaryDirectory(prefix="thps-preservation-") as directory:
        out = Path(directory) / "thps.mblevel.json"
        subprocess.run([sys.executable, str(ROOT / "scripts/build_thps_level.py"), str(out)], check=True, capture_output=True, text=True)
        return out.read_bytes().decode("utf-8")


def read_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text())


def check() -> list[str]:
    baseline = read_baseline()
    result = []
    try:
        actual = snapshot(sorted(set(baseline["assets"]) | set(legacy_paths())))
        actual = json.loads(json.dumps(actual))
        result.extend(differences(baseline, actual, "shipped"))
    except (OSError, ValueError, KeyError) as error:
        result.append(f"shipped snapshot failed: {error}")
        result.extend(differences(baseline["assets"], fingerprints(ROOT, list(baseline["assets"])), "assets"))
    try:
        result.extend(differences(baseline["level"], regenerate(), "generated.level"))
    except (OSError, subprocess.CalledProcessError) as error:
        result.append(f"generated.level failed: {error}\n{getattr(error, 'stderr', '')}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="acknowledge a shipped-level change and replace the baseline")
    args = parser.parse_args()
    if args.refresh:
        baseline = snapshot(legacy_paths())
        missing = [name for name, value in baseline["assets"].items() if value is None]
        if missing:
            parser.error("missing preservation inputs: " + ", ".join(missing))
        if regenerate() != baseline["level"]:
            parser.error("fresh generator output differs from the shipped level; refusing refresh")
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n")
        print(f"Refreshed {BASELINE_PATH.relative_to(ROOT)}: this acknowledges a shipped Warehouse change.")
        return 0
    changes = check()
    if changes:
        print("\n".join(changes))
        return 1
    print("Shipped Warehouse preservation baseline matches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
