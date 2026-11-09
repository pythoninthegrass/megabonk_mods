"""Tests for the frame-time sweep driver's sample gates, which decide what counts as a measurement."""

import perf_sweep
import pytest
from argparse import Namespace


def test_sweeper_uses_bepinex_log(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(perf_sweep.hb, "resolve_game_dir", lambda lookup: tmp_path)
    sweeper = perf_sweep.Sweeper(Namespace())
    assert sweeper.log == tmp_path / "BepInEx" / "LogOutput.log"
    assert sweeper.harness == tmp_path / "harness"


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
        "count_0_rendoff_r2",
        "count_0_rendon_r2",
        "count_0_rendon_r3",
        "count_0_rendoff_r3",
        "count_240_rendon_r1",
        "count_240_rendoff_r1",
        "count_240_rendoff_r2",
        "count_240_rendon_r2",
        "count_240_rendon_r3",
        "count_240_rendoff_r3",
    ]


def test_render_arms_hand_the_leading_arm_over_each_repeat() -> None:
    """A fixed arm order makes the always-second arm absorb the within-session drift the doc records."""
    arms = [render_on for _, _, render_on in perf_sweep.render_plan([240], 4)]

    assert arms == [True, False, False, True, True, False, False, True]


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


def test_a_window_asked_for_rendering_that_still_hid_renderers_is_suspect() -> None:
    reason = perf_sweep.render_suspect_reason({"_renderArm": "on", "_renderersOff": 240}, target=240)

    assert reason == "the render cull still disabled 240 renderers with rendering asked for"


def test_the_off_arm_asks_for_rendering_to_stop_and_the_on_arm_for_it_to_continue() -> None:
    assert perf_sweep.render_arm_payload(True) == {"action": "render", "enabled": True}
    assert perf_sweep.render_arm_payload(False) == {"action": "render", "enabled": False}


def test_a_player_at_the_fixed_point_at_window_start_is_not_suspect() -> None:
    assert perf_sweep.player_start_suspect_reason([0.0, 1.92, 0.0], (0.0, 1.92, 0.0)) is None
    assert perf_sweep.player_start_suspect_reason([0.4, 1.92, -0.4], (0.0, 1.92, 0.0)) is None
    # A swarm piled on the standing point shoves the player a few units during the settle; that is not a failed teleport.
    assert perf_sweep.player_start_suspect_reason([3.1, 1.92, -3.1], (0.0, 1.92, 0.0)) is None


def test_a_player_elsewhere_at_window_start_is_suspect() -> None:
    reason = perf_sweep.player_start_suspect_reason([24.0, 1.92, 0.0], (0.0, 1.92, 0.0))

    assert reason is not None
    assert "fixed point" in reason and "24.0" in reason


def test_a_missing_player_position_is_left_to_the_other_gates() -> None:
    assert perf_sweep.player_start_suspect_reason(None, (0.0, 1.92, 0.0)) is None
    assert perf_sweep.player_start_suspect_reason([0.0, 1.92, 0.0], None) is None


def test_the_cull_reports_its_own_cost_per_frame_from_the_window_ticks() -> None:
    report = {"frames": 2000, "ticks": [{"name": "KillFloor", "ms": 4.0}, {"name": "RenderCull", "ms": 12.0}]}

    assert perf_sweep.cull_ms_per_frame(report) == 0.006
    assert perf_sweep.cull_ms_per_frame({"frames": 2000, "ticks": []}) is None
    assert perf_sweep.cull_ms_per_frame({"frames": 0, "ticks": [{"name": "RenderCull", "ms": 1.0}]}) is None


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


# --- Engine-side A/B: the same interleaved arms for the kinematic-rigidbody and animation controls ---


def test_physics_arms_alternate_the_arms_within_every_repeat() -> None:
    windows = perf_sweep.control_plan([240], 3, "physics")

    assert [name for name, _, _ in windows] == [
        "count_240_physbase_r1",
        "count_240_physkin_r1",
        "count_240_physkin_r2",
        "count_240_physbase_r2",
        "count_240_physbase_r3",
        "count_240_physkin_r3",
    ]


def test_animation_arms_alternate_the_arms_within_every_repeat() -> None:
    windows = perf_sweep.control_plan([240], 2, "animation")

    assert [name for name, _, _ in windows] == [
        "count_240_animbase_r1",
        "count_240_animoff_r1",
        "count_240_animoff_r2",
        "count_240_animbase_r2",
    ]


def test_every_control_hands_the_leading_arm_over_each_repeat() -> None:
    """A fixed arm order makes the always-second arm absorb the within-session drift the doc records."""
    for control in ("render", "physics", "animation"):
        armed = [is_armed for _, _, is_armed in perf_sweep.control_plan([240], 4, control)]

        assert armed == [False, True, True, False, False, True, True, False]


