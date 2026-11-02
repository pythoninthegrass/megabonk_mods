---
id: TASK-034
title: Attribute the unprobed per-enemy frame cost with a frame-level capture
status: To Do
assignee: []
created_date: '2026-11-02T07:48:00Z'
labels: []
dependencies: []
modified_files:
  - docs/performance.md
  - scripts/perf_sweep.py
priority: medium
type: spike
ordinal: 143000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Frame-time attribution at 240 enemies leaves the largest share of the enemy-count growth unaccounted for. Measured on the Windows build under Proton (vsync off, player fixed at the spawn point, 20 s windows, unpaused frames only): mean 7.02 ms/frame at 240 enemies against 4.15 ms at 0, so +2.87 ms of growth. Of that, 0.63 ms is the probed stock enemy path (EnemyManager.FixedUpdate 0.279, Enemy.MyFixedUpdate 0.236, EnemyMovementRb.MyFixedUpdate 0.077 at 84 calls/frame) and 0.044 ms is mod work. About 2.2 ms per frame is engine cost no probe covers, and the residual at 0 enemies is already 4.11 ms, so it is not all per-enemy.

Density, not count, drives part of it: the same 240 enemies measured 9.63 ms gathered on the player at one point and 7.02 ms strung out across the map, which points at physics contacts. Next step is a frame-level capture (Unity frame debugger, or RenderDoc on the Direct3D 11 build) of a 240-enemy run to split render from physics from GC, not another Harmony probe. Reuse scripts/perf_sweep.py for the population and the gating; see docs/performance.md for the tables and docs/development.md for the method.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
