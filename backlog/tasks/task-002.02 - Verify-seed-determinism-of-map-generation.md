---
id: TASK-002.02
title: Verify seed determinism of map generation
status: To Do
assignee: []
created_date: '2026-10-06 21:40'
labels:
  - level-editor
dependencies:
  - TASK-002.01
parent_task_id: TASK-002
priority: high
type: spike
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-002 first for full context. Depends on TASK-002.01's hello-mod/hook being in place.

This is the single most important finding in the entire project: the "seed + edits" level model (the decided approach — see parent context) only works if `MapGenerationController`'s generation is fully deterministic given the same map, stage, and seed. If it isn't, levels can't be represented as "seed + edit list" and must instead store a full layout snapshot (every spawned object's type + transform), which is a materially different (larger, less flexible) design that would need to be re-planned.

Extend the mod from TASK-002.01: on `A_GenerationComplete`, walk every spawned tile and object under the generated map root, and compute a stable hash (e.g. sort by a deterministic key like grid coordinates, then hash type + local position + rotation + scale for each). Force the same `mapSeed` (via `MapGenerationController.mapSeed` or `ProceduralTileGeneration`'s `debugSeed`, whichever actually controls generation — confirm by testing both) across two full generations of the same map + stage (e.g. via `MapController.TestMap` called twice, or restarting the run), and compare the hashes.

Test at least 2 different (map, stage) combinations to catch a case where determinism holds for one map type (e.g. `EMap.Forest`, tile-based) but not another (e.g. the Perlin-noise `EMapType.ProceduralMesh` path, which may use a different RNG consumption order).

If any case is non-deterministic, identify why if feasible (e.g. physics-order-dependent spawning, a RNG call seeded from wall-clock time somewhere, coroutine/frame-timing-dependent ordering) and record it. Then write up the fallback decision: either "full-layout snapshot" becomes the save format instead of "seed + edits" project-wide, or determinism can be forced for the paths that matter (document which).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Two full generations of the same map+stage+seed are compared via a deterministic hash of every spawned tile/object's type+transform, for at least 2 different (map, stage) combinations
- [ ] #2 The result (deterministic or not, and for which map types) is documented with the exact hashing method used so the test is reproducible
- [ ] #3 If non-deterministic in any case, the likely cause is investigated and recorded, and a concrete fallback decision (snapshot format vs forcing determinism) is written into docs/ for TASK-003 to consume
- [ ] #4 The field(s) that actually control generation (mapSeed vs debugSeed, or both) are confirmed by direct testing, not assumed from dump.cs field names alone
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
