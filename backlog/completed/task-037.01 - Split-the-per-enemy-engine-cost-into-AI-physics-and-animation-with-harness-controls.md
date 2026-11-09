---
id: TASK-037.01
title: >-
  Split the per-enemy engine cost into AI, physics and animation with harness
  controls
status: Done
assignee: []
created_date: '2026-11-04 06:31'
updated_date: '2026-11-04 07:33'
labels: []
dependencies:
  - TASK-037
documentation:
  - docs/performance.md#attributing-the-per-enemy-cost
  - docs/development.md#frame-time-profiling
  - src/MegabonkLevels.Mod/enemy_render_cull.cs
  - src/MegabonkLevels.Mod/enemy_render_cull_plan.cs
modified_files:
  - docs/performance.md
  - docs/development.md
  - src/
  - scripts/
  - tests/
parent_task_id: TASK-037
priority: medium
ordinal: 153000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: docs/performance.md now attributes the per-enemy frame cost to engine work - the render-only A/B bounds enemy draw submission at <=0.7 ms/frame at 240 enemies (pair deltas -0.61 to +0.66 ms in the clean leg, inside the ~0.8 ms session-to-session offset) while hiding them removes 93-96% of the enemy-attributable submitted vertices. Everything that clears the offset, +4.06 to +4.65 ms over the same leg's 0-enemy window in that protocol (17-19 us per enemy), sits in the engine's per-enemy update on the main and physics threads. The doc cannot yet say which of three things dominates - per-enemy AI state work, the Rigidbody under Unity's physics solver, or animation beyond the probed AnimatedMesh.Update - so nobody knows which lever is worth pulling, and the doc's open item says exactly that.

What: two more harness controls beside the existing perf render verb, on the same pattern, then the same gated-window A/B against a 240-enemy population: (a) make the live enemies' Rigidbodies kinematic, which takes them out of the solver while leaving AI and animation running, and (b) stop the enemies' animator/animated-mesh updates while leaving renderers and physics running. Each is a Renderer.enabled-style toggle on live enemies (EnemyManager.Instance.enemies.Values), restoring exactly what it changed, with the decision logic in a pure plan class like EnemyRenderCullPlan, its own ungated PerfTick so a toggle-all-off control arm cannot strand it, a perf verb, and status/report fields proving the state. perf reset must restore both. Reuse the existing Harmony probe set (Enemy.MyFixedUpdate, EnemyMovementRb.MyFixedUpdate, AnimatedMesh.Update, EnemyManager.FixedUpdate) - do not add new patches.

Handoff context an implementer needs: the render-only work established that a control is only as good as its fidelity evidence, so each new control has to show what else it suppresses, not just what it disables. Making 240 Rigidbodies kinematic also removes their contacts and broadphase work, which is part of what the physics figure means - say so in the doc rather than calling it a pure solver measurement. Stopping animation updates may change how far the swarm actually reaches the player, which changes AI work; if the enemy count or the position-sum drift differs between arms, the A/B is not like-for-like and the doc has to record it. The render A/B also carries a caveat worth not repeating: Unity culls animator updates by renderer visibility, which is why that split attributes at most 0.039 ms/frame (the probed AnimatedMesh.Update) to animation.

Measurement rules that apply, all of them already paid for: run legs with --tier 4 --seed 20261102 (levels/example-forest.mblevel.json carries tier 0 and --tier defaults to the level's own value, so omitting it measures a different protocol); interleave the arms and flip the leading arm every repeat, because cost walks upward through a session and an always-second arm absorbs that drift; at least 3 repeats per arm reported as ranges; a delta that does not clear the ~0.8 ms session offset is inconclusive, not a number; every window pausedFrames == 0 with the player teleported to the fixed point (the window JSON's _playerAtOrigin/_origin is the audit, 8 units is the crowd-shove tolerance); report each control's own ms/frame from its tick, and its effect on enemy count. The harness does not serve perf verbs while the game is in editor mode - commands time out. Scripts and gates are in scripts/perf_sweep.py; the protocol and its traps are in docs/development.md#frame-time-profiling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness control makes the live enemies' Rigidbodies kinematic and another stops their animator/animated-mesh updates; each restores exactly what it changed, status and report carry their state, and perf reset restores both
- [x] #2 Decision logic lives in pure plan classes with unit tests, following EnemyRenderCullPlan (no Unity APIs in the decision layer); the sweep gains arms for each control alongside --render-arms
- [x] #3 Each control reports its fidelity in-game: enemy count with it armed against unarmed, position-sum drift, and a written statement of what else it suppresses (contacts and broadphase for kinematic, AI reach for animation)
- [x] #4 A gated-window A/B per control at 0 and 240 enemies, arms interleaved with the leading arm flipped each repeat, at least 3 repeats per arm, tier 4, seed 20261102, every window pausedFrames == 0 and the player within 8 units of the fixed point at window start
- [x] #5 Each arm reported as a range with pair deltas and the ~0.8 ms session offset stated, any delta below it labelled inconclusive, and each control's own ms/frame reported
- [x] #6 docs/performance.md's open item is replaced by the measured AI-versus-physics-versus-animation split, or by the bounded result plus why it is bounded; no new Harmony patches beyond the existing probe set
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach (approved with maintainer 2026-11-04)

