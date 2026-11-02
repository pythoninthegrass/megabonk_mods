---
id: TASK-035
title: Resolve the three profiler probes that never record a call
status: To Do
assignee: []
created_date: '2026-11-02T07:48:00Z'
labels: []
dependencies: []
modified_files:
  - src/MegabonkLevels.Mod/perf_probes.cs
  - scripts/perf_sweep.py
priority: low
type: bug
ordinal: 144000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enemy.MyUpdate, EnemyHpBar.Update and VisualizeTargeting.Update recorded zero calls in every measurement window, across populations of 0 to 240 enemies, while the probes on Enemy.MyFixedUpdate, EnemyMovementRb.MyFixedUpdate and AnimatedMesh.Update recorded millions. Either the game does not call those methods on the path a live run takes, or the attribute-based Harmony patch never attaches to them (Il2Cpp interning or inlining, or the method being reached through a different entry point).

Until this is settled, do not treat those three costs as zero in any attribution. Reproduce with scripts/perf_sweep.py --count 240 and read the probes array in the window JSON; the patch installation path is in src/MegabonkLevels.Mod/perf_probes.cs.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
