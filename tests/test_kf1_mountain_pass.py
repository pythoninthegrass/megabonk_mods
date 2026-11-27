import hashlib
import json
import kf1_mountain_pass as kf1
import level_geometry as geometry
import pytest
import struct

SAMPLE = """Begin Map
Begin Actor Class=StaticMeshActor Name=StaticMeshActor589
    StaticMesh=StaticMesh'KillingFloorStatics.ArmyTruck'
    Tag="StaticMeshActor"
    Location=(X=6004.5,Y=2746.25,Z=1.000000)
    Rotation=(Yaw=-19456)
    DrawScale3D=(X=0.900000,Y=0.900000,Z=0.900000)
    Skins(0)=Texture'KF-MountainPass.GUP-MountainSky'
End Actor
Begin Actor Class=PlayerStart Name=PlayerStart0
    Location=(X=1208.5,Y=-1708.5,Z=974.5)
    Rotation=(Pitch=16,Yaw=8192,Roll=-32)
End Actor
Begin Actor Class=ShopVolume Name=ShopVolume1
    Location=(X=-1336.000000,Y=-3432.000000,Z=192.000000)
    Begin Brush Name=Model131
       Begin PolyList
          Begin Polygon Link=0
             Location=(X=9,Y=9,Z=9)
             Vertex   -00128.000000,-00120.000000,-00128.000000
          End Polygon
       End PolyList
    End Brush
End Actor
Begin Actor Class=PathNode Name=PathNode3
    Location=(X=1,Y=2,Z=3)
End Actor
Begin Actor Class=KFRandomItemSpawn Name=KFRandomItemSpawn1
End Actor
End Map
"""


def bmp(rows):
    height, width = len(rows), len(rows[0])
    pixels = b"".join(struct.pack(f"<{width}H", *row) for row in reversed(rows))
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 16, 0, len(pixels), 0, 0, 0, 0)
    return b"BM" + struct.pack("<IHHI", 54 + len(pixels), 0, 0, 54) + info + pixels


def test_parse_actors_reads_the_requested_classes_with_their_transforms():
    actors = kf1.parse_actors(SAMPLE)
    assert [actor["class"] for actor in actors] == ["StaticMeshActor", "PlayerStart", "ShopVolume", "KFRandomItemSpawn"]
    truck = actors[0]
    assert truck["name"] == "StaticMeshActor589"
    assert truck["mesh"] == "KillingFloorStatics.ArmyTruck"
    assert truck["location"] == (6004.5, 2746.25, 1.0)
    assert truck["rotation"] == (0, -19456, 0)
    assert truck["scale"] == (0.9, 0.9, 0.9)


def test_parse_actors_defaults_missing_properties_and_ignores_brush_internals():
    start, shop, spawn = kf1.parse_actors(SAMPLE)[1:]
    assert start["rotation"] == (16, 8192, -32)
    assert start["scale"] == (1, 1, 1)
    assert start["mesh"] is None
    assert shop["location"] == (-1336.0, -3432.0, 192.0)
    assert spawn["location"] == (0, 0, 0)


def test_parse_actors_filters_by_class():
    assert [a["name"] for a in kf1.parse_actors(SAMPLE, classes={"PlayerStart"})] == ["PlayerStart0"]


def test_world_point_keeps_handedness_and_puts_unreal_up_on_y():
    origin, scale = (10, 20, 30), 0.5
    assert kf1.world_point((10, 20, 30), origin, scale) == [0, 0, 0]
    assert kf1.world_point((12, 20, 30), origin, scale) == [0, 0, 1]
    assert kf1.world_point((10, 24, 30), origin, scale) == [2, 0, 0]
    assert kf1.world_point((10, 20, 36), origin, scale) == [0, 3, 0]
    x, y, z = ([c for c in kf1.world_point(point, (0, 0, 0), 1)] for point in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    cross = [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]]
    assert cross == z