Base: TASK-037's branch was merged into main as a plumbing merge commit (git merge-tree + commit-tree, pushed to origin main as 767a365) rather than a local merge, because the primary checkout holds another agent's uncommitted TASK-040 work whose tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj collides with 037's edit to the same file. Local main in that checkout is untouched and catches up when that work is committed.

Worktree: /Users/maintainer/git/megabonk_mods-037.01 on branch perf-037-01-engine-split, based on the merge commit. .env is a symlink into the primary checkout; every other gitignored file is an APFS clone copy (.tools, tools/ost, unity/pack-authoring/Assets/Thps, steamstub dll, CLAUDE.local.md); .venv is a fresh uv sync rather than a copy, because a copied venv keeps shebangs pointing at the primary checkout. Baseline green: pytest 1189 passed/29 skipped, xUnit 1810 passed. Local builds run with -p:ModInstanceFolder=<worktree>/.build-deploy so a build here does not overwrite the shared CrossOver Mods folder another agent may be using. The DLL under test is built here and scp'd to the player box's Mods.

1. Tests first (TDD): tests/test_perf_sweep.py cases for control_plan per control (strict alternation, leading arm flipped each repeat, names, counts), control_arm_payload direction, control-aware suspect rules (armed control that changed nothing at a population, changed something at zero, a baseline arm still holding state, two controls armed at once), mutual exclusion of the new arm flags, tick_ms_per_frame; tests/MegabonkLevels.Tests/enemy_physics_freeze_plan_tests.cs and enemy_animation_cull_plan_tests.cs; perf_command_tests.cs cases for the two new actions; test_mcp_server.py perf cases.
2. src/MegabonkLevels.Mod/enemy_physics_freeze.cs + enemy_physics_freeze_plan.cs: Rigidbody.isKinematic=true on every Rigidbody under the live enemies (EnemyManager.Instance.enemies.Values, GetComponentsInChildren<Rigidbody>(true)), tracked instance-id -> prior isKinematic so restore puts back exactly what it found; rescan on population change or 0.5 s, same policy as the render cull. Plan class holds arm sense, rescan policy, which bodies to set (only ones currently dynamic), restore mapping, and the suppresses statement (solver plus contacts, broadphase, and anything that moves the body through rb.velocity).
3. src/MegabonkLevels.Mod/enemy_animation_cull.cs + enemy_animation_cull_plan.cs: Behaviour.enabled=false on the enemies' AnimatedMesh and Animator components with renderers left on, tracked prior enabled, per-type counts so the doc can say what was actually found on an enemy.
4. perf_monitor.cs: PerfTick.PhysicsFreeze and PerfTick.AnimationCull, both in IsUngated like RenderCull so toggle-all-off cannot strand an armed A/B, driven from Tick() through Timed; SetEnemyPhysics/SetEnemyAnimation; status and report gain physicsFreeze{armed,rigidbodiesKinematic} and animationCull{armed,behavioursOff,animatedMeshOff,animatorOff} each with its suppresses list; Reset() restores both and reports physicsFreezeRestored/animationCullRestored.
5. Wire the verbs: harness_command.cs allowed perf actions (physics, animation, both requiring enabled), dev_harness.cs RunPerf routing, run.py PERF_ACTIONS plus the --enable/--disable help, mcp_server.py perf docstring and enabled validation.
6. scripts/perf_sweep.py: generalize the render-arm machinery to control_plan(counts, repeats, control), control_arm_payload(control, armed), tick_ms_per_frame(report, tick); new --physics-arms N and --anim-arms N beside --render-arms, mutually exclusive; each window records _control, _controlArm, the control's own counters, its tick ms/frame, the four existing probes' ms/frame and the position-sum pair; the other controls are explicitly disarmed before one is armed and all are restored in finally. No new Harmony patches: fidelity comes from the existing Enemy.MyFixedUpdate / EnemyMovementRb.MyFixedUpdate / AnimatedMesh.Update / EnemyManager.FixedUpdate probes plus the position sum and enemy counts.
7. Legs on the player box (tailscale-only host, its own worktree on this branch, .env and .venv symlinked, DLL scp'd): tier 4, seed 20261102, levels/example-forest.mblevel.json, 0 and 240 enemies, >=3 repeats per arm, interleaved with the leading arm flipped each repeat, 20 s gated windows, pausedFrames == 0, player within 8 units of the fixed point, vsync off, spawns off, one session per control. Report each arm as a range with pair deltas against the ~0.8 ms session offset, label anything below it inconclusive, and give each control's own ms/frame.
8. Docs: docs/development.md perf verb rows and an engine-side A/B section for the new flags and fidelity fields; docs/performance.md's open item replaced by the measured AI-versus-physics-versus-animation split, or by the bound plus why it is bounded. Confounds recorded, not hidden: a kinematic swarm may stop translating if the game drives movement through rb.velocity, which makes that figure solver plus contacts, broadphase and movement rather than a pure solver number; if the animation arm changes how far the swarm reaches the player, the A/B is not like-for-like and the position-sum drift says so.
9. Close: task check (build, installer test skip, dotnet test, pytest, lint), conventional commits with no attribution, finalize per the backlog guide.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Shipped

Branch `perf-037-01-engine-split` (5e1c909 controls, 28943d9 sweep, 9806b94 found-counters, 29b6e05 docs), based on main at 767a365.

**Controls.** `perf physics --disable` sets Rigidbody.isKinematic on every Rigidbody under the live enemies; `perf animation --disable` sets Behaviour.enabled=false on their AnimatedMesh/Animator components. Both track the value they found and restore exactly that, rescan on population change or 0.5 s, run as their own ungated PerfTicks so a toggle-all cannot strand an armed A/B, and are restored by `perf reset` (live log: `froze 116 rigidbodies` then `restored 240`). Shared arm sense and rescan policy in `EnemyControlPlan`, with `EnemyRenderCullPlan` delegating to it. No new Harmony patches.

**Sweep.** `--physics-arms N` and `--anim-arms N` beside `--render-arms`, mutually exclusive, one `control_plan` behind all three. Every window records `_control`, `_controlArm`, `_controlState`, `_controlMsPerFrame` and `_probesMsPerFrame`, and is flagged `_suspect` for an armed control that changed nothing at a population, changed something at zero, a baseline arm still holding state, or a second control armed per `status`.

**Legs** (fedora, tier 4, seed 20261102 - confirmed by `LevelLoader: starting map=Forest stage=0 tier=4 seed=20261102`; 0 and 240 enemies, 20 s windows, 3 repeats per arm; 24/24 windows pausedFrames == 0, vsync off, no `_suspect`, player inside the 8-unit gate):

- solver: 240 base 8.66-9.18 (mean 8.98) against kinematic 7.78-7.97 (mean 7.87), pairs -0.88 / -1.32 / -1.12 ms - the only engine figure that clears the ~0.8 ms session offset. 0.90-1.34 ms with the arm's own 0.025 ms/frame rescan added back; 5.5-8.4 us per body actually frozen.
- animation: 240 base 8.66-9.44 (mean 8.94) against off 8.73-9.55 (mean 9.18), pairs +0.59 / +0.02 / +0.11 ms - inconclusive, and bounded instead by the probe at ~0.06 ms/frame (AnimatedMesh.Update 0.060 to 0.0000, behavioursOff 240 of componentsFound 240, byType {AnimatedMesh: 240}), because the arm's rescan costs 0.036-0.051 ms/frame.
- both arms read noise at 0 enemies, as they should.
- confounds in the doc, not hidden: the kinematic swarm also loses contacts, broadphase and rb.velocity-driven movement (position-sum drift +980 to +217), and the arm claims only bodies the game left dynamic (140/240/133 at arm time). Why some enemy bodies sit kinematic stays open, with where to look.

**Tests.** xUnit 1837 passed, including enemy_physics_freeze_plan_tests.cs, enemy_animation_cull_plan_tests.cs and the two new perf command cases. pytest 1226 passed / 29 skipped: control_plan alternation and arm flip, payload direction, suspect rules, flag mutual exclusion, run.py verbs, MCP perf verbs.

**Docs.** performance.md gains "Engine-side A/B: the solver and animation" and the open item is replaced by the measured split plus the bound on animation; development.md gains the two verbs with their counters, a control-family paragraph, the sweep flags and the engine-side A/B paragraph.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
