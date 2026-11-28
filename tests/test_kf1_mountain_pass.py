import hashlib
import json
import kf1_mountain_pass as kf1
import level_geometry as geometry
import pytest
import re
import struct
from PIL import Image


def test_additive_brush_render_collision_and_floor(tmp_path):
    brush = """Begin Actor Class=Brush Name=Floor
    CsgOper=CSG_Add
    PrePivot=(X=2)
    Location=(X=12,Z=50)
    Begin Brush Name=Model1
       Begin PolyList
          Begin Polygon Texture=Test.Floors.Stone Link=0
             Origin   +0,+0,+0
             TextureU +1,+0,+0
             TextureV +0,+1,+0
             Vertex   +0,+0,+0
             Vertex   +16,+0,+0
             Vertex   +16,+8,+0
             Vertex   +0,+8,+0
          End Polygon
       End PolyList
    End Brush
End Actor
"""
    path = tmp_path / "out/Test/Texture/Stone.tga"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (16, 8)).save(path)
    excluded = [
        brush.replace("CSG_Add", "CSG_Subtract"),
        brush.replace("Class=Brush", "Class=ShopVolume"),
        brush.replace("Test.Floors.Stone", "Engine.BlackTexture"),
        brush.replace("    CsgOper=CSG_Add\n", ""),
    ]
    brushes = kf1.parse_brushes(brush + "".join(excluded))
    heights = [[32768] * 2 for _ in range(2)]
    terrain = kf1.terrain_triangles(heights, kf1.ORIGIN, kf1.SCALE)
    mesh = kf1.unpack_map(tmp_path / "out", [], heights, terrain, brushes)
    (floor,) = mesh["meshes"][1:]
    (primitive,) = floor["primitives"]
    assert floor["name"] == "Floor"
    assert primitive["indices"] == [0, 1, 2, 0, 2, 3]
    assert primitive["positions"][:3] == pytest.approx([0, 50 * kf1.SCALE, 10 * kf1.SCALE])
    assert primitive["uv"] == [0, 1, 1, 1, 1, 0, 0, 0]
    assert (tmp_path / mesh["materials"][primitive["material"]]["texture"]).samefile(path)
    assert mesh["collision"]["indices"][6:] == [4, 5, 6, 4, 6, 7]
    assert mesh["collision"]["positions"][12:] == primitive["positions"]
    assert kf1.floor_placement(kf1.collision_triangles(mesh["collision"]), (12, 4, 55), kf1.ORIGIN, kf1.SCALE)[
        1
    ] == pytest.approx(50 * kf1.SCALE)
    path.unlink()
    missing = kf1.unpack_map(tmp_path / "out", [], heights, terrain, brushes)
    rgba = missing["meshes"][1]["primitives"][0]["rgba"]
    assert len(rgba) == 16
    assert max(rgba[:3]) < 180 and rgba[3] == 255


def test_standing_kf_human_matches_player_capsule():
    assert pytest.approx(3.85) == 2 * 50 * kf1.SCALE


def test_actor_scalar_scale_and_skin_slot():
    actor = kf1.parse_actors(SAMPLE.replace('    Tag="StaticMeshActor"', '    DrawScale=3.0'))[0]
    assert actor["scale"] == pytest.approx((2.7, 2.7, 2.7))
    assert actor["skins"][0] == "KF-MountainPass.GUP-MountainSky"


VEHICLE_MESHES = (
    "KillingFloorStatics.London_police_car",
    "KillingFloorStatics.LanciaStatic1",
    "KillingFloorStatics.LondonCabASE",
    "KillingFloorStatics.ArmyTruck",
    "KF-MountainPass.GUP-Lorry1",
)
LORRY_PARTS = (
    "KF-MountainPass.GUP-LorryDoorLeft",
    "KF-MountainPass.GUP-LorryDoorRight",
    "KF-MountainPass.GUP-LorryCargoDoor",
)


def vehicle_actor(name, mesh, location=(0, 0, 0), scale=(1, 1, 1)):
    return {"name": name, "mesh": mesh, "location": location, "rotation": (0, 0, 0), "scale": scale}


