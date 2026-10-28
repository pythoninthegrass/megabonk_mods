"""
Self-test for scripts/extract_thps_item_overrides.py.
"""

import build_thps_level as b
import extract_thps_item_overrides as x
import json
import pytest

needs_extract = pytest.mark.skipif(
    not (b.NODES_PATH.exists() and b.OBJ_PATH.exists()), reason="needs the extraction under .tools/thps1/warehouse"
)


def move(placement: int, position: tuple, rotation: tuple = (270.0, 0.0, 0.0)) -> dict:
    transform = {
        "position": dict(zip("xyz", position, strict=True)),
        "rotation": dict(zip("xyz", rotation, strict=True)),
        "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
    }
    return b.edit("object.move", {"newTransform": transform}, f"placement:{placement}")


def saved_level(extra: list[dict]) -> dict:
    return {**b.build_level(), "edits": [*b.build_level()["edits"], *extra]}


def first_item_placement() -> int:
    return len(b.mesh_rail_edits()) + len(b.warehouse_edits())


@needs_extract
def test_the_last_move_of_a_placement_becomes_its_override() -> None:
    first = first_item_placement()
    level = saved_level([move(first + 3, (1, 2, 3)), move(first + 3, (4, 5, 6), (270, 90, 0))])
    assert x.overrides_from_level(level) == {b.collectibles()[3].code: {"position": [4, 5, 6], "rotation": [270, 90, 0]}}


@needs_extract
def test_a_move_back_to_the_anchored_transform_is_not_an_override() -> None:
    c = b.collectibles()[0]
    first = first_item_placement()
    level = saved_level([move(first, (1, 2, 3)), move(first, (c.x, c.y, c.z), c.euler)])
    assert x.overrides_from_level(level) == {}


@needs_extract
def test_float_noise_in_a_saved_rotation_is_cleaned() -> None:
    level = saved_level([move(first_item_placement(), (1, 2, 3), (-1.6e-43, 240.50081234, 1.6e-43))])
    assert next(iter(x.overrides_from_level(level).values()))["rotation"] == [0, 240.5008, 0]


@needs_extract
def test_moves_of_other_placements_are_ignored() -> None:
    assert x.overrides_from_level(saved_level([move(0, (1, 2, 3)), move(first_item_placement() - 1, (1, 2, 3))])) == {}


@needs_extract
def test_removing_a_collectible_is_refused() -> None:
    level = saved_level([b.edit("object.remove", {}, f"placement:{first_item_placement()}")])
    with pytest.raises(ValueError, match="removes"):
        x.overrides_from_level(level)


def test_write_overrides_round_trips_through_the_generator_loader(tmp_path) -> None:
    path = tmp_path / "overrides.json"
    x.write_overrides({"K": {"position": [1, 2, 3], "rotation": [270, 0, 0]}}, path)
    assert json.loads(path.read_text()) == {"K": {"position": [1, 2, 3], "rotation": [270, 0, 0]}}
    assert b.load_overrides(path) == {"K": {"position": [1, 2, 3], "rotation": [270, 0, 0]}}
