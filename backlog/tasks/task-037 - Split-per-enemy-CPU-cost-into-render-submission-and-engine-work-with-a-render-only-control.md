---
id: TASK-037
title: >-
  Split per-enemy CPU cost into render submission and engine work with a
  render-only control
status: To Do
assignee: []
created_date: '2026-11-03 06:41'
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
type: spike
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
- [ ] #1 A harness toggle disables enemy renderers only: the game still reports 240 enemies, their positions still advance, and the submitted-vertex count for enemy shapes drops to the zero-enemy baseline
- [ ] #2 Gated-window A/B captured for on and off at 0 and 240 enemies, arms interleaved or in separate sessions, every window with pausedFrames == 0 and the player teleported to the fixed point
- [ ] #3 Each arm repeated at least 3 times and reported as a range with the session offset stated, so a delta that does not clear ~0.8 ms is labelled inconclusive rather than quoted
- [ ] #4 docs/performance.md's unprobed row and its open item replaced by the measured submission-versus-engine split, or by the bounded result plus the reason it is bounded
- [ ] #5 No new Harmony probes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
