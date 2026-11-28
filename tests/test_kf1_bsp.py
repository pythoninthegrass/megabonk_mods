import kf1_bsp
import kf1_mountain_pass as kf1
import pytest

WALL = "Test.A.Wall"
ROOM = "Test.A.Room"
DOOR = "Test.B.Door"
FLOOR = "Test.A.Floor"


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def polygon(vertices, texture, outward=None, wind_backwards=False):
    """One T3D polygon: an outward Normal, the Vertex ring that winds it, and optional bad winding."""
    normal = _cross(
        [vertices[1][k] - vertices[0][k] for k in range(3)],
        [vertices[2][k] - vertices[0][k] for k in range(3)],
    )
    ring = list(vertices)
    if outward and sum(n * o for n, o in zip(normal, outward, strict=True)) < 0:
        normal = tuple(-n for n in normal)
        ring = ring[::-1]
    if wind_backwards:
        ring = ring[::-1]
    lines = [f"          Begin Polygon Texture={texture} Link=0"]
    lines.append("             Origin   " + ",".join(f"{n:+f}" for n in ring[0]))
    lines.append("             Normal   " + ",".join(f"{n:+f}" for n in normal))
    lines.append("             TextureU +1,+0,+0")
    lines.append("             TextureV +0,+1,+0")
    lines += ["             Vertex   " + ",".join(f"{n:+f}" for n in v) for v in ring]
    lines.append("          End Polygon")
    return "\n".join(lines)


def box_polygons(lo, hi, texture, backwards=()):
    """The six outward polygons of an axis-aligned box, some wound backwards on purpose."""
    lo, hi = [float(n) for n in lo], [float(n) for n in hi]
    corner = lambda i, j, k: tuple(lo[n] if flag == 0 else hi[n] for n, flag in enumerate((i, j, k)))
    centre = [(lo[n] + hi[n]) / 2 for n in range(3)]
    faces = [
        [corner(0, 0, 0), corner(1, 0, 0), corner(1, 1, 0), corner(0, 1, 0)],
        [corner(0, 0, 1), corner(0, 1, 1), corner(1, 1, 1), corner(1, 0, 1)],
        [corner(0, 0, 0), corner(0, 0, 1), corner(1, 0, 1), corner(1, 0, 0)],
        [corner(0, 1, 0), corner(1, 1, 0), corner(1, 1, 1), corner(0, 1, 1)],
        [corner(0, 0, 0), corner(0, 0, 1), corner(0, 1, 1), corner(0, 1, 0)],
        [corner(1, 0, 0), corner(1, 1, 0), corner(1, 1, 1), corner(1, 0, 1)],
    ]
    polygons = []
    for index, face in enumerate(faces):
        middle = [sum(v[k] for v in face) / len(face) for k in range(3)]
        outward = [m - c for m, c in zip(middle, centre, strict=True)]
        polygons.append(polygon(face, texture, outward, index in backwards))
    return polygons


def actor(name, op, polys):
    return (
        f"Begin Actor Class=Brush Name={name}\n"
        f"    CsgOper={op}\n"
        "    Location=(X=0,Y=0,Z=0)\n"
        "    PrePivot=(X=0,Y=0,Z=0)\n"
        "    Begin Brush Name=Model\n"
        "       Begin PolyList\n" + "\n".join(polys) + "\n       End PolyList\n"
        "    End Brush\n"
        "End Actor\n"
    )


def box_brush(name, op, lo, hi, texture, backwards=()):
    return actor(name, op, box_polygons(lo, hi, texture, backwards))


def compile_text(text):
    return kf1_bsp.compile_brushes(kf1.parse_brushes(text))


def triangles_of(text):
    return compile_text(text).triangles


def volume(triangles):
    total = 0.0
    for _, _, (a, b, c) in triangles:
        total += a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
    return abs(total) / 6


def area(triangles):
    total = 0.0
    for _, _, (a, b, c) in triangles:
        u, v = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
        total += sum(n * n for n in _cross(u, v)) ** 0.5 / 2
    return total


def segment_hits(triangles, start, end):
    """Moller-Trumbore, so an opening is judged by what a ray through it actually meets.

    Distances are deduplicated: a ray that runs along the edge two triangles of one surface share
    meets both of them at the same distance, which is one surface, not two.
    """
    d = [end[k] - start[k] for k in range(3)]
    hits = set()
    for _, _, (a, b, c) in triangles:
        e1, e2 = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
        p = _cross(d, e2)
        det = sum(x * y for x, y in zip(e1, p, strict=True))
        if abs(det) < 1e-9:
            continue
        s = [start[k] - a[k] for k in range(3)]
        u = sum(x * y for x, y in zip(s, p, strict=True)) / det
        if not 0 <= u <= 1:
            continue
        q = _cross(s, e1)
        v = sum(x * y for x, y in zip(d, q, strict=True)) / det
        if v < 0 or u + v > 1:
            continue
        t = sum(x * y for x, y in zip(e2, q, strict=True)) / det
        if 0 <= t <= 1:
            hits.add(round(t, 9))
    return len(hits)


