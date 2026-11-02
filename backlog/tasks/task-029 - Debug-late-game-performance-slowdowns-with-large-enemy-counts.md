---
id: TASK-029
title: Debug late-game performance slowdowns with large enemy counts
status: In Progress
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-02T06:11:00Z'
labels: []
dependencies: []
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
- [ ] #1 A repeatable profiling method for a late-game run with a large enemy count exists (harness-driven, spawns on, invulnerable player, forced stage/tier) and is documented in docs/development.md
- [ ] #2 Frame-time attribution identifies the top cost centers with measurements, separating stock game systems from mod-added per-frame work
- [ ] #3 Every mod-side cost that scales with enemy count is measured; small ones are fixed in this task and larger ones are filed as follow-up tasks with the measurement attached
- [ ] #4 Findings are written up in docs: what scales with enemy count and what does not, so future performance work starts from evidence
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
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
