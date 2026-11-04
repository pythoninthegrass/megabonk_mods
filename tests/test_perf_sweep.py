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
        ("count_0", 0, None),
        ("count_40", 40, None),
        ("count_240", 240, None),
        ("count_240_modoff", 240, None),
        ("count_240_reenabled", 240, None),
    ]


def test_the_controls_follow_the_largest_count_whatever_order_the_counts_came_in() -> None:
    plan = perf_sweep.plan([240, 40, 120])

    assert [name for name, _, _ in plan] == [
        "count_240",
        "count_40",
        "count_120",
        "count_240_modoff",
        "count_240_reenabled",
    ]
    assert [target for _, target, _ in plan[-2:]] == [240, 240]


def test_a_single_count_still_gets_its_own_controls() -> None:
    assert [name for name, _, _ in perf_sweep.plan([80])] == [
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


# --- density A/B: gathered is the swarm at the player, strung leaves the player a fixed offset away ---


def test_strung_position_moves_the_player_downstream_along_x() -> None:
    assert perf_sweep.strung_position((-8.0, 0.6, -9.8), 150.0) == (142.0, 0.6, -9.8)


def test_strung_position_with_a_zero_offset_is_the_origin() -> None:
    assert perf_sweep.strung_position((-8.0, 0.6, -9.8), 0.0) == (-8.0, 0.6, -9.8)


def test_density_defaults_to_gathered_with_no_captures() -> None:
    args = perf_sweep.parse_args(["--count", "0"])

    assert args.density == "gathered"
    assert args.strung_offset == 150.0
    assert args.captures == 0
    assert str(args.capture_dir) == "/tmp/RenderDoc"


def test_density_flag_accepts_strung() -> None:
    args = perf_sweep.parse_args(["--density", "strung"])

    assert args.density == "strung"


def test_counts_replace_the_default_ladder() -> None:
    """--count names the whole ladder: passing two counts must not measure the untouched seven as well."""
    assert perf_sweep.parse_args(["--count", "0", "--count", "240"]).counts == [0, 240]


def test_counts_default_to_the_full_ladder() -> None:
    assert perf_sweep.parse_args([]).counts == list(perf_sweep.DEFAULT_COUNTS)


def test_density_flag_rejects_unknown_densities() -> None:
    with pytest.raises(SystemExit):
        perf_sweep.parse_args(["--density", "bunched"])


def test_launch_cmd_defaults_to_the_taskfile_launch() -> None:
    assert perf_sweep.parse_args(["--count", "0"]).launch_cmd is None


def test_launch_cmd_overrides_the_game_launch() -> None:
    args = perf_sweep.parse_args(["--launch-cmd", "systemctl --user restart megabonk-034"])

    assert args.launch_cmd == "systemctl --user restart megabonk-034"


# --- RenderDoc capture pairing: new .rdc files in the capture dir belong to the window that triggered them ---


def test_capture_trigger_is_an_f12_keypress_for_the_menu_driver() -> None:
    assert perf_sweep.capture_trigger_batch() == [["key", "KEY_F12"]]


def test_pair_captures_takes_only_new_rdc_files_in_capture_order() -> None:
    assert perf_sweep.pair_captures({}, {"b.rdc": 2.0, "a.rdc": 5.0}) == ["b.rdc", "a.rdc"]


def test_pair_captures_ignores_preexisting_files() -> None:
    before = {"old.rdc": 1.0}
    after = {"old.rdc": 1.0, "new.rdc": 2.0}

    assert perf_sweep.pair_captures(before, after) == ["new.rdc"]


def test_pair_captures_ignores_files_that_are_not_captures() -> None:
    assert perf_sweep.pair_captures({}, {"log.txt": 9.0, "frame1.rdc.tmp": 3.0}) == []


# --- Render-only A/B: interleaved on/off arms per count, gated like every other window ---


def test_render_arms_alternate_the_arms_within_every_repeat() -> None:
    windows = perf_sweep.render_plan([0, 240], 3)

    assert [name for name, _, _ in windows] == [
        "count_0_rendon_r1",
        "count_0_rendoff_r1",
        "count_0_rendon_r2",
        "count_0_rendoff_r2",
        "count_0_rendon_r3",
        "count_0_rendoff_r3",
        "count_240_rendon_r1",
        "count_240_rendoff_r1",
        "count_240_rendon_r2",
        "count_240_rendoff_r2",
        "count_240_rendon_r3",
        "count_240_rendoff_r3",
    ]


def test_render_arms_pair_every_count_with_both_arms() -> None:
    windows = perf_sweep.render_plan([0, 120, 240], 2)

    assert {(target, render_on) for _, target, render_on in windows} == {
        (0, True),
        (0, False),
        (120, True),
        (120, False),
        (240, True),
        (240, False),
    }


def test_render_arms_keep_the_toggles_untouched_outside_the_mode() -> None:
    windows = perf_sweep.plan([0, 240])

    assert all(render_on is None for _, _, render_on in windows)


def test_a_cull_that_disabled_no_renderers_at_a_population_is_suspect() -> None:
    reason = perf_sweep.render_suspect_reason({"_renderArm": "off", "_renderersOff": 0}, target=240)

    assert reason == "the render cull disabled no renderers at 240 enemies"


def test_a_cull_that_disabled_renderers_with_no_enemies_is_suspect() -> None:
    reason = perf_sweep.render_suspect_reason({"_renderArm": "off", "_renderersOff": 5}, target=0)

    assert reason == "the render cull disabled 5 renderers with no enemies alive"


def test_healthy_render_arms_are_not_suspect() -> None:
    assert perf_sweep.render_suspect_reason({"_renderArm": "off", "_renderersOff": 480}, target=240) is None
    assert perf_sweep.render_suspect_reason({"_renderArm": "on", "_renderersOff": 0}, target=240) is None
    assert perf_sweep.render_suspect_reason({"_renderArm": "off", "_renderersOff": 0}, target=0) is None


def test_render_arms_needs_a_positive_repeat_count() -> None:
    with pytest.raises(SystemExit):
        perf_sweep.parse_args(["--render-arms", "0"])
    with pytest.raises(SystemExit):
        perf_sweep.parse_args(["--render-arms", "-1"])

    assert perf_sweep.parse_args(["--render-arms", "3"]).render_arms == 3


def test_render_arms_default_to_off_and_take_the_count_ladder() -> None:
    assert perf_sweep.parse_args([]).render_arms is None


def test_the_startup_warning_dismissal_is_an_enter_keypress_for_the_menu_driver() -> None:
    assert perf_sweep.startup_dismiss_batch() == [["key", "KEY_ENTER"]]