def test_every_control_pairs_each_count_with_both_arms() -> None:
    for control in ("physics", "animation"):
        windows = perf_sweep.control_plan([0, 240], 2, control)

        assert {(target, is_armed) for _, target, is_armed in windows} == {(0, False), (0, True), (240, False), (240, True)}


def test_the_render_plan_is_the_render_control_of_the_same_machinery() -> None:
    """render_plan keeps its render-on convention; the general one names the arm that is armed, the inverse."""
    general = perf_sweep.control_plan([0, 240], 3, "render")
    legacy = perf_sweep.render_plan([0, 240], 3)

    assert [name for name, _, _ in general] == [name for name, _, _ in legacy]
    assert [(target, not render_on) for _, target, render_on in legacy] == [(target, armed) for _, target, armed in general]


def test_a_control_plan_that_arms_nothing_is_still_a_plan() -> None:
    """A sweep is free to measure the ordinary run alone, and the names must say which arm that is."""
    assert [name for name, _, armed in perf_sweep.control_plan([120], 2, "physics") if not armed] == [
        "count_120_physbase_r1",
        "count_120_physbase_r2",
    ]


def test_an_unknown_control_is_refused_rather_than_silently_measured() -> None:
    with pytest.raises(SystemExit, match="unknown control"):
        perf_sweep.control_plan([240], 1, "solver")


def test_the_physics_arms_leave_the_solver_or_take_the_bodies_out_of_it() -> None:
    assert perf_sweep.control_arm_payload("physics", False) == {"action": "physics", "enabled": True}
    assert perf_sweep.control_arm_payload("physics", True) == {"action": "physics", "enabled": False}


def test_the_animation_arms_keep_or_stop_the_animation_updates() -> None:
    assert perf_sweep.control_arm_payload("animation", False) == {"action": "animation", "enabled": True}
    assert perf_sweep.control_arm_payload("animation", True) == {"action": "animation", "enabled": False}


def test_the_render_arms_read_the_same_way_through_the_general_payload() -> None:
    """The general payload asks whether the control is armed; the render one asks whether rendering is wanted."""
    assert perf_sweep.control_arm_payload("render", armed=True) == perf_sweep.render_arm_payload(render_on=False)
    assert perf_sweep.control_arm_payload("render", armed=False) == perf_sweep.render_arm_payload(render_on=True)


def test_a_freeze_that_kinematicised_nothing_at_a_population_is_suspect() -> None:
    reason = perf_sweep.control_suspect_reason({"_controlArm": "physkin", "_controlState": {"rigidbodiesKinematic": 0}}, control="physics", target=240)

    assert reason == "the physics freeze kinematicised no rigidbodies at 240 enemies"


def test_a_freeze_that_kinematicised_bodies_with_no_enemies_is_suspect() -> None:
    reason = perf_sweep.control_suspect_reason({"_controlArm": "physkin", "_controlState": {"rigidbodiesKinematic": 6}}, control="physics", target=0)

    assert reason == "the physics freeze kinematicised 6 rigidbodies with no enemies alive"


def test_a_baseline_physics_window_still_holding_kinematic_bodies_is_suspect() -> None:
    reason = perf_sweep.control_suspect_reason({"_controlArm": "physbase", "_controlState": {"rigidbodiesKinematic": 240}}, control="physics", target=240)

    assert reason == "the physics freeze still kinematicised 240 rigidbodies with the solver asked for"


def test_a_healthy_physics_ab_is_not_suspect() -> None:
    assert (
        perf_sweep.control_suspect_reason({"_controlArm": "physkin", "_controlState": {"rigidbodiesKinematic": 240}}, control="physics", target=240)
        is None
    )
    assert (
        perf_sweep.control_suspect_reason({"_controlArm": "physbase", "_controlState": {"rigidbodiesKinematic": 0}}, control="physics", target=240)
        is None
    )
    assert perf_sweep.control_suspect_reason({"_controlArm": "physbase", "_controlState": {"rigidbodiesKinematic": 0}}, control="physics", target=0) is None


def test_an_animation_cull_that_stopped_nothing_at_a_population_is_suspect() -> None:
    reason = perf_sweep.control_suspect_reason(
        {"_controlArm": "animoff", "_controlState": {"behavioursOff": 0}}, control="animation", target=240
    )

    assert reason == "the animation cull stopped no animation components at 240 enemies"


def test_an_animation_cull_that_stopped_components_with_no_enemies_is_suspect() -> None:
    reason = perf_sweep.control_suspect_reason(
        {"_controlArm": "animoff", "_controlState": {"behavioursOff": 3}}, control="animation", target=0
    )

    assert reason == "the animation cull stopped 3 animation components with no enemies alive"


