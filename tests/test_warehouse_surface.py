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