def test_rotation_matrix_turns_in_65536ths_and_applies_yaw_after_pitch_after_roll():
    def turn(angles, vector):
        matrix = kf1.rotation_matrix(*angles)
        return [round(sum(row[i] * vector[i] for i in range(3)), 6) for row in matrix]

    assert turn((0, 16384, 0), (1, 0, 0)) == [0, 1, 0]
    assert turn((16384, 0, 0), (1, 0, 0)) == [0, 0, 1]
    assert turn((0, 0, 16384), (0, 1, 0)) == [0, 0, -1]
    assert turn((0, 0, 0), (1, 2, 3)) == [1, 2, 3]
    assert turn((16384, 16384, 0), (1, 0, 0)) == [0, 0, 1]
    assert turn((0, 32768, 0), (1, 0, 0)) == [-1, 0, 0]


def test_mesh_point_undoes_the_umodel_export_then_scales_rotates_and_translates():
    assert kf1.mesh_point((1, 2, 3), (0, 0, 0), (1, 1, 1), (0, 0, 0)) == pytest.approx((100, 300, 200))
    placed = kf1.mesh_point((1, 2, 3), (0, 16384, 0), (2, 1, 0.5), (10, 20, 30))
    assert placed == pytest.approx((10 - 300, 20 + 200, 30 + 100))


def test_read_heightmap_returns_rows_top_first_from_the_bottom_up_bmp():
    rows = [[1, 2, 3], [40000, 5, 6]]
    assert kf1.read_heightmap(bmp(rows)) == rows


def test_read_heightmap_rejects_other_formats():
    with pytest.raises(ValueError, match="16-bit"):
        kf1.read_heightmap(b"BM" + bytes(24) + struct.pack("<HH", 1, 8) + bytes(100))


def test_terrain_height_is_a_quarter_world_unit_per_value_step_around_flat_ground():
    assert kf1.terrain_height(32768) == 0
    assert kf1.terrain_height(32768 + 256) == 64
    assert kf1.terrain_height(32768 - 512) == -128


def test_terrain_points_center_the_grid_on_the_origin_at_64_units_per_sample():
    heights = [[32768] * 4 for _ in range(4)]
    heights[2][1] = 32768 + 256
    points = kf1.terrain_points(heights)
    assert points[0][0] == (-128, -128, 0)
    assert points[2][1] == (-64, 0, 64)
    assert points[3][3] == (64, 64, 0)


def test_terrain_triangles_cover_each_cell_and_face_up_in_world_space():
    heights = [[32768, 32768 + 256, 32768], [32768, 32768, 32768], [32768, 32768, 32768]]
    triangles = kf1.terrain_triangles(heights, (0, 0, 0), 1)
    assert len(triangles) == 8
    assert all(len(points) == 3 for points, _surface in triangles)
    assert geometry.floor_height(triangles, (-64, 1000, -64)) == pytest.approx(0, abs=1e-6)
    peak = kf1.world_point((0, -64, 64), (0, 0, 0), 1)
    assert geometry.floor_height(triangles, (peak[0], 1000, peak[2])) == pytest.approx(64)
    midway = kf1.world_point((0, -32, 32), (0, 0, 0), 1)
    assert 0 < geometry.floor_height(triangles, (midway[0], 1000, midway[2])) < 64


def test_floor_placement_drops_a_point_on_the_terrain_with_clearance():
    triangles = kf1.terrain_triangles([[32768 + 256] * 3 for _ in range(3)], (0, 0, 0), 0.5)
    placement = kf1.floor_placement(triangles, (0, 0, 100), (0, 0, 0), 0.5, clearance=2)
    assert placement == [0, 34, 0]


def test_floor_placement_refuses_points_with_no_floor_nearby():
    triangles = kf1.terrain_triangles([[32768] * 3 for _ in range(3)], (0, 0, 0), 1)
    with pytest.raises(ValueError, match="No floor"):
        kf1.floor_placement(triangles, (5000, 5000, 0), (0, 0, 0), 1)
    with pytest.raises(ValueError, match="No floor"):
        kf1.floor_placement(triangles, (0, 0, 900), (0, 0, 0), 1, reach=100)


