#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Record the collectibles rearranged in the editor so build_thps_level.py reproduces them.

Reads a level saved from the editor (a generated level plus the MoveObject edits the editor appended), takes the last move of each collectible placement, and writes the ones that differ from the anchored transform to scripts/thps_item_overrides.json.
"""

import argparse
import build_thps_level as b
import json
from pathlib import Path

ROTATION_DECIMALS = 4
POSITION_DECIMALS = 4
SAME_TOLERANCE = 1e-3


def clean(value: float, decimals: int) -> float | int:
    rounded = round(value, decimals)
    return 0 if rounded == 0 else int(rounded) if rounded == int(rounded) else rounded


def overrides_from_level(level: dict) -> dict[str, dict]:
    first = len(b.mesh_rail_edits()) + len(b.warehouse_edits())
    items = b.anchored_collectibles()
    by_target = {f"placement:{first + i}": c for i, c in enumerate(items)}
    final: dict[str, dict] = {}
    for e in level["edits"]:
        if e["target"] not in by_target:
            continue
        if e["opType"] == "object.remove":
            raise ValueError(f"the saved level removes {by_target[e['target']].code}; overrides cannot express that")
        if e["opType"] == "object.move":
            final[e["target"]] = json.loads(e["payload"])["newTransform"]
    overrides = {}
    for target, transform in final.items():
        c = by_target[target]
        p, r = transform["position"], transform["rotation"]
        position = [clean(p[k], POSITION_DECIMALS) for k in "xyz"]
        rotation = [clean(r[k], ROTATION_DECIMALS) for k in "xyz"]
        same = all(abs(a - v) <= SAME_TOLERANCE for a, v in zip(position + rotation, [c.x, c.y, c.z, *c.euler], strict=True))
        if not same:
            overrides[c.code] = {"position": position, "rotation": rotation}
    return overrides


def write_overrides(overrides: dict[str, dict], path: Path) -> None:
    path.write_text(json.dumps(overrides, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("saved", type=Path, help="level saved from the editor, e.g. <game>/UserData/Levels/thps.mblevel.json")
    parser.add_argument("out", nargs="?", type=Path, default=b.OVERRIDES_PATH)
    args = parser.parse_args()
    overrides = overrides_from_level(json.loads(args.saved.read_text()))
    write_overrides(overrides, args.out)
    print(f"wrote {len(overrides)} overrides to {args.out}")


if __name__ == "__main__":
    main()
