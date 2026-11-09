"""Generate the separate editable Warehouse without touching the shipped level."""

import argparse
import build_thps_level as legacy
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "unity/pack-authoring/packs/thps"
OUTPUT = ROOT / "levels/thps-editable.mblevel.json"


def read_inputs():
    return json.loads((PACK / "pieces.json").read_text()), json.loads((PACK / "attachments.json").read_text())


def vector(values):
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError("piece transforms require three finite coordinates")
    return dict(zip("xyz", values, strict=True))


def piece_edits(pieces, defaults):
    if pieces.get("schema") != "thps-pieces/1" or defaults.get("schema") != "pack-attachments/1":
        raise ValueError("unsupported piece or attachment schema")
    entries = pieces["pieces"]
    by_asset = {piece["asset"]: piece for piece in entries}
    if len(by_asset) != len(entries):
        raise ValueError("duplicate piece asset")
    scale = pieces["meshToWorld"]["scale"]
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("invalid meshToWorld scale")
    assets = defaults["instances"]
    supports = set()
    for owner, children in assets.items():
        if owner not in by_asset or by_asset[owner]["module"] == "suppressed-post":
            raise ValueError(f"missing attachment owner {owner}")
        names = set()
        for child in children:
            if child["name"] in names:
                raise ValueError(f"duplicate attachment name on {owner}")
            names.add(child["name"])
            for field in ("position", "rotation", "scale"):
                vector([child["localTransform"][field][axis] for axis in "xyz"])
            if any(child["localTransform"]["scale"][axis] <= 0 for axis in "xyz"):
                raise ValueError(f"nonpositive attachment scale on {owner}")
            if child["catalogId"].startswith("bundle:thps/"):
                support = child["sourceInstance"]
                if support not in by_asset or support in supports or support in assets or child["catalogId"] != f"bundle:thps/{by_asset[support]['catalogAsset']}":
                    raise ValueError(f"missing, duplicate or nested support {support}")
                supports.add(support)
    edits, next_id = [], 0
    for piece in entries:
        position = vector(piece["position"])
        if not math.isfinite(piece["yaw"]):
            raise ValueError("nonfinite piece yaw")
        asset = piece["asset"]
        if piece["module"] == "suppressed-post" or asset in supports:
            continue
        children = [
            {key: copy.deepcopy(child[key]) for key in ("name", "catalogId", "localTransform", "hidden")}
            for child in assets.get(asset, [])
        ]
        payload = {
            "catalogId": f"bundle:thps/{piece['catalogAsset']}",
            "position": position,
            "rotation": vector(piece["rotation"]),
            "scale": vector(piece["scale"]),
            "placementId": next_id,
        }
        if children:
            payload["attachments"] = children
        edits.append(legacy.edit("object.place", payload))
        next_id += 1 + len(children)
    return edits


def build_level():
    level = legacy.build_level()
    level["title"] = "Warehouse — Editable"
    manifest = json.loads((PACK / "manifest.json").read_text())
    level["packKitVersions"] = {"thps": manifest["kitVersion"]}
    pieces, defaults = read_inputs()
    kit_assets = {asset for asset in manifest["assets"] if any(asset.startswith(prefix) for prefix in manifest["kitAssetPrefixes"])}
    if {piece["catalogAsset"] for piece in pieces["pieces"] if piece["catalogAsset"]} != kit_assets:
        raise ValueError("manifest kit assets and pieces.json disagree")
    level["edits"] = piece_edits(pieces, defaults) + legacy.radio_edits() + legacy.collectible_edits()
    return level


def write_level(path):
    path = Path(path)
    if path.resolve() == (ROOT / "levels/thps.mblevel.json").resolve():
        raise ValueError("refusing to overwrite the shipped Warehouse")
    path.write_text(json.dumps(build_level(), indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", nargs="?", type=Path, default=OUTPUT)
    args = parser.parse_args()
    write_level(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
