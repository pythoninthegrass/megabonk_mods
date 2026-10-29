"""
Self-test for scripts/warehouse_surface.py, on synthetic triangles.
"""

import math
import pytest
import warehouse_surface as ws

FLOOR = ((0, 0, 0), (10, 0, 0), (0, 0, 10))
FLOOR_FAR = ((10, 0, 10), (0, 0, 10), (10, 0, 0))
SHELF = ((0, 5, 0), (10, 5, 0), (0, 5, 10))


def test_drop_returns_the_height_and_upward_normal_of_the_triangle_below() -> None:
    hit = ws.drop([FLOOR], 2, 3, 2)
    assert hit is not None
    assert hit.y == pytest.approx(0)
    assert hit.normal == pytest.approx((0, 1, 0))
    assert hit.index == 0


def test_drop_takes_the_highest_triangle_at_or_below_the_start() -> None:
    assert ws.drop([FLOOR, SHELF], 2, 8, 2).y == pytest.approx(5)
    assert ws.drop([FLOOR, SHELF], 2, 4, 2).y == pytest.approx(0)


def test_drop_misses_when_nothing_is_below_or_beside() -> None:
    assert ws.drop([FLOOR], 2, -1, 2) is None
    assert ws.drop([FLOOR], 20, 3, 2) is None


def test_drop_gives_the_normal_of_a_sloped_triangle_pointing_up() -> None:
    ramp = ((0, 0, 0), (10, 5, 0), (0, 0, 10))
    hit = ws.drop([ramp], 5, 50, 1)
    assert hit.y == pytest.approx(2.5)
    assert hit.normal[1] > 0
    assert math.hypot(*hit.normal) == pytest.approx(1)
    assert hit.normal[0] == pytest.approx(-5 / math.hypot(5, 10))


def test_a_flat_surface_leaves_the_item_upright_at_the_authored_pitch() -> None:
    assert ws.unity_euler(ws.item_rotation((0, 1, 0), 0)) == pytest.approx((270, 0, 0))


@pytest.mark.parametrize("normal", [(0, 1, 0), (0.3, 0.9, 0.1), (-0.5, 0.8, 0.2), (0.1, 0.7, -0.6)])
@pytest.mark.parametrize("yaw", [0, 40, 270])
def test_unity_euler_reproduces_the_item_rotation(normal: tuple, yaw: float) -> None:
    n = tuple(c / math.hypot(*normal) for c in normal)
    rotation = ws.item_rotation(n, yaw)
    back = ws.euler_matrix(*ws.unity_euler(rotation))
    for row, expected in zip(back, rotation, strict=True):
        assert row == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("normal", [(0, 1, 0), (0.3, 0.9, 0.1), (-0.5, 0.8, 0.2)])
def test_the_prefab_up_axis_follows_the_surface_normal(normal: tuple) -> None:
    n = tuple(c / math.hypot(*normal) for c in normal)
    rotation = ws.item_rotation(n, 25)
    prefab_up = tuple(rotation[row][2] for row in range(3))
    assert prefab_up == pytest.approx(n, abs=1e-6)


def test_a_box_resting_on_a_triangle_does_not_overlap_it() -> None:
    upright = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert ws.box_hits([FLOOR], (3, 1.05, 3), upright, (1, 1, 1)) == []


def test_a_box_sunk_into_a_triangle_overlaps_it() -> None:
    upright = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert ws.box_hits([FLOOR], (3, 0.5, 3), upright, (1, 1, 1)) == [0]


def test_a_box_hits_a_triangle_above_it_and_beside_it() -> None:
    upright = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert ws.box_hits([FLOOR, SHELF], (3, 3.5, 3), upright, (1, 1.6, 1)) == [1]
    wall = ((5, 0, 0), (5, 4, 0), (5, 0, 10))
    assert ws.box_hits([wall], (4.5, 2, 3), upright, (1, 1, 1)) == [0]


def test_a_box_beside_a_triangle_without_touching_it_is_clear() -> None:
    upright = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    wall = ((5, 0, 0), (5, 4, 0), (5, 0, 10))
    assert ws.box_hits([wall], (3, 2, 3), upright, (1, 1, 1)) == []


def gable(x0: float, x1: float, z: float = 0.0, ridge: float = 4.0) -> list[ws.Triangle]:
    """A roof ridge along x at height `ridge`, falling to height 0 a metre either side in z."""
    return [
        ((x0, ridge, z), (x1, ridge, z), (x0, 0, z - 1)),
        ((x1, ridge, z), (x1, 0, z - 1), (x0, 0, z - 1)),
        ((x0, ridge, z), (x0, 0, z + 1), (x1, ridge, z)),
        ((x1, ridge, z), (x0, 0, z + 1), (x1, 0, z + 1)),
    ]


def test_ridge_runs_finds_the_edge_where_two_faces_fall_away_opposite_ways() -> None:
    [(start, end)] = ws.ridge_runs(gable(0, 10))
    assert sorted([start, end]) == [(0, 4, 0), (10, 4, 0)]


def test_ridge_runs_merges_collinear_edges_into_one_run() -> None:
    [(start, end)] = ws.ridge_runs(gable(0, 10) + gable(10, 25))
    assert sorted([start, end]) == [(0, 4, 0), (25, 4, 0)]