def test_cars_and_trucks_are_enlarged_and_nothing_else():
    assert pytest.approx(1.2) == kf1.VEHICLE_SCALE
    assert frozenset(VEHICLE_MESHES) == kf1.VEHICLE_MESHES
    assert frozenset(LORRY_PARTS) == kf1.LORRY_PART_MESHES
    for mesh in VEHICLE_MESHES:
        (enlarged,) = kf1.enlarge_vehicles([vehicle_actor("V", mesh, (100, 0, 50), (3.5, -3.5, 2.0))])
        assert enlarged["scale"] == pytest.approx((4.2, -4.2, 2.4))
        assert enlarged["location"] == (100, 0, 50)
    for mesh in ("KillingFloorStatics.TWBus", "KillingFloorStatics.Ambulance", "22Patch.ChopperBroken", None):
        actor = vehicle_actor("O", mesh, (100, 0, 50), (3.5, 3.5, 3.5))
        assert kf1.enlarge_vehicles([actor]) == [actor]


def test_lorry_parts_grow_about_the_nearest_lorry_so_they_stay_attached():
    near, far = (1000, 0, 0), (-9000, 0, 0)
    actors = [
        vehicle_actor("LorryNear", "KF-MountainPass.GUP-Lorry1", near),
        vehicle_actor("LorryFar", "KF-MountainPass.GUP-Lorry1", far),
        vehicle_actor("Door", "KF-MountainPass.GUP-LorryDoorLeft", (1100, 50, 20)),
    ]
    door = kf1.enlarge_vehicles(actors)[2]
    assert door["scale"] == pytest.approx((1.2, 1.2, 1.2))
    assert door["location"] == pytest.approx((1120, 60, 24))


def test_enlarge_vehicles_does_not_mutate_its_input():
    actors = [vehicle_actor("V", VEHICLE_MESHES[0], scale=(1, 1, 1))]
    kf1.enlarge_vehicles(actors)
    assert actors[0]["scale"] == (1, 1, 1)


def write_unit_triangle(meshes, package, name):
    folder = meshes / package / "StaticMesh"
    folder.mkdir(parents=True, exist_ok=True)
    data = struct.pack("<9f3H2x", 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 2)
    (folder / f"{name}.bin").write_bytes(data)
    gltf = {
        "buffers": [{"uri": f"{name}.bin", "byteLength": len(data)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 36},
            {"buffer": 0, "byteOffset": 36, "byteLength": 6},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]},
            {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
    }
    (folder / f"{name}.gltf").write_text(json.dumps(gltf))


def test_unpack_map_renders_an_enlarged_car_larger_than_a_bus(tmp_path):
    meshes = tmp_path / "out"
    write_unit_triangle(meshes, "KillingFloorStatics", "LanciaStatic1")
    write_unit_triangle(meshes, "KillingFloorStatics", "TWBus")
    heights = [[32768] * 2 for _ in range(2)]
    terrain = kf1.terrain_triangles(heights, kf1.ORIGIN, kf1.SCALE)
    actors = [
        vehicle_actor("Car", "KillingFloorStatics.LanciaStatic1"),
        vehicle_actor("Bus", "KillingFloorStatics.TWBus"),
    ]
    mesh = kf1.unpack_map(meshes, kf1.enlarge_vehicles(actors), heights, terrain)
    rendered = {m["name"]: m["primitives"][0]["positions"] for m in mesh["meshes"][1:]}
    assert max(rendered["Car"]) == pytest.approx(1.2 * max(rendered["Bus"]))


