import build_thps_attachments as attachments
import build_thps_level as legacy
import json
import math
import pytest
from warehouse_surface import euler_matrix


def test_split_path_preserves_endpoints_and_seam_without_overlaps():
    segments = attachments.split_path((0, 2, 0), (30, 2, 0), [10, 20], axis=0)
    assert segments == [((0, 2, 0), (10, 2, 0)), ((10, 2, 0), (20, 2, 0)), ((20, 2, 0), (30, 2, 0))]
    with pytest.raises(ValueError, match="short"):
        attachments.split_path((0, 0, 0), (10, 0, 0), [2], axis=0)


def test_local_attachment_transform_reconstructs_world_rail_endpoints():
    owner = {"position": [10, 2, 30], "yaw": 90}
    position, yaw, scale, pitch = legacy.rail_along((20, 8, 40), (40, 8, 40))
    local = attachments.local_transform(owner, position, (0, yaw, pitch), scale)
    world = attachments.world_transform(owner, local)
    assert world["position"] == pytest.approx(position)
    assert world["scale"] == pytest.approx([scale] * 3)
    for actual, expected in zip(world["rotation"], [0, yaw, pitch], strict=True):
        assert (actual - expected + 180) % 360 - 180 == pytest.approx(0, abs=1e-9)


def test_generated_metadata_is_committed_and_reproducible():
    built = attachments.build()
    assert json.loads(attachments.OUTPUT.read_text()) == built
    assert built["schema"] == "pack-attachments/1"
    assert "Warehouse" not in built["assets"]
    assert all(entry for entry in built["assets"].values())


def test_all_legacy_paths_have_one_owner_per_subpath_and_no_short_segments():
    data = attachments.build()
    paths = [child for children in data["assets"].values() for child in children if child["hidden"]]
    assert {child["name"].split("/")[0] for child in paths} == {
        *[f"added-grind-mesh-{i}" for i in range(4)],
        *[f"added-grind-coping-{i}" for i in range(len(legacy.COPING_LIPS))],
    }
    assert len({child["name"] for child in paths}) == len(paths)
    for child in paths:
        length = math.dist(child["start"], child["end"])
        assert length > 3.5, child["name"]
        assert child["catalogId"] == "interactable/rail/0"
    for i, (start, end) in enumerate(legacy.COPING_LIPS):
        segments = [p for p in paths if p["name"].split("/")[0] == f"added-grind-coping-{i}"]
        assert segments[0]["start"] == pytest.approx(start)
        assert segments[-1]["end"] == pytest.approx(end)
        for a, b in zip(segments, segments[1:]):
            assert a["end"] == b["start"]


def test_posts_are_owned_once_by_their_bar_with_original_world_transform():
    data = attachments.build()
    pieces = json.loads(attachments.PIECES.read_text())["pieces"]
    records = {entry["asset"]: entry for entry in pieces}
    found = []
    for owner, children in data["instances"].items():
        names = [child["name"] for child in children]
        assert len(names) == len(set(names))
        for child in children:
            if not child["name"].startswith("added-post-"):
                continue
            found.append(child["name"])
            world = attachments.world_transform(records[owner], child["localTransform"])
            assert world["position"] == pytest.approx(records[child["name"]]["position"])
            assert world["scale"] == pytest.approx(records[child["name"]]["scale"])
            n = int(child["name"].rsplit("-", 1)[1])
            assert owner == ("piece-rail-big-straight" if n < 5 else "piece-rail-big-bend" if n < 7 else "piece-rail-deck")
    assert sorted(found) == [f"added-post-{i}" for i in range(10)]


def test_every_local_grind_path_reconstructs_its_world_endpoints_on_its_owner():
    data = attachments.build()
    records = {piece["asset"]: piece for piece in json.loads(attachments.PIECES.read_text())["pieces"]}
    bounds = attachments.source_bounds()
    for owner, children in data["instances"].items():
        for child in children:
            if not child["hidden"]:
                continue
            world = attachments.world_transform(records[owner], child["localTransform"])
            rotation = euler_matrix(*world["rotation"])
            scale = world["scale"][0]
            centre = [world["position"][k] + rotation[k][1] * legacy.RAIL0_BAR_HEIGHT * scale for k in range(3)]
            for sign, endpoint in zip((-1, 1), (child["start"], child["end"]), strict=True):
                actual = [centre[k] + sign * rotation[k][0] * legacy.RAIL0_LENGTH * scale / 2 for k in range(3)]
                assert actual == pytest.approx(endpoint, abs=1e-6), child["name"]
                for axis in range(3):
                    low, high = bounds[owner][axis]
                    assert low - 0.2 <= endpoint[axis] <= high + 0.2, (owner, child["name"])
