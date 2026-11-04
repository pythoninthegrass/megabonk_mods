---
id: TASK-037
title: >-
  Split per-enemy CPU cost into render submission and engine work with a
  render-only control
status: Done
assignee: []
created_date: '2026-11-03 06:41'
updated_date: '2026-11-04 06:24'
labels: []
dependencies:
  - TASK-036
documentation:
  - docs/performance.md
  - docs/development.md#headless-replay-no-qt-host
  - docs/development.md#frame-time-profiling
modified_files:
  - docs/performance.md
  - src/
  - scripts/
priority: medium
ordinal: 147000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-036 settled the first half: the ~1.6 ms/frame of unprobed per-enemy cost at 240 enemies is CPU-side, not GPU render. Enemy draw shapes take 38-54% of the frame's summed per-event GPU time (4.4% churn floor between two captures of the same condition), but going 0 to 240 enemies roughly doubles that GPU time and triples submitted vertices while the harness's wall-clock frame rises only 1.6x (4.877 ms to 7.482 ms mean), so the GPU has headroom and is not the constraint. Per enemy that is +0.88 to +1.18 draw calls and +3,405 to +7,022 submitted vertices - about one Vulkan draw plus its state setup on the render thread.

The half that is still open is the split inside the CPU side: render-thread draw submission versus the engine's per-enemy main/physics work (Rigidbody solve, animator, AI beyond the probed Enemy.MyFixedUpdate / EnemyMovementRb.MyFixedUpdate / AnimatedMesh.Update). RenderDoc cannot answer it. Per-event EventGPUDuration from headless replay is inflated at least 4.7x (a frame the harness measured at 4.88 ms mean sums to 22.8 ms) and anti-correlates with submitted work (101 ms on 0.7 M vertices against 44.5 ms on 2.5 M); Intel ANV exposes no whole-frame GPUCounter.Duration and the pymodule has no REVENT, so there is no cross-check. See the "Headless replay, no Qt host" section of docs/development.md before reaching for a capture again.