def test_closed_box_brush_compiles_to_its_twelve_triangles():
    compiled = compile_text(box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL))
    assert compiled.uncarved == [] and compiled.cutters == [] and compiled.estimated == 0
    assert len(compiled.triangles) == 12
    assert volume(compiled.triangles) == pytest.approx(64)
    assert area(compiled.triangles) == pytest.approx(96)
    assert {name for name, _, _ in compiled.triangles} == {"Wall"}


def test_backwards_wound_polygon_still_builds_the_solid():
    compiled = compile_text(box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL, backwards=(2,)))
    assert compiled.uncarved == []
    assert volume(compiled.triangles) == pytest.approx(64)
    assert area(compiled.triangles) == pytest.approx(96)


def test_subtractive_brush_carves_the_additive_box_and_the_cutters_faces_appear():
    text = box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + box_brush("Cut", "CSG_Subtract", (3, 3, 0), (6, 6, 6), ROOM)
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(64 - 1 * 1 * 4)
    assert [tri for _, _, tri in compiled.triangles if all(3.5 < n < 5.5 for p in tri for n in p)] == []
    assert {name for name, _, _ in compiled.triangles} == {"Wall", "Cut"}
    assert sum(1 for name, _, _ in compiled.triangles if name == "Cut") == 4


def test_subtractive_brush_before_the_brush_it_would_cut_carries_no_effect():
    carved = compile_text(
        box_brush("Cut", "CSG_Subtract", (3, 3, 0), (6, 6, 6), ROOM) + box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL)
    )
    plain = compile_text(box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL))
    assert carved.triangles == plain.triangles


def test_world_size_subtractive_brush_that_arrives_first_carries_no_effect():
    compiled = compile_text(
        box_brush("World", "CSG_Subtract", (-30720, -30720, -18368), (30720, 30720, 18368), ROOM)
        + box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL)
    )
    assert volume(compiled.triangles) == pytest.approx(64)


def test_a_fully_enclosed_carve_keeps_both_skins_of_the_void():
    text = box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + box_brush(
        "Room", "CSG_Subtract", (1, 1, 1), (3, 3, 3), ROOM
    )
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(64 - 8)
    assert volume([item for item in compiled.triangles if item[0] == "Wall"]) == pytest.approx(64)
    assert volume([item for item in compiled.triangles if item[0] == "Room"]) == pytest.approx(8)
    assert segment_hits(compiled.triangles, (2.5, 1.5, 2), (2.5, 1.5, 9)) == 2


def test_subtractive_brush_that_holds_a_brush_removes_it():
    text = box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + box_brush(
        "Gone", "CSG_Subtract", (-1, -1, -1), (5, 5, 5), ROOM
    )
    compiled = compile_text(text)
    assert compiled.triangles == []
    assert compiled.cutters == []


def test_open_shell_subtractive_brush_leaves_the_geometry_as_it_was():
    five_faces = box_polygons((1, 1, 1), (3, 3, 3), ROOM)[:-1]
    text = box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + actor("Gap", "CSG_Subtract", five_faces)
    compiled = compile_text(text)
    assert [brush["name"] for brush in compiled.cutters] == ["Gap"]
    assert volume(compiled.triangles) == pytest.approx(64)
    assert compiled.uncarved == []


def test_doorway_subtractive_brush_clears_the_opening():
    wall = box_brush("Wall", "CSG_Add", (0, 0, 0), (40, 8, 64), WALL)
    assert segment_hits(triangles_of(wall), (20, -2, 20), (20, 10, 20)) == 2
    opened = compile_text(wall + box_brush("Door", "CSG_Subtract", (12, -2, 0), (28, 10, 40), DOOR))
    assert segment_hits(opened.triangles, (20, -2, 20), (20, 10, 20)) == 0
    assert segment_hits(opened.triangles, (5, -2, 20), (5, 10, 20)) == 2
    assert volume(opened.triangles) == pytest.approx(40 * 8 * 64 - 16 * 8 * 40)


