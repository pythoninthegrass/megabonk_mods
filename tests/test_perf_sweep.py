"""Tests for the frame-time sweep driver's sample gates, which decide what counts as a measurement."""

import perf_sweep
import pytest


def report(**fields) -> dict:
    """A 20-second window that passes every gate, with whatever fields a test cares about replaced."""
    base = {
        "frames": 5000,
        "pausedFrames": 0,
        "paused": False,
        "vSyncCount": 0,
        "enemiesMin": 120,
        "enemiesMax": 120,
        "meanMs": 5.0,
    }
    base.update(fields)
    return base


def test_clean_window_has_nothing_to_fix() -> None:
    assert perf_sweep.discard_reasons(report(), window_seconds=20.0, min_fps=30) == []


def test_paused_frames_make_a_window_unusable() -> None:
    reasons = perf_sweep.discard_reasons(report(pausedFrames=784), window_seconds=20.0, min_fps=30)

    assert reasons == ["784 paused frames were UI frames"]


def test_a_window_that_stopped_rendering_is_unusable() -> None:
    reasons = perf_sweep.discard_reasons(report(frames=100), window_seconds=20.0, min_fps=30)

    assert reasons == ["only 100 sampled frames in 20.0 s at 30 fps minimum"]


def test_vsync_returning_mid_window_invalidates_the_sample() -> None:
    reasons = perf_sweep.discard_reasons(report(vSyncCount=1), window_seconds=20.0, min_fps=30)

    assert reasons == ["vsync came back on"]


def test_a_paused_run_with_no_paused_frames_reported_is_inconsistent() -> None:
    reasons = perf_sweep.discard_reasons(report(paused=True), window_seconds=20.0, min_fps=30)

    assert reasons == ["the run is paused but no paused frames were recorded"]


def test_every_problem_is_reported_together() -> None:
    reasons = perf_sweep.discard_reasons(
        report(pausedFrames=3, frames=10, vSyncCount=1, paused=True), window_seconds=20.0, min_fps=30
    )

    assert len(reasons) == 4


def test_a_thinned_population_makes_a_window_suspect() -> None:
    assert perf_sweep.suspect_reason(report(enemiesMax=86), target=120) == "only 86 of 120 enemies were alive"


def test_a_population_within_the_tolerance_is_not_suspect() -> None:
    assert perf_sweep.suspect_reason(report(enemiesMax=96), target=120) is None
    assert perf_sweep.suspect_reason(report(enemiesMax=0), target=0) is None


def test_windows_are_one_per_count_plus_the_mod_controls_at_the_top_count() -> None:
    plan = perf_sweep.plan([0, 40, 240])

    assert plan == [
        ("count_0", 0),
        ("count_40", 40),
        ("count_240", 240),
        ("count_240_modoff", 240),
        ("count_240_reenabled", 240),
    ]


def test_the_controls_follow_the_largest_count_whatever_order_the_counts_came_in() -> None:
    plan = perf_sweep.plan([240, 40, 120])

    assert [name for name, _ in plan] == [
        "count_240",
        "count_40",
        "count_120",
        "count_240_modoff",
        "count_240_reenabled",
    ]
    assert [target for _, target in plan[-2:]] == [240, 240]


def test_a_single_count_still_gets_its_own_controls() -> None:
    assert [name for name, _ in perf_sweep.plan([80])] == [
        "count_80",
        "count_80_modoff",
        "count_80_reenabled",
    ]


def test_origin_reads_the_player_position_from_a_state_report() -> None:
    assert perf_sweep.origin_from_state({"player": {"position": [-8.0, 0.6, -9.8]}}) == (-8.0, 0.6, -9.8)


def test_origin_needs_a_live_player() -> None:
    with pytest.raises(SystemExit, match="live player"):
        perf_sweep.origin_from_state({"player": None})
    with pytest.raises(SystemExit, match="live player"):
        perf_sweep.origin_from_state({})


def test_a_thinned_window_is_flagged_not_thrown_away() -> None:
    """Enemies die during a fight, so a thin population is a caveat on the sample rather than a reason to lose it."""
    thin = report(enemiesMax=40)

    assert perf_sweep.discard_reasons(thin, window_seconds=20.0, min_fps=30) == []
    assert perf_sweep.suspect_reason(thin, target=240) is not None