def test_exported_shader_finds_diffuse_in_named_package_with_cutout_alpha(tmp_path):
    meshes = tmp_path / "out"
    mat = meshes / "Foliage/Shader/Needles.mat"
    mat.parent.mkdir(parents=True)
    mat.write_text("Diffuse=Branch\n")
    texture = meshes / "Foliage/Texture/Branch.tga"
    texture.parent.mkdir()
    image = Image.new("RGBA", (2, 1), (40, 60, 20, 255))
    image.putpixel((0, 0), (0, 0, 0, 0))
    image.save(texture)
    material = kf1.static_material(kf1.material_index(meshes), meshes, "Foliage.Trees.Needles", {})
    assert material["texture"] == "out/Foliage/Texture/Branch.tga"
    assert material["alphaMode"] == "MASK"


def test_explicit_skin_does_not_borrow_a_same_named_texture_from_another_package(tmp_path):
    texture = tmp_path / "out/Other/Texture/Floor.tga"
    texture.parent.mkdir(parents=True)
    Image.new("RGB", (1, 1)).save(texture)
    meshes = tmp_path / "out"
    material = kf1.static_material(kf1.material_index(meshes), meshes, "Missing.Room.Floor", {}, explicit_skin=True)
    assert "texture" not in material
    assert material["baseColor"] == [0.3, 0.3, 0.3, 1]


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
        ),
        classes=kf1.ACTOR_CLASSES | {"PathNode"},
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
    chests = [json.loads(edit["payload"]) for edit in level["edits"][1:]]
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


def test_shrine_spots_include_grounded_path_nodes_beyond_the_maximum_shrine_count():
    actors = level_actors(
        ("PlayerStart", 0, 0, 0),
        ("ZombieVolume", 64, 0, 0),
        ("ShopVolume", -64, 0, 0),
        ("PathNode", 8000, 0, 0),
        *(("PathNode", x, 128, 0) for x in range(-192, 193, 32)),
    )
    level = kf1.make_level(level_terrain(), actors)
    spots = level["shrineSpots"]
    assert len({tuple(spot) for spot in spots}) == level["extraShrinesMax"] + len(level["guaranteedShrineKinds"]) + 1
    assert all(y == 0 for _, y, _ in spots)


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
    assert level["shrineSpots"] == level["powerupSpots"] == []
    assert level["edits"] == [kf1.bundle_placement_edit()]


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


TERRAIN_LAYERS = {
    0: ("Landscape_T.Soil.earth_1051", "KF-MountainPass.Main_Dirt", 2.0, 2.0),
    1: ("Landscape_T.Grass.grass_2589", "KF-MountainPass.Main_Grass", 2.0, 2.0),
    2: ("KF-MountainPass.GUP-MountainRock", "KF-MountainPass.Main_Rock", 2.0, 2.0),
    3: ("KF-MountainPass.GUP-GravelRocks", "KF-MountainPass.Main_Gravel", 1.5, 1.5),
    4: ("WyreTex.Common.MudGround", "KF-MountainPass.Main_Forest", 2.0, 2.0),
    6: ("KF-MountainPass.GUP-MountainGrass", "KF-MountainPass.Main_DecoGrass", 1.0, 1.0),
    7: ("KF-MountainPass.Main_DecoGrass", "KF-MountainPass.Main_DecoFoliage", 1.0, 1.0),
}
TERRAIN_DECO = {
    0: ("WyreStatics.Forest.WyreMiddleFoliage", "KF-MountainPass.Main_DecoFoliage"),
    1: ("KF-MountainPass.GUP-GrassLOD", "KF-MountainPass.Main_DecoGrass"),
}


