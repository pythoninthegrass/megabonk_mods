---
id: TASK-002.02
title: Verify seed determinism of map generation
status: Done
assignee: []
created_date: '2026-10-06 21:40'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-002.01
parent_task_id: TASK-002
priority: high
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
- [x] #1 Two full generations of the same map+stage+seed are compared via a deterministic hash of every spawned tile/object's type+transform, for at least 2 different (map, stage) combinations
- [x] #2 The result (deterministic or not, and for which map types) is documented with the exact hashing method used so the test is reproducible
- [x] #3 If non-deterministic in any case, the likely cause is investigated and recorded, and a concrete fallback decision (snapshot format vs forcing determinism) is written into docs/ for TASK-003 to consume
- [x] #4 The field(s) that actually control generation (mapSeed vs debugSeed, or both) are confirmed by direct testing, not assumed from dump.cs field names alone
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a pure, tested `GenerationHash.Compute` (SHA-256 over sorted, quantized transform records) in `generation_hash.cs`, test-first.
2. Extend `GenerationSnapshot`/`GenerationReport` (test-first) to carry debugSeed, map name/type, node count, and hash.
3. In `generation_patch.cs`, collect every distinct GameObject across `tiles`/`flatTiles`/`fillTiles` (dedup by instance ID) and hash their world transforms; log alongside existing counts.
4. Add an F9-cycled Harmony prefix (`seed_force_patch.cs`) on `ProceduralTileGeneration.Generate` that forces either `debugSeed`+`useDebugSeed` or `mapSeed` to a fixed constant, to empirically test which field controls generation.
5. On CrossOver, force DebugSeed mode and generate Forest (Tiles) three times and Desert (ProceduralMesh) twice, comparing hashes; write the findings and fallback decision to docs/.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Code (all test-first, `task check` green): `generation_hash.cs` (SHA-256 over position/rotation/scale records, sorted by a quantized grid key so hierarchy order never matters) + `generation_hash_tests.cs`; `generation_report.cs` extended to log `map=`, `mapType=`, `debugSeed=`, `nodes=`, `hash=` alongside the existing fields, tests updated; `generation_patch.cs` rewritten to hash every distinct GameObject across `ProceduralTileGeneration.tiles`/`flatTiles`/`fillTiles` (a `newRoot`-hierarchy walk was tried first but `newRoot` is empty by the time `A_GenerationComplete` fires — nodes=0, abandoned); `seed_force_patch.cs` adds an F9-cycled Harmony prefix on `ProceduralTileGeneration.Generate` forcing `debugSeed`+`useDebugSeed=true` (`DebugSeed` mode) or `MapGenerationController.mapSeed` (`MapSeedOnly` mode) to a fixed constant (20261007).

Live-tested on CrossOver/macOS (build 1.0.69), driven interactively via the running game with the maintainer at the keyboard (hotkey + map navigation) while I read `MelonLoader/Latest.log` after each generation. Full results, exact hashing method, and the fallback decision are in `docs/map-generation-determinism.md`.

Forest (`MapForest`, `mapType=0`/Tiles): 3 full generations with `debugSeed` forced to 20261007 produced byte-identical hashes (`0F5D88E2...`) despite `mapSeed` differing every time (1073930310, 1701581358, 111760902). Confirms AC #4 directly: `debugSeed` (not `mapSeed`) controls tile generation; `mapSeed` is a separately-randomized value disconnected from the actual layout.

Desert (`MapDesert`, `mapType=1`/ProceduralMesh): 2 full generations also produced identical hashes (`692987B2...`), but `debugSeed` read back as 1952838951 both times — our forced 20261007 did not take effect for this map type, meaning its generation path doesn't honor the same `ProceduralTileGeneration.Generate` parameters. Still reproducible in practice, but not yet controllable; flagged as an open follow-up (likely `MapGenerationController.proceduralMapMeshGenerator`/`MapGenerator` is the real seed source) rather than guessed at.

Fallback decision: determinism holds for both map types tested, so "seed + edits" stays the save format project-wide — no full-layout-snapshot fallback needed. The mod must force `useDebugSeed=true` + a chosen `debugSeed` (not `mapSeed`) when generating a map it intends to save/reproduce on Tiles maps; ProceduralMesh maps need their real seed field identified before the mod can choose/control a reproducible seed for them, tracked as a follow-up rather than a blocker since reproducibility itself was confirmed.

One operational note: a running Megabonk process does not hot-reload the mod DLL — had to confirm the deployed DLL's SHA-256 matched the latest build and have the maintainer fully quit/relaunch after every code change before testing (per [[feedback-verify-deployed-mod-dll]]), three times this session.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
