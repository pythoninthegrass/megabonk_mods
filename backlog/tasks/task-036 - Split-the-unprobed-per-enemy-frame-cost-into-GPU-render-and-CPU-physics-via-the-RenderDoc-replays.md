---
id: TASK-036
title: >-
  Split the unprobed per-enemy frame cost into GPU render and CPU physics via
  the RenderDoc replays
status: Done
assignee: []
created_date: '2026-11-02T21:32:00Z'
updated_date: '2026-11-03 06:37'
labels: []
dependencies: []
documentation:
  - docs/performance.md
  - docs/development.md
modified_files:
  - docs/performance.md
  - docs/development.md
priority: medium
type: spike
ordinal: 145000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Frame-time attribution at 240 enemies (levels/example-forest.mblevel.json, tier 4, seed 20261102, vsync off, scripts/perf_sweep.py gated windows) accounts for only part of the growth over an empty level: mean 7.02 ms/frame at 240 vs 4.15 ms at 0. Probed stock enemy paths are ~0.63 ms/frame (Enemy.MyFixedUpdate, EnemyMovementRb.MyFixedUpdate, AnimatedMesh.Update et al.), the mod is ~0.04-0.1 ms, density-contact overhead ~0.18 ms - leaving roughly 1.6 ms/frame of unprobed per-enemy engine work (Unity rendering, physics broadphase and solver, animation beyond AnimatedMesh). Harmony probes are exhausted on this; docs/performance.md's open items say the next step is separating GPU render time from CPU-side physics through a RenderDoc capture replay.