def terrain_actor(layers=TERRAIN_LAYERS, deco=TERRAIN_DECO):
    """A TerrainInfo1 actor as UCC batchexport writes it, with only the given numeric slots."""

    def layer(slot, diffuse, mask, uscale, vscale):
        return (
            f"    Layers({slot})=(Texture=Texture'{diffuse}',AlphaMap=Texture'{mask}',"
            f"UScale={uscale:.6f},VScale={vscale:.6f},TerrainMatrix=("
            f"XPlane=(X={1 / (64 * uscale):.6f}),YPlane=(Y={1 / (64 * vscale):.6f}),ZPlane=(Z=4.000000),"
            "WPlane=(W=1.000000,X=0.015625,Y=0.015625,Z=524272.000000)))\n"
        )

    def deco_layer(slot, mesh, density_map):
        return (
            f"    DecoLayers({slot})=(ShowOnTerrain=1,DensityMap=Texture'{density_map}',"
            f"StaticMesh=StaticMesh'{mesh}',ScaleMultiplier=(X=(Min=0.800000,Max=1.000000),"
            "Y=(Min=0.800000,Max=1.000000),Z=(Min=0.500000,Max=1.000000),"
            "FadeoutRadius=(Min=3000.000000,Max=3000.000000),DensityMultiplier=(Min=0.500000,Max=0.750000),"
            "MaxPerQuad=1,AlignToTerrain=1)\n"
        )

    return (
        "Begin Actor Class=TerrainInfo Name=TerrainInfo2\n"
        "    Layers(5)=(Texture=Texture'Bogus.Other',AlphaMap=Texture'Bogus.Hidden',UScale=1.000000,VScale=1.000000,"
        "TerrainMatrix=(XPlane=(X=0.015625),YPlane=(Y=0.015625),ZPlane=(Z=4.000000),"
        "WPlane=(W=1.000000,X=0.031250,Y=0.031250,Z=524272.000000)))\nEnd Actor\n"
        "Begin Actor Class=TerrainInfo Name=TerrainInfo1\n"
        "    TerrainMap=Texture'KF-MountainPass.Terrain_Main'\n"
        + "".join(layer(slot, *layers[slot]) for slot in sorted(layers))
        + "".join(deco_layer(slot, *deco[slot]) for slot in sorted(deco))
        + "    DecoLayerOffset=-4.000000\nEnd Actor\n"
    )


def write_tga(meshes, reference, image, folder=None):
    package, *parts = reference.split(".")
    path = meshes / package / (folder or parts[0] if len(parts) == 2 else "Texture") / f"{parts[-1]}.tga"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def write_mesh(meshes, reference, folder=None):
    package, *parts = reference.split(".")
    path = meshes / package / (folder or parts[0] if len(parts) == 2 else "StaticMesh") / f"{parts[-1]}.gltf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")
    return path


def alpha_mask(size=8):
    """A umodel-exported mask: flat gray color with the layer weight in the alpha channel."""
    image = Image.new("RGBA", (size, size))
    image.putdata([(127, 127, 127, round(255 * i / (size * size - 1))) for i in range(size * size)])
    return image


def export_terrain(meshes, layers=TERRAIN_LAYERS, deco=TERRAIN_DECO, texture_folder=None, skip=()):
    """Write umodel's exported files for every reference the terrain names, textures in the given folder."""
    for _, (diffuse, mask, _, _) in layers.items():
        for reference in (diffuse, mask):
            if reference not in skip:
                write_tga(
                    meshes,
                    reference,
                    alpha_mask() if "Main_" in reference else Image.new("RGB", (16, 16)),
                    texture_folder,
                )
    for _, (mesh, density_map) in deco.items():
        if mesh not in skip:
            write_mesh(meshes, mesh)
        if density_map not in skip and density_map not in {layer[1] for layer in layers.values()}:
            write_tga(meshes, density_map, alpha_mask(), texture_folder)


def test_terrain_layers_keep_numeric_slots_and_uv_settings():
    terrain = kf1.parse_terrain_layers(terrain_actor())
    assert sorted(terrain["layers"]) == [0, 1, 2, 3, 4, 6, 7]
    assert terrain["heightmap"] == "KF-MountainPass.Terrain_Main"
    assert terrain["deco_offset"] == pytest.approx(-4.0)
    gravel = terrain["layers"][3]
    assert gravel["diffuse"] == "KF-MountainPass.GUP-GravelRocks"
    assert gravel["mask"] == "KF-MountainPass.Main_Gravel"
    assert (gravel["uscale"], gravel["vscale"]) == (1.5, 1.5)
    assert gravel["matrix"]["u"] == pytest.approx(1 / 96, rel=1e-4)
    assert gravel["matrix"]["v"] == pytest.approx(1 / 96, rel=1e-4)
    foliage = terrain["deco_layers"][0]
    assert foliage["mesh"] == "WyreStatics.Forest.WyreMiddleFoliage"
    assert foliage["density_map"] == "KF-MountainPass.Main_DecoFoliage"
    assert foliage["align_to_terrain"] is True
    assert foliage["density"] == pytest.approx((0.5, 0.75))
    assert foliage["scale"]["z"] == pytest.approx((0.5, 1.0))


