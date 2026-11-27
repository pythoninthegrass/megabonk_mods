import conker_colors as colors
import hashlib
import json
import math
import pytest
import struct
import warehouse_surface as ws


def test_verify_rom_rejects_wrong_bytes(tmp_path, monkeypatch):
    rom = tmp_path / "game.z64"
    rom.write_bytes(b"fixture")
    monkeypatch.setattr(colors, "ROM_SHA256", hashlib.sha256(b"fixture").hexdigest())
    colors.verify_rom(rom)
    rom.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="US retail"):
        colors.verify_rom(rom)


def test_collision_uses_the_same_reflection_and_scale_as_level_points():
    triangle = [[[0, 4, 0], [0, 4, 8], [8, 4, 0]], "0x00"]
    runs = [{"layer": "terrain", "triangles": [triangle]}]
    vertices, indices = colors.collision_mesh(runs, (4, 4, 4), 0.5)
    assert vertices == [[-2, 0, 2], [-2, 0, -2], [2, 0, 2]]
    assert indices == [0, 2, 1]
    assert colors.world_point([8, 4, 0], (4, 4, 4), 0.5) == vertices[2]


def test_floor_selection_rejects_walls_ceilings_and_upper_walkways():
    terrain = [
        ([[0, 0, 0], [0, 0, 8], [8, 0, 0]], None),
        ([[0, 3, 0], [8, 3, 0], [0, 3, 8]], None),
        ([[0, 9, 0], [0, 9, 8], [8, 9, 0]], None),
        ([[0, 0, 0], [0, 6, 0], [0, 0, 8]], None),
    ]
    assert colors.floor_height(terrain, (2, 4, 2)) == 0
    assert colors.floor_height(terrain, (2, 10, 2)) == 9
    assert colors.floor_height(terrain, (20, 10, 20)) is None


def test_render_primitive_applies_model_matrix_and_shared_world_transform():
    data = struct.pack("<9f6f12B3I", 0, 0, 0, 0, 0, 8, 8, 0, 0, 0, 0, 0, 0.5, 2, 1, *range(12), 0, 1, 2)
    gltf = {
        "bufferViews": [{"byteOffset": offset} for offset in (0, 36, 60, 72)],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC2"},
            {"bufferView": 2, "componentType": 5121, "count": 3, "type": "VEC4", "normalized": True},
            {"bufferView": 3, "componentType": 5125, "count": 3, "type": "SCALAR"},
        ],
    }
    primitive = {"attributes": {"POSITION": 0, "TEXCOORD_0": 1, "COLOR_0": 2}, "indices": 3, "material": 2}
    matrix = [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 4, 4, 4, 1]
    result = colors.render_primitive(gltf, data, primitive, matrix, (4, 4, 4), 0.5)
    assert result["positions"] == [0, 0, 0, 0, 0, -8, 8, 0, 0]
    assert result["indices"] == [0, 2, 1]
    assert result["uv"] == [0, 1, 0, 0.5, 2, 0]
    assert result["rgba"] == list(range(12))
    assert result["material"] == 2


def test_local_arena_places_stock_loot_on_floors_along_the_route():
    source = colors.WORK / "export/maps/30"
    if not (source / "spawns.json").exists():
        pytest.skip("Run task conker:extract to create the local Colors fixture")
    runs = json.loads((source / "collision.json").read_text())
    spawns = json.loads((source / "spawns.json").read_text())
    level = colors.make_level(runs, spawns, {"version": "1.0.0"})
    edits = [json.loads(edit["payload"]) for edit in level["edits"]]
    loot = [edit for edit in edits if edit["catalogId"].startswith("interactable/chest")]
    assert len(loot) >= 5
    assert any(edit["catalogId"] == "interactable/chestFree" for edit in loot)
    assert all(edit["rotation"]["x"] == 270 for edit in loot)
    zs = [edit["position"]["z"] for edit in loot]
    assert min(zs) < -100 < 0 < max(zs)
    assert level["extraShrines"] >= 2
    assert len(level["shrineSpots"]) >= level["extraShrines"]
    assert "shadyGuy" in level["guaranteedShrineKinds"]
    assert level["strictShrineSpots"]
    assert len(level["powerupSpots"]) >= 4
    assert level["randomizePlacementsEachRun"]
    assert level["pitRecoveryDamage"] > 0
    assert level["killFloorY"] < -34
    assert len(level["minibossGroundSpots"]) >= 4
    assert level["extraShrinesMax"] == 3
    assert level["extraShrineKinds"] == ["charge"]
    assert {"magnet", "challenge", "cursed", "moai"} <= set(level["guaranteedShrineKinds"])
    assert level["shrineKindRanges"]["microwave"] == [0, 1]
    assert level["chestLuckRange"] == [-0.5, 2.0]
    assert "scale" not in level["bossSpawner"]
    assert "BottomPiece" in level["bossSpawner"]["hiddenChildren"]
    assert "Collider" not in level["bossSpawner"]["hiddenChildren"]
    assert {tuple(spot) for spot in level["powerupSpots"]}.isdisjoint(map(tuple, level["shrineSpots"]))
    terrain = [
        tuple(tuple(colors.world_point(point, colors.ORIGIN, colors.SCALE)) for point in face)
        for run in runs
        for face, _surface in run["triangles"]
    ]
    for x, y, z in level["shrineSpots"]:
        assert not ws.box_hits(terrain, (x, y + 4.25, z), ws.IDENTITY, (4.6, 3.75, 4.6))