def test_ridge_runs_ignores_a_valley_a_flat_floor_and_a_gentle_ridge() -> None:
    valley = [((0, 0, 0), (10, 0, 0), (0, 4, -1)), ((10, 0, 0), (10, 4, -1), (0, 4, -1)), ((0, 0, 0), (0, 4, 1), (10, 0, 0)), ((10, 0, 0), (0, 4, 1), (10, 4, 1))]
    assert ws.ridge_runs(valley) == []
    assert ws.ridge_runs([FLOOR, FLOOR_FAR]) == []
    assert ws.ridge_runs(gable(0, 10, ridge=0.2)) == []


def test_ridge_runs_ignores_runs_shorter_than_the_minimum() -> None:
    assert ws.ridge_runs(gable(0, 1.5)) == []


def hip(x1: float, drop: float) -> list[ws.Triangle]:
    """A ridge from (0, 4, 0) falling `drop` over x1, with faces falling away a metre either side in z."""
    return [
        ((0, 4, 0), (x1, 4 - drop, 0), (0, 0, -1)),
        ((x1, 4 - drop, 0), (x1, 0, -1), (0, 0, -1)),
        ((0, 4, 0), (0, 0, 1), (x1, 4 - drop, 0)),
        ((x1, 4 - drop, 0), (0, 0, 1), (x1, 0, 1)),
    ]


def test_ridge_runs_follows_a_ridge_that_falls_along_its_length() -> None:
    [(start, end)] = ws.ridge_runs(hip(10, 2.5))
    assert sorted([start, end]) == [(0, 4, 0), (10, 1.5, 0)]


def test_ridge_runs_ignores_a_ridge_steeper_than_the_grade_limit() -> None:
    assert ws.ridge_runs(hip(10, 8)) == []


DECK = ((0, 5, 5), (10, 5, 5), (0, 5, 15))
RAMP = [((0, 0, 0), (10, 0, 0), (0, 5, 5)), ((10, 0, 0), (10, 5, 5), (0, 5, 5))]


def test_lip_runs_finds_the_top_of_a_ramp_that_meets_a_flat_deck() -> None:
    [(start, end)] = ws.lip_runs([*RAMP, DECK])
    assert sorted([start, end]) == [(0, 5, 5), (10, 5, 5)]


def test_lip_runs_ignores_the_foot_of_a_ramp_where_it_meets_the_floor() -> None:
    floor = ((0, 0, 0), (10, 0, 0), (0, 0, -10))
    assert [r for r in ws.lip_runs([*RAMP, floor]) if r[0][1] == 0] == []


def test_lip_runs_ignores_a_ramp_that_meets_a_wall() -> None:
    wall = ((0, 5, 5), (10, 5, 5), (0, 15, 5))
    assert ws.lip_runs([*RAMP, wall]) == []


def test_lip_runs_still_finds_a_ridge() -> None:
    [(start, end)] = ws.lip_runs(gable(0, 10))
    assert sorted([start, end]) == [(0, 4, 0), (10, 4, 0)]


def test_lip_runs_joins_a_ridge_to_the_deck_edge_it_continues_into() -> None:
    ridge = gable(10, 20, z=5, ridge=5)
    [(start, end)] = ws.lip_runs([*RAMP, DECK, *ridge])
    assert sorted([start, end]) == [(0, 5, 5), (20, 5, 5)]


LEDGE_TOP = ((0, 5, 0), (10, 5, 0), (0, 5, 10))
LEDGE_FACE = ((0, 5, 0), (10, 5, 0), (0, 0, 0))


def test_ledge_runs_finds_the_top_edge_of_a_deck_over_a_vertical_face() -> None:
    [(start, end)] = ws.ledge_runs([LEDGE_TOP, LEDGE_FACE])
    assert sorted([start, end]) == [(0, 5, 0), (10, 5, 0)]


def test_ledge_runs_ignores_the_foot_of_a_wall_where_it_meets_a_floor() -> None:
    floor = ((0, 0, 0), (10, 0, 0), (0, 0, -10))
    assert ws.ledge_runs([LEDGE_FACE, floor]) == []


def test_ledge_runs_ignores_a_ramp_meeting_a_deck() -> None:
    assert ws.ledge_runs([*RAMP, DECK]) == []


def test_ledge_runs_merges_collinear_edges() -> None:
    second = ((10, 5, 0), (20, 5, 0), (10, 5, 10))
    second_face = ((10, 5, 0), (20, 5, 0), (10, 0, 0))
    [(start, end)] = ws.ledge_runs([LEDGE_TOP, LEDGE_FACE, second, second_face])
    assert sorted([start, end]) == [(0, 5, 0), (20, 5, 0)]


def test_lip_runs_treats_a_double_sided_mesh_like_a_single_sided_one() -> None:
    doubled = [*RAMP, DECK, *[(t[0], t[2], t[1]) for t in [*RAMP, DECK]]]
    [(start, end)] = ws.lip_runs(doubled)
    assert sorted([start, end]) == [(0, 5, 5), (10, 5, 5)]


def test_ridge_runs_and_ledge_runs_treat_a_double_sided_mesh_like_a_single_sided_one() -> None:
    both = lambda tris: [*tris, *[(t[0], t[2], t[1]) for t in tris]]  # noqa: E731
    assert len(ws.ridge_runs(both(gable(0, 10)))) == 1
    assert len(ws.ledge_runs(both([LEDGE_TOP, LEDGE_FACE]))) == 1