def test_a_baseline_animation_window_still_holding_a_cull_is_suspect() -> None:
    reason = perf_sweep.control_suspect_reason(
        {"_controlArm": "animbase", "_controlState": {"behavioursOff": 240}}, control="animation", target=240
    )

    assert reason == "the animation cull still stopped 240 animation components with animation asked for"


def test_a_window_with_a_second_control_armed_is_suspect() -> None:
    """Two armed controls measure neither of them: the window is the A/B of both at once."""
    reason = perf_sweep.other_control_suspect_reason(
        {"physicsFreeze": {"armed": True}, "animationCull": {"armed": True}, "renderCull": {"armed": False}}, "physics"
    )

    assert reason is not None
    assert "animation" in reason and "render" not in reason


def test_one_armed_control_in_a_window_is_not_suspect() -> None:
    only_mine = {"physicsFreeze": {"armed": True}, "animationCull": {"armed": False}, "renderCull": {"armed": False}}

    assert perf_sweep.other_control_suspect_reason(only_mine, "physics") is None
    assert perf_sweep.other_control_suspect_reason({"renderCull": {"armed": True}, "physicsFreeze": {"armed": False}}, "render") is None
    assert perf_sweep.other_control_suspect_reason({"physicsFreeze": {"armed": True}, "renderCull": {"armed": False}}, "render") is not None


def test_the_freeze_and_the_animation_cull_report_their_own_cost_per_frame() -> None:
    report = {"frames": 2000, "ticks": [{"name": "PhysicsFreeze", "ms": 8.0}, {"name": "AnimationCull", "ms": 2.0}]}

    assert perf_sweep.tick_ms_per_frame(report, "PhysicsFreeze") == 0.004
    assert perf_sweep.tick_ms_per_frame(report, "AnimationCull") == 0.001
    assert perf_sweep.tick_ms_per_frame(report, "KillFloor") is None
    assert perf_sweep.cull_ms_per_frame({"frames": 2000, "ticks": [{"name": "RenderCull", "ms": 12.0}]}) == 0.006


def test_the_fidelity_probes_are_read_per_frame_so_a_drop_in_ai_work_is_visible() -> None:
    report = {
        "frames": 1000,
        "probes": [
            {"name": "Enemy.MyFixedUpdate", "ms": 250.0},
            {"name": "EnemyMovementRb.MyFixedUpdate", "ms": 80.0},
            {"name": "AnimatedMesh.Update", "ms": 40.0},
            {"name": "EnemyManager.FixedUpdate", "ms": 280.0},
            {"name": "MinimapUi.Update", "ms": 5.0},
        ],
    }

    assert perf_sweep.probes_ms_per_frame(report) == {
        "Enemy.MyFixedUpdate": 0.25,
        "EnemyMovementRb.MyFixedUpdate": 0.08,
        "AnimatedMesh.Update": 0.04,
        "EnemyManager.FixedUpdate": 0.28,
    }


def test_a_probe_that_never_ran_is_reported_as_nothing_rather_than_missing() -> None:
    assert perf_sweep.probes_ms_per_frame({"frames": 1000, "probes": []}) == {name: 0.0 for name in perf_sweep.FIDELITY_PROBES}
    assert perf_sweep.probes_ms_per_frame({"frames": 0, "probes": []}) == {}


def test_the_control_arm_flags_need_a_positive_repeat_count() -> None:
    for flag in ("--physics-arms", "--anim-arms"):
        with pytest.raises(SystemExit):
            perf_sweep.parse_args([flag, "0"])
        with pytest.raises(SystemExit):
            perf_sweep.parse_args([flag, "-1"])

    assert perf_sweep.parse_args(["--physics-arms", "3"]).physics_arms == 3
    assert perf_sweep.parse_args(["--anim-arms", "3"]).anim_arms == 3


def test_each_control_arm_flag_names_its_own_control() -> None:
    assert perf_sweep.parse_args(["--physics-arms", "3"]).control == "physics"
    assert perf_sweep.parse_args(["--anim-arms", "3"]).control == "animation"
    assert perf_sweep.parse_args(["--render-arms", "3"]).control == "render"


def test_only_one_control_can_be_abaed_in_a_sweep() -> None:
    """Two armed controls in one window measure neither, so the flags are mutually exclusive."""
    with pytest.raises(SystemExit):
        perf_sweep.parse_args(["--render-arms", "3", "--physics-arms", "3"])
    with pytest.raises(SystemExit):
        perf_sweep.parse_args(["--physics-arms", "3", "--anim-arms", "3"])


def test_no_control_arms_means_no_control_and_the_count_ladder() -> None:
    args = perf_sweep.parse_args([])

    assert args.control is None
    assert args.render_arms is None and args.physics_arms is None and args.anim_arms is None