Deliverable: a harness control that turns off only the enemies' renderers - Renderer.enabled = false on the live enemy objects, or an equivalent cull that suppresses their draws - while AI, physics and animation keep running, then a gated-window A/B of it against count_240 measured on the harness's own frame clock. The control belongs beside the existing perf toggles in the dev harness (see scripts/perf_sweep.py and the perf verbs in docs/development.md#frame-time-profiling); do not add Harmony probes.

Measurement rules that apply, all of them learned the hard way:
- Windows drift upward through a session (one population measured 7.482, 7.784 then 9.501 ms in sweep order) and two sessions of the same condition differ by ~0.8 ms, which is half the residual being attributed. Interleave the arms or take them in separate sessions, and state the spread; a delta below the session offset is not a result.
- Discard any window with pausedFrames > 0 and teleport the player to the fixed point before each window; the kill floor ends runs mid-window otherwise.
- Report the toggle's own effect on enemy count: if disabling renderers changes despawn or culling behaviour, the A/B is no longer like-for-like and the numbers must say so.

Write the result into docs/performance.md: the "per-enemy CPU-side update, submission and engine overhead (unprobed)" row and the open item that currently names this experiment as the missing control.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness toggle disables enemy renderers only: the game still reports 240 enemies, their positions still advance, and the submitted-vertex count for enemy shapes drops to the zero-enemy baseline
- [x] #2 Gated-window A/B captured for on and off at 0 and 240 enemies, arms interleaved or in separate sessions, every window with pausedFrames == 0 and the player teleported to the fixed point
- [x] #3 Each arm repeated at least 3 times and reported as a range with the session offset stated, so a delta that does not clear ~0.8 ms is labelled inconclusive rather than quoted
- [x] #4 docs/performance.md's unprobed row and its open item replaced by the measured submission-versus-engine split, or by the bounded result plus the reason it is bounded
- [x] #5 No new Harmony probes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach (approved with Lance 2026-11-03)

Worktree `~/git/megabonk_mods-037` on branch `perf-037-render-only` off origin/main (036 merged); gitignored .env/.tools/.venv/CLAUDE.local.md symlinked from the main checkout. Fedora gets a matching worktree (same branch, .env+.venv symlinked); DLL built on the authoring box and scp'd into the game's Mods.

1. C# control, no Harmony probes: new `enemy_render_cull.cs` - `Renderer.enabled=false` on all child renderers of live enemies (`EnemyManager.Instance.enemies.Values`, `GetComponentsInChildren<Renderer>(true)`); Enemy/EnemyMovementRb/AnimatedMesh/Rigidbody stay enabled. Tracked instance-id set restores only renderers we disabled; rescan only on enemy-count change or interval so the control itself costs ~nothing per frame. `perf render --enable|--disable` via RunPerf; `status`/`report` gain `renderCull{armed,renderersOff}` and `enemyPositionSum` (sum of live rb.position) for the positions-advance check; Reset() restores.
2. Python: run.py PERF_ACTIONS + render, mcp_server perf verb, perf_sweep `--render-arms N` - interleaved `count_<c>_rendon_r<k>`/`count_<c>_rendoff_r<k>` windows, toggle set before perf start, `_renderArm`/`_renderersOff`/position-sum delta in the window JSON, suspect when renderersOff==0 at target>0, render restored in finally. Sweep also drives KEY_ENTER through the menu service after launch (fedora Photosensitivity Warning).
3. Tests first: tests/test_perf_sweep.py (render_plan ordering/naming/interleaving, arg validation, suspect rule); tests/MegabonkLevels.Tests/enemy_render_cull_tests.cs (rescan policy, tracked-set disable/restore/prune) + perf_command_tests case; mirrors the perf_probe_plan pure-class pattern.
4. Fedora legs: AC#1 via RenderDoc-armed capture run (--captures 2, ENABLE_VULKAN_RENDERDOC_CAPTURE=1 through launch-megabonk.sh env) at 240 rendoff/240 rendon/0, then renderdoc_replay --structured (python3.14) - enemy shapes to 0-enemy vertex baseline, enemies stay 240, position sum advances. Timing A/B capture-free, two sessions, `--count 0 --count 240 --render-arms 3 --seconds 20 --seed 20261102`; gates: pausedFrames==0, teleport to fixed point, spawns off, vsync off, reward dismissal.
5. Split: submission ~= mean(240,rendon) - mean(240,rendoff); engine ~= mean(240,rendoff) - mean(0). Ranges over >=3 repeats per arm, session offset stated; deltas under the offset labelled inconclusive. Renderer.enabled=false also removes those renderers' culling and shadow-pass work - the doc must say the submission figure includes that. If the toggle moves enemy counts between arms, report it as the like-for-like caveat.
6. Close: rewrite docs/performance.md unprobed row + open item; docs/development.md render verb + --render-arms; task check, pytest, dotnet test; conventional commits no attribution; finalize per backlog guide.

Executed approach, where it differed from the plan as approved:

- The cull's per-frame work is instrumented as its own PerfTick (RenderCull) and that tick is exempt from `toggle all off` (IsUngated, with DevHarnessPoll), so a mod-off control arm cannot strand an armed A/B.

- Wire field `enabled` means enemy rendering wanted everywhere; EnemyRenderCullPlan.ArmsCull(renderEnabled) => !renderEnabled is the single place converting it to cull arming, mirrored by perf_sweep.render_arm_payload. An earlier build had the two disagree and silently swap arms, which is why the mirror is now a tested pure function on both sides.

- Arms strictly alternate and the leading arm flips every repeat: a fixed order makes the always-second arm absorb the within-session upward drift, which biases the submission estimate toward zero - the quantity under test.

- Each window records _playerAtOrigin and _origin, suspect beyond 8 units (240 enemies shove the player 2-4.4 units during the settle after the teleport).

- Legs must be run with --tier 4 --seed 20261102: levels/example-forest.mblevel.json carries tier 0 and --tier defaults to the level's own value, so omitting it measures a tier-0 leg that is not comparable to the published table.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Protocol fix before the reported legs: the render A/B had measured rendon before rendoff in every repeat, so the off arm always sat one window later than its partner and absorbed the documented within-session upward drift. That bias pushes the submission estimate toward zero, which is the quantity under test, so render_plan now flips the leading arm on even repeats (test added). Each window also records _playerAtOrigin against _origin and is flagged suspect beyond 2 units, making the fixed-point condition auditable from the window JSON.

Tier-4 capture evidence (structured replay, /tmp/perf037-cap/captures): the 2,013-index instanced enemy body shape submits 889,746-966,240 vertices across 8-9 draws at 240 enemies with rendering on and exactly 0 with the cull armed, as it does at 0 enemies. Whole-frame submitted vertices 0.773 M (0 enemies) / 2.03-2.05 M (on) / 0.83-0.86 M (off): 93-96% of the enemy-attributable vertex volume is removed, draw calls fall from +248/+259 above baseline to +146/+195 because the enemy meshes are instanced into a handful of draws. Residual above baseline in the off arm is shape churn present with and without enemies (2,304-index shape at 23-55 k, shared 4,812/4,020-index shapes), not enemy meshes.

Final numbers (player box, tier 4, seed 20261102, 20 s gated windows, vsync off, live run, two sessions, six 240-enemy pairs). Captures (structured replay, tier 4): enemy body shape (2,013 indices, instanced) 889,746-966,240 submitted vertices across 8-9 draws at 240 with rendering on and exactly 0 with the cull armed, as at 0 enemies; whole-frame submitted vertices 772,608-773,178 (0), 2,026,260-2,052,171 (on), 829,788-859,902 (off), so 93-96% of the enemy-attributable vertex volume is removed; draw calls +248/+259 above baseline fall to +146/+195 because the enemy meshes are instanced.

Timing: clean leg baseline 5.15-5.31 (mean 5.22), 240 render on 9.19-9.99 (9.60), 240 render off 9.32-9.79 (9.54), pair deltas -0.13/+0.49/-0.16, submission -0.61..+0.66 ms (inside the ~0.8 ms session offset, bounded not quoted), engine (off - same-leg baseline) +4.06..+4.65 ms = 17-19 us per enemy. Second leg is the noisier replication: its off arm read slower than its on arm because the swarm carried the player 35-178 units from the standing point in exactly those three windows; recorded in the doc rather than dropped.

Control cost and fidelity: cull tick 0.027-0.045 ms/frame armed, 0.0006 disarmed; mod ms/frame 0.160-0.181 on arm vs 0.199-0.203 off arm; enemiesLast 240 in both arms, enemyPositionSum advancing while culled, pool 240/550 in both, so the toggle has no effect on despawn or population. perf render --disable reports renderersOff 240/240 (exactly one renderer per enemy); perf reset returns renderCullRestored:true and status then reads armed:false renderersOff:0 with 240 alive; perf render --enable restores 240/240.

Environment notes: the harness does not serve perf verbs while the game sits in editor mode (commands time out; run them on a live run). A sweep launched with --tier omitted silently measures tier 0. The RenderDoc pymodule replay needs /usr/bin/python3.14 and refuses to open a replay device while the game is running, so replay legs are sequenced after the timing legs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Adds a harness render-only control and uses it to split the per-enemy frame cost into render submission and engine work, replacing the unprobed row in docs/performance.md and the open item that named this control as the missing measurement.

Control: src/MegabonkLevels.Mod/enemy_render_cull.cs sets Renderer.enabled=false on every renderer under the live enemies and nothing else (Enemy/EnemyMovementRb/AnimatedMesh/Rigidbody stay enabled), tracks the instance ids it disabled so only those are restored, and rescans on population change or a 0.5 s interval. Decisions live in enemy_render_cull_plan.cs (ArmsCull, ShouldRescan, ToDisable, PositionSum), the pattern the perf probes already use. Wired as the perf `render` verb through RunPerf, run.py PERF_ACTIONS and the MCP perf verb; status and report carry renderCull{armed,renderersOff} and enemyPositionSum; perf reset un-arms and restores. The cull runs as its own PerfTick, exempt from `toggle all off` so a mod-off arm cannot strand it. No new Harmony probes.

Measurement: perf_sweep --render-arms N emits interleaved count_<c>_rendon_r<k>/rendoff_r<k> windows with the leading arm flipped each repeat, arms the cull before perf start, records _renderArm/_renderersOff/_cullMsPerFrame/_positionSumBefore/After/_playerAtOrigin/_origin, and flags suspect an off arm that disabled nothing at a population, an on arm still hiding renderers, or a player off the standing point.

Result: enemy draw submission is bounded at <=0.7 ms/frame at 240 enemies (pair deltas -0.61..+0.66 in the clean leg, inside the ~0.8 ms session offset) while the captures show 93-96% of the enemy-attributable submitted vertices and every enemy body draw removed; what clears the offset is engine work on the main and physics threads, +4.06..+4.65 ms over the same leg's 0-enemy window, 17-19 us per enemy. The control's own cost is 0.027-0.045 ms/frame armed.

Tests written first: tests/test_perf_sweep.py (render_plan interleaving and leading-arm flip, render_arm_payload direction, render and player-start suspect rules, cull_ms_per_frame), tests/MegabonkLevels.Tests/enemy_render_cull_plan_tests.cs (ArmsCull, ShouldRescan, ToDisable, PositionSum), perf_command_tests.cs. task check green at 1189 passed / 29 skipped with markdownlint and ruff clean; the xUnit suite passes.

Risks and follow-ups: the split is a bound, not a measurement, because the submission delta never cleared the session offset - more repeats per arm would tighten it. The figure attributes to engine work anything Unity culls by renderer visibility (animator updates), bounded at the 0.039 ms/frame the probed AnimatedMesh.Update accounts for. The natural next control is inside the engine side: kinematic Rigidbody, or animator disabled with renderers back on, on the same gated-window pattern.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