def test_terrain_layers_come_only_from_terrain_info1(tmp_path):
    layers = {slot: TERRAIN_LAYERS[slot] for slot in (0, 7)}
    terrain = kf1.parse_terrain_layers(terrain_actor(layers=layers, deco={}))
    assert sorted(terrain["layers"]) == [0, 7]


def test_terrain_inventory_keeps_same_named_objects_apart(tmp_path):
    meshes = tmp_path / "out"
    layers = {
        0: ("Landscape_T.Soil.rock", "Landscape_T.Common.MudGround", 2.0, 2.0),
        1: ("Landscape_T.Grass.rock", "WyreTex.Common.MudGround", 2.0, 2.0),
    }
    export_terrain(meshes, layers=layers, deco={})
    rows = kf1.terrain_inventory(meshes, terrain_actor(layers=layers, deco={}))["layers"]
    assert [row["diffuse"]["file"] for row in rows] == ["Landscape_T/Soil/rock.tga", "Landscape_T/Grass/rock.tga"]
    assert [row["mask"]["file"] for row in rows] == ["Landscape_T/Common/MudGround.tga", "WyreTex/Common/MudGround.tga"]


def test_terrain_inventory_falls_back_to_umodel_class_folders(tmp_path):
    meshes = tmp_path / "out"
    export_terrain(meshes, texture_folder="Texture")
    rows = kf1.terrain_inventory(meshes, terrain_actor())["layers"]
    assert rows[0]["diffuse"]["file"] == "Landscape_T/Texture/earth_1051.tga"
    assert rows[0]["deco_layers"] == []


@pytest.mark.parametrize("missing", ["Landscape_T.Soil.earth_1051", "KF-MountainPass.GUP-GrassLOD"])
def test_terrain_inventory_names_the_missing_qualified_object(tmp_path, missing):
    meshes = tmp_path / "out"
    export_terrain(meshes, skip=(missing,))
    with pytest.raises(ValueError, match=re.escape(missing)):
        kf1.terrain_inventory(meshes, terrain_actor())


def test_terrain_mask_weight_is_the_alpha_channel(tmp_path):
    summary = kf1.mask_summary(write_tga(tmp_path, "KF-MountainPass.Main_Grass", alpha_mask(16)))
    assert summary["channel"] == "alpha"
    assert summary["distinct"] == 256
    assert summary["mean"] == pytest.approx(0.5, abs=0.01)
    assert summary["covered"] == pytest.approx(0.5, abs=0.01)


def test_terrain_mask_channel_falls_back_to_color_and_reports_a_constant_mask(tmp_path):
    image = Image.new("RGBA", (4, 4))
    image.putdata([(i * 17 % 256, 0, 0, 255) for i in range(16)])
    assert kf1.mask_summary(write_tga(tmp_path, "KF-MountainPass.Main_Painted", image))["channel"] == "red"
    flat = Image.new("RGBA", (4, 4), (127, 127, 127, 255))
    assert kf1.mask_summary(write_tga(tmp_path, "KF-MountainPass.Main_Dirt", flat))["channel"] == "constant"


def test_terrain_inventory_reports_a_mask_used_as_a_surface(tmp_path):
    meshes = tmp_path / "out"
    export_terrain(meshes)
    rows = {row["slot"]: row for row in kf1.terrain_inventory(meshes, terrain_actor())["layers"]}
    assert rows[7]["role"] == "mask-as-diffuse"
    assert rows[0]["role"] == rows[6]["role"] == "ground"
    assert rows[6]["deco_layers"] == [1]
    assert rows[7]["deco_layers"] == [0]
    assert rows[0]["deco_layers"] == []
    assert rows[2]["diffuse"]["width"] == 16
    assert rows[2]["mask"]["width"] == 8
    assert rows[3]["units_per_tile"] == pytest.approx([96.0, 96.0])