def test_local_arena_clears_tall_players_and_catches_the_pit():
    source = colors.WORK / "export/maps/30"
    if not (source / "collision.json").exists():
        pytest.skip("Run task conker:extract to create the local Colors fixture")
    runs = json.loads((source / "collision.json").read_text())
    spawns = json.loads((source / "spawns.json").read_text())
    level = colors.make_level(runs, spawns, {"version": "1.0.0"})
    triangles = [face for run in runs for face in run["triangles"]]
    ceilings = [((a, c, b), surface) for (a, b, c), surface in triangles]
    for index in (2, 3, 4, 5, 6, 7, 8, 9, 12):
        x, y, z = spawns[index]["position"]
        floor = colors.floor_height(triangles, (x, y + 50, z))
        roof = colors.floor_height(ceilings, (x, floor + 650, z))
        assert (roof - floor) * colors.SCALE >= 10
    pit = colors.world_point((-850, -2404, -1950), colors.ORIGIN, colors.SCALE)
    assert level["killFloorY"] < pit[1] < level["bossSpawner"]["position"][1]
    assert (
        colors.floor_height([face for run in colors.arena_collision(runs) for face in run["triangles"]], (-850, -2100, -1950))
        is None
    )


def test_local_arena_does_not_import_conkers_pickup_models():
    source = colors.WORK / "export/maps/30"
    if not (source / "level.gltf").exists():
        pytest.skip("Run task conker:extract to create the local Colors fixture")
    runs = json.loads((source / "collision.json").read_text())
    meshes = colors.unpack_map(source, runs)["meshes"]
    assert [mesh["name"] for mesh in meshes] == ["04-30-00", "04-30-01", "PitBackdrop"]


def _covers(wall, x, z):
    """Whether a wall box's plan footprint holds the point x and z, allowing for its yaw."""
    depth = (math.sin(math.radians(wall["yaw"])), math.cos(math.radians(wall["yaw"])))
    along = (-depth[1], depth[0])
    shift = (x - wall["center"][0], z - wall["center"][2])
    length, thickness = wall["size"][0] / 2, wall["size"][2] / 2
    return (
        abs(shift[0] * along[0] + shift[1] * along[1]) <= length and abs(shift[0] * depth[0] + shift[1] * depth[1]) <= thickness
    )


def test_boundary_walls_trace_notches_and_stop_at_the_surface():
    outline = [(-100, -200), (100, -200), (100, -100), (60, -50), (60, 50), (100, 100), (100, 200), (-100, 200)]
    top, skirt = [], []
    for (ax, az), (bx, bz) in zip(outline, outline[1:] + outline[:1], strict=True):
        top.append(((-20, 20, -30), (ax, 20, az), (bx, 20, bz)))
        skirt.extend(
            (
                ((ax, 20, az), (bx, 20, bz), (bx * 1.05, -40, bz * 1.05)),
                ((ax, 20, az), (bx * 1.05, -40, bz * 1.05), (ax * 1.05, -40, az * 1.05)),
            )
        )
    barrier = colors.perimeter([*top, *skirt], max_slope_degrees=45)
    assert len(barrier) >= 8
    assert all(-8 <= wall["center"][1] - wall["size"][1] / 2 <= 20 for wall in barrier)
    assert all(wall["center"][1] + wall["size"][1] / 2 == pytest.approx(1020) for wall in barrier)
    assert not any(wall["center"][0] > 102 and -60 < wall["center"][2] < 60 for wall in barrier)
    assert any(wall["center"][0] < 70 and abs(wall["center"][2]) < 60 for wall in barrier)


