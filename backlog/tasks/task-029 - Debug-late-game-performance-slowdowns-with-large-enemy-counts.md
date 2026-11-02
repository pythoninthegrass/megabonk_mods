---
id: TASK-029
title: Debug late-game performance slowdowns with large enemy counts
status: Done
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-02T08:06:00Z'
labels: []
dependencies: []
references:
  - docs/performance.md
  - scripts/perf_sweep.py
  - src/MegabonkLevels.Mod/perf_monitor.cs
priority: medium
type: spike
ordinal: 136000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Late in a run, once stage scaling has spawned a large number of enemies, the game slows down noticeably. Where the frame time goes at high enemy counts is unknown. Stock systems that scale with enemy count include per-enemy Rigidbody movement, minimap icon updates, animations and effects; the mod adds its own per-frame work on the same population (the kill-floor watcher scanning EnemyManager.enemies, the dev readout's enemy scans, Harmony prefixes on hot paths). Diagnose and attribute the cost so any fix targets the real bottleneck instead of a guess — the same pattern as TASK-027's diagnosis-first split.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A repeatable profiling method for a late-game run with a large enemy count exists (harness-driven, spawns on, invulnerable player, forced stage/tier) and is documented in docs/development.md
- [x] #2 Frame-time attribution identifies the top cost centers with measurements, separating stock game systems from mod-added per-frame work
- [x] #3 Every mod-side cost that scales with enemy count is measured; small ones are fixed in this task and larger ones are filed as follow-up tasks with the measurement attached
- [x] #4 Findings are written up in docs: what scales with enemy count and what does not, so future performance work starts from evidence
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation plan (approved with Lance 2026-11-02)

Test box: fedora (Windows build under Proton Experimental, -force-d3d11; game dir ~/.local/share/Steam/steamapps/common/Megabonk; harness enabled; .venv present).

Phase 0 - Prep:
1. Reconcile fedora's uncommitted WIP (dev_harness.cs, run.py, mcp_server.py, build_thps_level.py, levels/thps.mblevel.json) with mbp's newest tree before building on top; sync via the CLAUDE.local.md rsync ritual.
2. Build on mbp (task mod:build), deploy DLL to fedora game dir Mods/.

Phase 1 - Instrumentation (gated on DevHarness.Enabled, zero player cost):
- PerfSampler: ring-buffered Time.unscaledDeltaTime -> p50/p90/p99/max frame ms + live enemy count via a new harness "perf" command; perf fields in state.
- us/frame timers around each per-frame tick in megabonk_levels_mod.OnUpdate (KillFloorWatcher, PositionLabel, LevelMusic, DevHarness.Poll, StartupCover, LiveEditPatch, GrindAssistWatcher, EditorMode) and MusicController.Update postfix.
- Runtime A/B toggles (perf <tick> off|on).
- New gated verbs (Lance approved): perf spawn N and perf timescale X for a repeatable enemy count.

Phase 2 - Repeatable method on fedora (AC#1, documented in docs/development.md):
- Forced --stage/--tier/--seed load, spawns on, invulnerable on; 30-60s measurement windows with no screenshots or other harness commands inside a window (ReadPixels stall pitfall); one mod-uninstalled run as true stock baseline; enemy-count sweep; MangoHud frametime logging as best-effort cross-check under gamescope. Avoid editor mode (stuck-editor-on-Proton caveat).

Phase 3 - Attribution (AC#2):
- Mod costs measured directly by timers; stock = total minus mod + per-enemy slope across the count sweep (Rigidbody movement, minimap icons, animations/effects). Record limitation: no Unity Profiler in release Il2Cpp; numbers are fedora/Intel-Arc-specific.

Phase 4 - Small fixes in-task (AC#3), follow-ups for larger:
- Candidates from code: KillFloorWatcher per-check Dictionary + LINQ allocs, per-enemy collider.bounds reads, heartbeat duplicate scan, DevHarness.Poll 0.5s directory scan. Measure before/after on fedora. Python tests first for new run.py/mcp_server verbs (DoD #2).

Phase 5 - Docs (AC#4) + closeout:
- Findings in docs/performance.md (content-first, no task refs); method in docs/development.md; temporary instrumentation kept gated or restored per TASK-027 cleanup discipline. Then finalization guide: ACs with evidence, task check, conventional commit, no attribution.

Risks: stock attribution inferential; forced counts may drift (spawn verb mitigates); fedora WIP must be reconciled first; repeated quit/relaunch on the live fedora session approved by Lance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Method and evidence. All measurement on fedora (Windows build under Proton Experimental, -force-d3d11), every window gated on a verified live run: state's levelLoaded/killFloorArmed true, editor/frozen false, perf status paused false, then vSyncCount 0 and pausedFrames 0 on the kept report. Protocol per window: teleport the player to a fixed point, perf health, spawn the top-up, perf start, 20 s while dismissing reward windows at 1 Hz, perf report. Driver is scripts/perf_sweep.py; the gates are unit tested in tests/test_perf_sweep.py (14 new tests). Results JSON per window in /tmp/t029_before2 (pre-fix build) and /tmp/t029 (fixed build) on fedora, copies in t029_results_before2/ and t029_results_after/ in the session temp dir.

Frame time vs enemy count, fixed build, one protocol throughout: 0 enemies 4.15 ms mean (260 fps), 40 4.45, 80 4.77, 120 5.07, 160 4.99, 200 7.37, 240 7.02 ms (154 fps). Mod-attributed 0.042 to 0.086 ms/frame, 1.0% to 1.2% of the frame. Probed stock enemy work at 240: EnemyManager.FixedUpdate 0.279, Enemy.MyFixedUpdate 0.236 (84 calls/frame, 2.81 us each), EnemyMovementRb.MyFixedUpdate 0.077, AnimatedMesh.Update 0.039 (239 calls/frame). Residual 6.30 ms/frame at 240, 4.11 ms at 0.

Mod-side costs that scaled with the population, all fixed with before/after measured on the same protocol: the kill-floor watcher's collider.bounds read on every actor every check (Unity builds bounds lazily, so on a fresh actor it rebuilds them) produced a 112.55 ms single call at 120 enemies and 58.41 ms at 160; KillFloor tick 0.022 to 0.013 ms/frame and 22.1 to 13.1 us/call at 240. KillTracker's LINQ/GroupBy allocations per check (now keyed dictionary in, reused scratch collections). The position overlay's actor sweep 0.25 s to 0.75 s cadence: 0.022 to 0.012 ms/frame at 240. 1687 C# tests and 993 Python tests pass; task check green.

Two findings about the measurement itself, each of which produced a wrong number first: paused frames are UI frames (one 160-enemy window held 784 and was discarded, so any window with pausedFrames > 0 is retaken), and perf health alone does not keep a run alive because PlayerHealth.KillPlayer bypasses both Mirror and hp, so the driver must teleport per window. Same-count spread across repeat windows at 240 was 6.5/7.0/7.8/9.6 ms, so total-frame-time deltas under ~1.5 ms are not evidence; per-tick totals and maxMs are.

Cleanup: fedora's Mods/MegabonkLevels.Mod.dll restored byte-for-byte from MegabonkLevels.Mod.dll.task029.bak (90b51146...) and the instrumented game stopped. The Mac's installed DLL is rebuilt from the committed source, which carries the profiler gated on the harness. Follow-ups filed for the ~2.2 ms unprobed engine cost and the three probes that never fired.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Frame time roughly doubles from an empty level to 240 enemies (4.15 to 7.02 ms mean, 260 to 154 fps on the Windows build under Proton), and essentially all of that growth is the game's own enemy update and physics: 0.63 ms/frame of probed stock enemy work, ~2.2 ms of unprobed engine cost, and 0.044 ms of mod work - the mod is 1.2% of a 240-enemy frame. The one cost the mod owned was a hitch: the kill-floor watcher read collider bounds on every actor every check, and Unity builds them lazily, which produced a 112.55 ms single call at 120 enemies. Probing distance, reused dictionaries, a collection-in KillTracker and a slower actor-overlay sweep took that to 0.53 ms and the tick from 0.022 to 0.013 ms/frame, with before and after measured on one protocol.

Shipped as tooling rather than a fix to gameplay: a harness-gated frame profiler (frame buffer that counts paused frames apart from sampled ones, per-tick timers, eleven probes over the enemy path) behind the perf verbs, and scripts/perf_sweep.py, which drives a fresh launch through gated measurement windows. Findings, limits and follow-ups are in docs/performance.md and the method in docs/development.md.

Two results were about the measurement, not the game: paused frames are UI frames, so a window holding any is retaken (one discarded window held 784); and the same 240 enemies measured 9.63 ms gathered on the player against 7.02 ms strung out across the map, so windows fix the player's position - which is also what keeps the run alive, because PlayerHealth.KillPlayer bypasses both Mirror and the hit-point floor. Window-to-window spread at 240 was 6.5 to 9.6 ms, so totals under ~1.5 ms between runs are not evidence; per-tick totals and worst calls are.

task check green (1687 C# tests, 993 Python tests, lint clean). Instrumented DLL removed from fedora and its original restored byte-for-byte from backup, the instrumented game stopped, the Mac's DLL rebuilt from committed source. Left open and filed with measurements: TASK-034 for the unprobed per-enemy engine cost, TASK-035 for three probes that never recorded a call.
<!-- SECTION:FINAL_SUMMARY:END -->