def test_terrain_table_has_one_row_per_occupied_slot(tmp_path):
    meshes = tmp_path / "out"
    export_terrain(meshes)
    table = kf1.terrain_table(kf1.terrain_inventory(meshes, terrain_actor()))
    assert table[0].startswith("| slot")
    assert all(name in table[0] for name in ("role", "weight channel", "units per tile"))
    assert [line.split("|")[1].strip() for line in table[2:]] == ["0", "1", "2", "3", "4", "6", "7"]
    assert any("Main_DecoFoliage" in line for line in table)


needs_kf1_export = pytest.mark.skipif(
    not (kf1.WORK / "export/KF-MountainPass.t3d").is_file(), reason="needs the KF1 batchexport under .tools/kf1/export"
)


@needs_kf1_export
def test_the_exported_terrain_info1_names_the_expected_layers():
    text = (kf1.WORK / "export/KF-MountainPass.t3d").read_text(encoding="latin-1")
    terrain = kf1.parse_terrain_layers(text)
    assert sorted(terrain["layers"]) == [0, 1, 2, 3, 4, 6, 7]
    assert [terrain["layers"][slot]["diffuse"] for slot in sorted(terrain["layers"])] == [
        TERRAIN_LAYERS[slot][0] for slot in sorted(TERRAIN_LAYERS)
    ]
    assert [terrain["layers"][slot]["uscale"] for slot in sorted(terrain["layers"])] == [2.0, 2.0, 2.0, 1.5, 2.0, 1.0, 1.0]
    assert terrain["deco_layers"][0]["mesh"] == "WyreStatics.Forest.WyreMiddleFoliage"
    for layer in terrain["layers"].values():
        assert layer["matrix"]["u"] == pytest.approx(1 / (kf1.SAMPLE_UNITS * layer["uscale"]), abs=1e-6)
        assert layer["matrix"]["v"] == pytest.approx(1 / (kf1.SAMPLE_UNITS * layer["vscale"]), abs=1e-6)
    if not (kf1.WORK / "out/Landscape_T").is_dir():
        pytest.skip("needs the umodel export of the terrain texture packages")
    inventory = kf1.terrain_inventory(kf1.WORK / "out", text)
    assert {row["mask"]["channel"] for row in inventory["layers"]} == {"alpha", "constant"}
    assert {row["mask"]["width"] for row in inventory["layers"]} == {256}
    assert {row["role"] for row in inventory["layers"]} == {"ground", "mask-as-diffuse"}


def test_make_level_declares_the_pack_and_places_the_bundle_asset_first():
    level = kf1.make_level(level_terrain(), level_actors(("PlayerStart", 0, 0, 0), ("ZombieVolume", 64, 0, 0)))
    assert level["packs"] == {kf1.PACK_ID: kf1.PACK_VERSION}
    assert level["edits"][0] == {
        "opType": "object.place",
        "target": "",
        "payload": (
            '{"catalogId":"bundle:kf1/MountainPass","position":{"x":0,"y":0,"z":0},'
            '"rotation":{"x":0,"y":0,"z":0},"scale":{"x":1,"y":1,"z":1}}'
        ),
    }


def test_prepare_writes_no_separate_preview_level():
    assert not hasattr(kf1, "preview_level")
    assert not hasattr(kf1, "PREVIEW_LEVEL_NAME")


@needs_kf1_export
def test_the_generated_level_on_disk_loads_the_pack():
    level = json.loads((kf1.WORK / kf1.LEVEL_NAME).read_text())
    assert level["packs"] == {kf1.PACK_ID: kf1.PACK_VERSION}
    assert f"bundle:{kf1.PACK_ID}/{kf1.PACK_ASSET}" in level["edits"][0]["payload"]