def level_actors(*specs):
    return kf1.parse_actors(
        "\n".join(
            f"Begin Actor Class={cls} Name={cls}{i}\n    Location=(X={x},Y={y},Z=10)\n    Rotation=(Yaw={yaw})\nEnd Actor"
            for i, (cls, x, y, yaw) in enumerate(specs)
        )
    )


def level_terrain():
    return kf1.terrain_triangles([[32768] * 8 for _ in range(8)], kf1.ORIGIN, kf1.SCALE)


def test_make_level_anchors_spawn_boss_shrines_chests_and_powerups_on_the_floor():
    actors = level_actors(
        ("PlayerStart", 0, 0, 16384),
        ("ZombieVolume", 64, 0, 0),
        ("ZombieVolume", -192, 0, 0),
        ("ShopVolume", 128, 0, 0),
        ("KFRandomItemSpawn", -128, 0, 0),
        ("KFRandomItemSpawn", 0, 128, 0),
        ("KFAmmoPickup", 0, -128, 0),
    )
    level = kf1.make_level(level_terrain(), actors)
    assert level["spawn"]["position"][1] == pytest.approx(2, abs=0.01)
    assert level["spawn"]["rotation"] == [0, 90, 0]
    assert level["bossSpawner"]["position"][2] == pytest.approx(kf1.SCALE * -192, abs=0.01)
    assert level["bossSpawner"]["position"][1] == pytest.approx(0, abs=0.01)
    assert len(level["shrineSpots"]) == 1
    assert len(level["powerupSpots"]) == 1
    assert all(spot[1] == pytest.approx(0, abs=0.01) for spot in level["shrineSpots"] + level["powerupSpots"])
    chests = [json.loads(edit["payload"]) for edit in level["edits"]]
    assert [chest["catalogId"] for chest in chests] == ["interactable/chest"] * 2
    assert all(chest["position"]["y"] == pytest.approx(0.5, abs=0.01) for chest in chests)
    assert level["killFloorY"] < 0


def test_make_level_only_emits_fields_the_runtime_already_reads():
    level = kf1.make_level(level_terrain(), level_actors(("PlayerStart", 0, 0, 0), ("ZombieVolume", 64, 0, 0)))
    assert set(level) <= kf1.LEVEL_FIELDS
    assert json.loads(json.dumps(level)) == level
    assert level["schemaVersion"] == 4
    assert level["baseline"] == "none"
    assert {"grid", "spawn", "bossSpawner"} <= set(level)


def test_make_level_skips_and_reports_anchors_with_no_terrain_floor():
    actors = level_actors(
        ("PlayerStart", 0, 0, 0),
        ("ZombieVolume", 64, 0, 0),
        ("ShopVolume", 100000, 0, 0),
        ("KFRandomItemSpawn", 0, 100000, 0),
        ("KFAmmoPickup", -100000, 0, 0),
    )
    skipped = []
    level = kf1.make_level(level_terrain(), actors, skipped)
    assert sorted(item.split()[0] for item in skipped) == ["KFAmmoPickup", "KFRandomItemSpawn", "ShopVolume"]
    assert level["shrineSpots"] == level["powerupSpots"] == level["edits"] == []


def test_make_level_picks_the_farthest_boss_volume_that_has_a_floor():
    actors = level_actors(("PlayerStart", 0, 0, 0), ("ZombieVolume", -192, 0, 0), ("ZombieVolume", 100000, 0, 0))
    boss = kf1.make_level(level_terrain(), actors)["bossSpawner"]["position"]
    assert boss[2] == pytest.approx(kf1.SCALE * -192, abs=0.01)


def test_make_level_refuses_a_spawn_with_no_floor():
    actors = level_actors(("PlayerStart", 100000, 0, 0), ("ZombieVolume", 64, 0, 0))
    with pytest.raises(ValueError, match="No floor"):
        kf1.make_level(level_terrain(), actors)


@pytest.mark.parametrize("missing", ["PlayerStart", "ZombieVolume"])
def test_make_level_needs_a_spawn_and_a_boss_volume(missing):
    actors = [a for a in level_actors(("PlayerStart", 0, 0, 0), ("ZombieVolume", 64, 0, 0)) if a["class"] != missing]
    with pytest.raises(ValueError, match=missing):
        kf1.make_level(level_terrain(), actors)


