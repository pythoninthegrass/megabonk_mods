import importlib
import json
from collections import deque
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def starter():
    return importlib.import_module("build_starter_level")


def edges(cell):
    height = cell["height"]
    slope = cell.get("slope")
    directions = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
    if not slope:
        return dict.fromkeys(directions.values(), height)
    dx, dz = directions[slope]
    return {(dx, dz): height + 1, (-dx, -dz): height}


def test_starter_is_native_forest_with_stock_rules():
    level = starter().build_level()
    assert (level["schemaVersion"], level["baseline"], level["map"], level["stageIndex"], level["tier"]) == (4, "none", 1, 0, 0)
    assert level["title"] == "Mosswatch Hollow"
    assert level["packs"] == {}
    assert not any(key in level for key in ("music", "allowedCharacters", "maxSlopeAngle", "fallDamageCharacter"))
    assert all(edit["opType"] == "object.place" for edit in level["edits"])
    assert all(not json.loads(edit["payload"])["catalogId"].startswith("bundle:") for edit in level["edits"])


def test_every_tile_is_walkable_from_spawn_without_jumping():
    level = starter().build_level()
    grid = level["grid"]
    assert (grid["width"], grid["depth"], len(grid["cells"])) == (11, 11, 121)
    cells = {(cell["x"], cell["z"]): cell for cell in grid["cells"]}
    assert len(cells) == 121
    assert {cell["height"] for cell in cells.values()} == {0, 1, 2}
    assert sum("slope" in cell for cell in cells.values()) >= 10
    start = starter().SPAWN_CELL
    visited = {start}
    queue = deque([start])
    while queue:
        x, z = queue.popleft()
        for (dx, dz), height in edges(cells[x, z]).items():
            target = (x + dx, z + dz)
            if target in cells and target not in visited and edges(cells[target]).get((-dx, -dz)) == height:
                visited.add(target)
                queue.append(target)
    assert visited == set(cells), f"Unreachable cells: {set(cells) - visited}"


def test_landmarks_and_rewards_have_ground_support():
    module = starter()
    level = module.build_level()
    cells = {(cell["x"], cell["z"]): cell for cell in level["grid"]["cells"]}
    positions = [level["spawn"]["position"], level["bossSpawner"]["position"]]
    payloads = [json.loads(edit["payload"]) for edit in level["edits"]]
    positions += [list(payload["position"].values()) for payload in payloads]
    for x, y, z in positions:
        cell = cells[round(x / 40 + 5), round(z / 40 + 5)]
        assert "slope" not in cell
        assert abs(y - cell["height"] * 20) <= 3
    ids = [payload["catalogId"] for payload in payloads]
    assert ids.count("interactable/chest") >= 6
    assert ids.count("interactable/chestFree") == 1
    assert len(level["shrineSpots"]) >= 6
    assert level["guaranteedShrineKinds"] == ["charge", "charge"]
    targets = [edit["target"] for edit in level["edits"]]
    assert targets[0] == "placement:0"
    assert len(targets) == len(set(targets))


def test_imported_vegetation_keeps_its_native_upright_rotation():
    module = starter()
    payloads = [json.loads(edit["payload"]) for edit in module.build_level()["edits"]]
    vegetation = [payload for payload in payloads if payload["catalogId"] in (module.TREE, module.LOG, module.BUSH)]
    assert vegetation
    assert all(payload["rotation"]["x"] == 270 for payload in vegetation)


def test_checked_in_level_matches_builder():
    assert json.loads((ROOT / "levels/mosswatch-hollow.mblevel.json").read_text()) == starter().build_level()


def test_original_selection_art_is_reproducible_and_small(tmp_path):
    starter().write_assets(tmp_path)
    for name, size in (("mosswatch-hollow.png", (1080, 720)), ("mosswatch-hollow.biome.png", (256, 256))):
        generated = tmp_path / name
        shipped = ROOT / "levels" / name
        with Image.open(generated) as image:
            assert image.size == size
            assert image.mode == "RGB"
        assert generated.read_bytes() == shipped.read_bytes()
        assert generated.stat().st_size < 1024 * 1024