The captures exist on fedora (ssh fedora, tailscale only): /tmp/perf-captures-g/captures/count_240_0.rdc and count_240_1.rdc (plus count_0 controls) and /tmp/perf-captures-s/captures/*.rdc (density A/B and mod-off/reenabled controls), taken through the DXVK layer under Proton Experimental per the "RenderDoc on a direct-Proton Linux host" section of docs/development.md. /tmp is volatile - if they are gone, regenerate from ~/git/megabonk_mods with: ENABLE_VULKAN_RENDERDOC_CAPTURE=1 launch plus uv run scripts/perf_sweep.py --count 240 --captures 2 --capture-dir /tmp/RenderDoc --launch-cmd "sh /home/lance/.local/share/scripts/launch-megabonk.sh" (absolute launch-cmd path is required; the game launches offline via the steamstub, no Steam session needed).

Deliverable: replay the 240-enemy captures in the RenderDoc Qt UI (renderdoccmd or the GUI on fedora's GNOME session, or copy the .rdc files to a machine with the RenderDoc app), read GPU frame duration, draw-call count and the per-enemy mesh/animation submission, and settle how much of the ~1.6 ms is GPU render versus CPU-side physics/animation. Write the verdict and the numbers into docs/performance.md - replace the "~1.6 ms/frame of per-enemy engine update overhead" open item with the settled split, and record the replay method in docs/development.md if it needed anything beyond the existing capture section. Do not add new Harmony probes.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

Unblock found before planning: the round-1 conclusion "headless replay is impossible because the pymodule needs the Qt host" is wrong. The pymodule is already built on fedora at `~/git/renderdoc-build/renderdoc/build3/lib/renderdoc.so` (v1.47, matches the capture-time layer) and it imports cleanly - but only under **python3.14** (its ABI target; system python3 is 3.13, which is what segfaulted), and it needs `renderdoc.InitialiseReplay()` / `ShutdownReplay()` around every call, which the Qt host normally does for you. See docs/python_api/python_module.rst in the vendored source.

### Steps
1. Worktree `~/git/megabonk_mods-036` on branch `perf-036-renderdoc-replay` (authoring box), gitignored files symlinked from the main checkout; fedora worktree for the same branch, same symlinks. Main checkout left untouched for the concurrent installer agent.
2. Replay harness: a python3.14 script on fedora that, per .rdc: InitialiseReplay -> OpenCaptureFile -> OpenCapture(ReplayOptions vsync off) -> GetFrameStatistics, GetRootActions tree with per-action gpuDuration, draw/instanced-draw counts, unique pipeline/shader/resource signatures (per-enemy submission), SupportsGPUCounters + available counters.
3. A/B on the existing controls: count_0 vs count_240 (both capture sets) gives per-enemy GPU render cost directly; modoff/reenabled pairs cross-check the mod's contribution. Compare against the frame-measured 4.15 vs 7.02 ms means.
4. Settle the split: GPU render ms vs CPU-side remainder of the ~1.6 ms; rewrite the "per-enemy update + engine overhead (unprobed)" row and the open item in docs/performance.md; correct the now-false "headless replay not achieved" paragraph in docs/development.md's RenderDoc section with the working method.

### Constraints / risks
- The game is currently running on fedora under Proton for the higher-priority installer task. Replay is a GPU workload and would both skew its own numbers and contend for the GPU. **Gate every replay run on a game-not-running check; if the game is up, stop and report rather than interfere.**
- Intel ANV + Vulkan GPU counters may be unsupported -> fallback is replay wall-clock throughput (presents/second with vsync off) as the GPU-bound proxy, plus the count_0 delta.
- No new Harmony probes (task constraint). No sudo on fedora: no package installs, everything stays in `~/.local` / `~/.venvs`.
- Deliverable so far names docs only; if the replay script should be committed as a tracked tool that is a scope change and needs approval.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Unblock (round 2)

The round-1 blocker was wrong on two counts, both now verified on fedora:
- `~/git/renderdoc-build/renderdoc/build3/lib/renderdoc.so` (pymodule, v1.47, built against **python3.14**) imports cleanly under `/usr/bin/python3.14`; the round-1 segfault was importing it under 3.13 (ABI mismatch) and never calling `InitialiseReplay()`/`ShutdownReplay()` - and RenderDoc also dumps core in interpreter teardown if `ShutdownReplay()` is skipped, which looks like an import crash.
- The pure `renderdoc` module (no `qrenderdoc`) is enough for headless replay; the Qt host is not needed. `docs/python_api/python_module.rst` in the vendored source says so explicitly.

Tracked tool: `scripts/renderdoc_replay.py` (+ `tests/test_renderdoc_replay.py`, 15 tests, test-first). Default mode opens a replay device; `--structured` parses the serialised API log with no GPU. It refuses to replay while the game is running.

## Structured A/B (GPU-free, /tmp/perf-captures-g, 240 vs 0, gathered)

| capture | draw calls | instanced | instances | vertices submitted |
| --- | ---: | ---: | ---: | ---: |
| count_0_0 | 661 | 144 | 1635 | 833,835 |
| count_0_1 | 659 | 146 | 1635 | 833,943 |
| count_240_0 | 944 | 179 | 2774 | 2,519,136 |
| count_240_1 | 873 | 159 | 2280 | 1,651,035 |
| count_240_modoff_0/_1 | 1025 / 957 | | 2301 / 2285 | 1.59M / 1.67M |
| count_240_reenabled#2_0/_1 | 409 / 650 | | 812 / 1264 | 0.70M / 0.86M |

Pair means: 0 enemies 660 draws / 0.834M vertices; 240 enemies 908 draws / 2.085M vertices -> **+1.03 draw calls and ~5.2k vertices submitted per extra enemy**, i.e. roughly one indexed draw per enemy (the heaviest shapes in the 240 captures are 2304- and 4020-index meshes bound 26x/18x, vs 12x at zero).

Capture-to-capture spread is wide (count_240_0 vs _1 differ by 71 draws and 0.9M vertices; the reenabled#2 pair is far below the baseline, so those two caught a different camera/culling state). Any per-enemy figure has to be quoted as a range from both captures, not one.

## Sequencing constraint

The Go-installer agent (TASK-006.04.01.01) is working the same box (repo synced 23:43, `run.py menu serve` live). Per Lance: zero-GPU work now, GPU replay only in a free window. The tool enforces the game-not-running check; the replay run is gated on that.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Replayed all 14 sweep captures headlessly and settled the split: the ~1.6 ms/frame unprobed per-enemy cost is CPU-side, not GPU render.

Verdict and evidence
- Enemy draw shapes account for 38-54% of the frame's summed per-event GPU time (35-47% with the mod off) against a 4.4% churn floor measured between two captures of the same condition, so enemy meshes really are about half the GPU's work.
- The GPU is not the constraint: within one session, 0 to 240 enemies roughly doubles the summed per-event GPU time (22.8 ms to 44.5 ms) and triples submitted vertices (0.85 M to 2.54 M) while the harness's wall-clock frame rises only 1.6x (4.877 ms to 7.482 ms mean). A GPU on the critical path cannot absorb twice its work in a 60% frame increase.
- What does scale per enemy is CPU-side submission: +0.88 to +1.18 draw calls and +3,405 to +7,022 submitted vertices per enemy, i.e. roughly one Vulkan draw plus its state setup per enemy on the render thread, on top of the engine's per-enemy main/physics work.
- Absolute milliseconds cannot come from replay: the 0-enemy frame sums to 22.8 ms of EventGPUDuration while the same condition measured 4.88 ms mean / 4.16 ms p50, and totals anti-correlate with work (101 ms on 0.7 M vertices against 44.5 ms on 2.5 M). The Intel ANV driver exposes no whole-frame Duration counter and the pymodule has no REVENT, so there is no cross-check. Ratios within a session are all the clock supports.

Shipped
- scripts/renderdoc_replay.py (tracked, approved scope expansion): replay mode, --structured (GPU-free, parses the serialised API log), --baseline/--enemies per-enemy split, --pipelines, --json; refuses to open a replay device while Megabonk.exe is running, --force to override; reports device, render targets, per-draw and per-shape GPU durations.
- tests/test_renderdoc_replay.py: 20 tests over game_pids, draw_histogram, top_shapes, gpu_totals, draw_records, shape_totals, per_enemy_cost, render_targets, renderdoc_lib. Full suite 1027 passed, 56 skipped.
- docs/performance.md: the false "headless replay was not achieved / pymodule needs the Qt host" paragraph replaced with the measurement; the attribution row and the open item now state the CPU-side verdict and name the missing control.
- docs/development.md: the replay section corrected (python3.14 ABI pin, InitialiseReplay/ShutdownReplay bracket, renderdoc-only module) plus two new limits - the inflated per-event clock and the structured-vs-replay instance divergence.
- Commits a797b73, b9dd730, 11c6fdb, fbcc9c3 on perf-036-renderdoc-replay (pushed). No new Harmony probes; no pre-024 backup DLLs touched.

Where the plan deviated
- Step 3 assumed count_0 vs count_240 yields per-enemy GPU render cost directly. It does not: the counter is inflated at least 4.7x, so the A/B bounds GPU involvement instead of measuring it. The verdict rests on the ratio argument plus the harness's own frame clock instead.
- Sidecar JSONs from the capture sweep produced three measurement findings not in the plan, now documented: cost walks upward through a session (7.482, 7.784, 9.501 ms for one population), two sessions of the same condition differ by ~0.8 ms, and switching the mod off made frames ~0.3 ms slower while its self-measured cost fell 0.056 ms.

No acceptance criteria were defined for this task, so verification was against the deliverable text in the description: docs/performance.md carries the verdict and numbers, docs/development.md the method.

Proposed next steps (not created)
- A harness control that disables only the enemies' renderers with AI, physics and animation running, measured as a gated window against count_240: the render-only A/B that splits submission from engine work on a trustworthy clock.
- Interleave or randomise window order in the capture sweep, since order drift and the ~0.8 ms session offset are the same order as the residual being attributed.
<!-- SECTION:FINAL_SUMMARY:END -->