def test_boundary_walls_fence_only_the_ground_the_player_can_reach():
    plateau = [((0, 20, 0), (40, 20, 0), (40, 20, 40)), ((0, 20, 0), (40, 20, 40), (0, 20, 40))]
    island = [((200, 20, 0), (240, 20, 0), (240, 20, 40)), ((200, 20, 0), (240, 20, 40), (200, 20, 40))]
    fenced = colors.perimeter([*plateau, *island], seeds={(10, 10)})
    assert any(wall["center"][0] < 40 for wall in fenced)
    assert not any(198 <= wall["center"][0] <= 242 for wall in fenced)


def test_boundary_walls_follow_the_outer_rim_past_the_bridge():
    source = colors.WORK / "export/maps/30"
    if not (source / "collision.json").exists():
        pytest.skip("Run task conker:extract to create the local Colors fixture")
    runs = json.loads((source / "collision.json").read_text())
    faces = [
        tuple(colors.world_point(point, colors.ORIGIN, colors.SCALE) for point in points)
        for run in runs
        for points, _surface in run["triangles"]
    ]
    walls = colors.perimeter(faces)

    for x in (-62, -60, -58):
        for z in range(98, 107, 2):
            assert not any(_covers(wall, x, z) for wall in walls), (x, z)

    for z in range(100, 111, 2):
        assert any(wall["center"][0] <= -88 and _covers(wall, wall["center"][0], z) for wall in walls), z


def test_boundary_walls_cover_the_terrain_border_and_straddle_the_surface():
    source = colors.WORK / "export/maps/30"
    if not (source / "collision.json").exists():
        pytest.skip("Run task conker:extract to create the local Colors fixture")
    runs = json.loads((source / "collision.json").read_text())
    faces = [
        tuple(colors.world_point(point, colors.ORIGIN, colors.SCALE) for point in points)
        for run in runs
        for points, _surface in run["triangles"]
    ]
    cells = colors.playable_cells(faces, max_slope_degrees=90)
    walls = colors.perimeter(faces)
    assert len(walls) >= 20
    assert walls == colors.perimeter(faces[::-1])

    open_air = colors._beyond(cells)
    ceiling = max(point[1] for face in faces for point in face) + 1000
    for (i, j), height in cells.items():
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (i + di, j + dj) not in open_air:
                continue
            x, z = (i + 0.5 + di / 2) * colors.CELL_SIZE, (j + 0.5 + dj / 2) * colors.CELL_SIZE
            half = colors.CELL_SIZE / 2
            assert any(
                _covers(wall, x - dj * half, z - di * half)
                and _covers(wall, x + dj * half, z + di * half)
                and wall["center"][1] - wall["size"][1] / 2 <= height
                and wall["center"][1] + wall["size"][1] / 2 == pytest.approx(ceiling)
                for wall in walls
            ), ((i, j), height, (di, dj))

    for wall in walls:
        x, y, z = wall["center"]
        depth = (math.sin(math.radians(wall["yaw"])), math.cos(math.radians(wall["yaw"])))
        bottom, top = y - wall["size"][1] / 2, y + wall["size"][1] / 2
        sides = [ws.drop(faces, x + depth[0] * offset, top, z + depth[1] * offset) for offset in (-1, 1)]
        assert any(hit is not None and bottom - 4 <= hit.y <= top + 4 for hit in sides), (wall, sides)

    assert any(60 <= wall["center"][0] <= 115 and -70 <= wall["center"][2] <= 70 for wall in walls)


def test_boundary_walls_leave_the_pit_open_to_the_kill_floor():
    source = colors.WORK / "export/maps/30"
    if not (source / "collision.json").exists():
        pytest.skip("Run task conker:extract to create the local Colors fixture")
    runs = json.loads((source / "collision.json").read_text())
    faces = [
        tuple(colors.world_point(point, colors.ORIGIN, colors.SCALE) for point in points)
        for run in runs
        for points, _surface in run["triangles"]
    ]
    walls = colors.perimeter(faces)
    for x in range(-46, -21):
        for z in range(72, 112):
            assert not any(_covers(wall, x, z) for wall in walls), (x, z)