def test_walls_come_from_the_shared_perimeter_of_the_terrain():
    terrain = kf1.terrain_triangles([[32768] * 16 for _ in range(16)], (0, 0, 0), 0.02)
    walls = kf1.walls(terrain)
    assert walls
    assert walls == geometry.perimeter([points for points, _surface in terrain], kill_floor=kf1.KILL_FLOOR_Y)


def test_object_edit_is_shared_with_conker():
    import conker_colors

    assert conker_colors.geometry.object_edit is geometry.object_edit
    edit = geometry.object_edit("interactable/chest", (1, 2, 3), 90)
    assert edit["opType"] == "object.place"
    assert json.loads(edit["payload"]) == {
        "catalogId": "interactable/chest",
        "position": {"x": 1, "y": 2, "z": 3},
        "rotation": {"x": 90, "y": 0, "z": 0},
        "scale": {"x": 1, "y": 1, "z": 1},
    }


def test_mesh_path_names_the_package_and_mesh_and_ignores_the_group(tmp_path):
    assert kf1.mesh_path(tmp_path, "KillingFloorStatics.ArmyTruck") == tmp_path / "KillingFloorStatics/StaticMesh/ArmyTruck.gltf"
    assert kf1.mesh_path(tmp_path, "HemispheresSM.BasicHEM.krasnyi_HEM") == tmp_path / "HemispheresSM/StaticMesh/krasnyi_HEM.gltf"


def test_render_primitive_places_an_umodel_mesh_with_up_facing_world_triangles():
    data = struct.pack("<9f2f2f2f3I", 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0.25, 1, 0, 0, 1, 2)
    gltf = {
        "bufferViews": [{"byteOffset": offset} for offset in (0, 36, 60)],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC2"},
            {"bufferView": 2, "componentType": 5125, "count": 3, "type": "SCALAR"},
        ],
    }
    primitive = {"attributes": {"POSITION": 0, "TEXCOORD_0": 1}, "indices": 2}
    result = kf1.render_primitive(gltf, data, primitive, (0, 0, 0), (1, 1, 1), (0, 0, 0), (0, 0, 0), 0.01, material=7)
    assert result["positions"] == pytest.approx([0, 0, 0, 1, 0, 0, 0, 0, 1])
    assert result["indices"] == [0, 2, 1]
    assert result["uv"] == [0, 1, 0, 0.75, 1, 1]
    assert result["rgba"] == []
    assert result["material"] == 7
    a, b, c = (result["positions"][i : i + 3] for i in (0, 6, 3))
    assert (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]) > 0


def test_verify_export_rejects_a_different_level_file(tmp_path, monkeypatch):
    t3d = tmp_path / "KF-MountainPass.t3d"
    t3d.write_bytes(b"fixture")
    monkeypatch.setattr(kf1, "T3D_SHA256", hashlib.sha256(b"fixture").hexdigest())
    kf1.verify_export(t3d)
    t3d.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="KF-MountainPass"):
        kf1.verify_export(t3d)


def test_read_accessor_reads_unsigned_short_indices_that_umodel_writes():
    data = struct.pack("<3H", 0, 2, 65535)
    gltf = {
        "bufferViews": [{"byteOffset": 0}],
        "accessors": [{"bufferView": 0, "componentType": 5123, "count": 3, "type": "SCALAR"}],
    }
    assert geometry.read_accessor(gltf, data, 0) == [(0,), (2,), (65535,)]


def test_boss_spawner_is_regular_size_with_only_the_cylinder_hidden():
    level = kf1.make_level(level_terrain(), level_actors(("PlayerStart", 0, 0, 0), ("ZombieVolume", 64, 0, 0)))
    boss = level["bossSpawner"]
    assert "scale" not in boss
    assert boss["hiddenChildren"] == geometry.BOSS_PORTAL_HIDDEN_CHILDREN == ["BottomPiece"]
    assert "bossRedirect" not in level
