---
id: TASK-037.01
title: >-
  Split the per-enemy engine cost into AI, physics and animation with harness
  controls
status: Done
assignee: []
created_date: '2026-11-04 06:31'
updated_date: '2026-11-04 18:13'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `perf physics` (Rigidbody.isKinematic) and `perf animation` (AnimatedMesh behaviour disable) controls beside `perf render`, each with a pure plan class and unit tests, its own ungated tick, status/report fields and restore on `perf reset`, swept by `--physics-arms` and `--anim-arms`. Measured at tier 4, seed 20261102, 0 and 240 enemies, 3 interleaved repeats per arm: taking the swarm out of the solver is worth 0.88-1.32 ms/frame at 240 enemies (0.90-1.34 with the arm's own rescan added back), the only engine figure that clears the ~0.8 ms session offset; animation is bounded at ~0.06 ms/frame by its own probe (the A/B is inconclusive because the rescan costs the same); render submission stays <=0.7 ms. Fidelity confounds are recorded in docs/performance.md (kinematic bodies also lose contacts, broadphase and velocity-driven movement; position-sum drift mean +980 vs +217). No new Harmony patches. task check passes.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