def test_hidden_interior_faces_between_two_brushes_are_dropped():
    text = box_brush("A", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + box_brush("B", "CSG_Add", (2, 2, 2), (6, 6, 6), ROOM)
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(120)
    assert area(compiled.triangles) == pytest.approx(96 + 96 - 2 * 12)  # the three facing faces of each cube are buried
    assert [tri for _, _, tri in compiled.triangles if all(2.5 < n < 3.5 for p in tri for n in p)] == []


def test_touching_brushes_share_a_skin_instead_of_stacking_coplanar_faces():
    text = box_brush("A", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + box_brush("B", "CSG_Add", (4, 0, 0), (8, 4, 4), ROOM)
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(128)
    assert area(compiled.triangles) == pytest.approx(160)
    assert compiled.estimated == 0


def test_open_shell_brush_is_reported_as_uncarvable():
    five_faces = box_polygons((0, 0, 0), (4, 4, 4), WALL)[:-1]
    compiled = compile_text(actor("Shell", "CSG_Add", five_faces))
    assert compiled.triangles == []
    assert [brush["name"] for brush in compiled.uncarved] == ["Shell"]
    assert len(compiled.uncarved[0]["faces"]) == 5


def test_uncarvable_brushes_are_still_handed_to_the_render_pass():
    five_faces = box_polygons((0, 0, 0), (4, 4, 4), WALL)[:-1]
    text = actor("Shell", "CSG_Add", five_faces) + box_brush("Wall", "CSG_Add", (10, 0, 0), (14, 4, 4), WALL)
    compiled = compile_text(text)
    assert [brush["name"] for brush in compiled.uncarved] == ["Shell"]
    assert {name for name, _, _ in compiled.triangles} == {"Wall"}
    assert volume(compiled.triangles) == pytest.approx(64)


def test_triangles_carry_the_brush_face_they_come_from():
    text = box_brush("Wall", "CSG_Add", (0, 0, 0), (4, 4, 4), WALL) + box_brush("Cut", "CSG_Subtract", (0, 0, 2), (4, 4, 6), ROOM)
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(32)
    assert compiled.estimated == 0
    assert {(name, face) for name, face, _ in compiled.triangles} <= {
        (name, index) for name in ("Wall", "Cut") for index in range(6)
    }
    lid = [face for name, face, tri in compiled.triangles if name == "Cut" and all(p[2] == 2 for p in tri)]
    assert lid and len(set(lid)) == 1
    sides = [face for name, face, tri in compiled.triangles if name == "Wall" and all(p[1] == 0 for p in tri)]
    assert sides and len(set(sides)) == 1


def test_coplanar_brushes_keep_their_own_faces():
    text = box_brush("Floor", "CSG_Add", (0, 0, 0), (8, 8, 1), FLOOR) + box_brush("Slab", "CSG_Add", (0, 0, 1), (8, 8, 2), ROOM)
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(128)
    top = [name for name, _, tri in compiled.triangles if all(p[2] == 2 for p in tri)]
    assert set(top) == {"Slab"}
    bottom = [name for name, _, tri in compiled.triangles if all(p[2] == 0 for p in tri)]
    assert set(bottom) == {"Floor"}


def test_a_coplanar_pair_only_divides_when_a_cut_reaches_the_shared_plane():
    text = (
        box_brush("Floor", "CSG_Add", (0, 0, 0), (8, 8, 1), FLOOR)
        + box_brush("Slab", "CSG_Add", (0, 0, 1), (8, 8, 2), ROOM)
        + box_brush("Cut", "CSG_Subtract", (2, 2, 1), (4, 4, 3), DOOR)
    )
    compiled = compile_text(text)
    assert volume(compiled.triangles) == pytest.approx(128 - 2 * 2 * 1)
    floor = [face for name, face, tri in compiled.triangles if name == "Floor" and all(p[2] == 1 for p in tri)]
    assert floor and len(set(floor)) == 1
    pocket = [name for name, _, tri in compiled.triangles if all(p[0] == 2 for p in tri)]
    assert set(pocket) == {"Cut"}


def textures(mesh):
    """Every brush texture the render meshes actually reference."""
    return {mesh["materials"][primitive["material"]]["name"] for item in mesh["meshes"][1:] for primitive in item["primitives"]}


def test_compiled_brush_geometry_reaches_the_render_and_collision_meshes(tmp_path):
    text = box_brush("Wall", "CSG_Add", (0, 0, 0), (40, 8, 64), WALL) + box_brush(
        "Door", "CSG_Subtract", (12, -2, 0), (28, 10, 40), DOOR
    )
    parsed = kf1.parse_brushes(text)
    heights = [[32768] * 2 for _ in range(2)]
    terrain = kf1.terrain_triangles(heights, kf1.ORIGIN, kf1.SCALE)
    approximate = kf1.unpack_map(tmp_path / "out", [], heights, terrain, parsed, csg=False)
    compiled = kf1.unpack_map(tmp_path / "out", [], heights, terrain, parsed, csg=True)
    for mesh in (approximate, compiled):
        rendered = sum(len(p["indices"]) for m in mesh["meshes"][1:] for p in m["primitives"])
        assert rendered == len(mesh["collision"]["indices"]) - 3 * len(terrain)
        assert rendered % 3 == 0
    for mesh in compiled["meshes"][1:]:
        for primitive in mesh["primitives"]:
            assert len(primitive["uv"]) * 3 == len(primitive["positions"]) * 2
    assert textures(approximate) == {WALL}
    assert textures(compiled) == {WALL, DOOR}
    assert {item["name"] for item in approximate["meshes"]} == {"Terrain", "Wall"}
    assert {item["name"] for item in compiled["meshes"]} == {"Terrain", "Wall", "Door"}
