---
id: TASK-002.03
title: 'Locate tile grid, tile spacing, and NavMeshSurface at runtime'
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
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-002 first for full context. Depends on TASK-002.01's hello-mod/hook being in place.

TASK-003 (level format) and TASK-004 (runtime editing/playback) both need concrete, verified answers to:

1. **Where is the tile grid at runtime?** Confirm `ProceduralTileGeneration`'s `proceduralTiles[][]`/`tiles`/`flatTiles`/`fillTiles` fields are reachable and populated post-generation (via Il2CppInterop field access from the mod), and document their actual shape (is it a dense 2D array, a sparse list, both?).
2. **What is the authoritative source of tile spacing/size?** Confirm `StageData.mapParameters` (`size`, `scale`, `tileWidth`/`tileHeight`, etc.) is what actually drives the generated grid's real-world spacing — read the value at runtime for at least 2 stages and cross-check against the actual measured distance between adjacent tile GameObjects' transforms. Do not hardcode a spacing constant anywhere downstream of this task.
3. **Where does the scene's NavMeshSurface live**, and what triggers a rebuild/bake? (`Unity.AI.Navigation` is a referenced assembly per earlier research, but confirm whether Megabonk's code actually bakes a runtime navmesh after generation, versus some other enemy-pathing mechanism — don't assume NavMeshSurface is used just because the package is referenced.) If a navmesh is baked, find the method/trigger a future mod can re-invoke after edits so enemies can path onto edited tiles.
4. **How are generated objects distinguishable/indexable** — i.e. can a stable `genId` (deterministic index like "spawner name + order spawned") be assigned to each object produced by `RandomObjectPlacer`/`GenerateTileObjects`/`SpawnInteractables`, so that TASK-004's edit application can target "the 3rd tree this run generated" reliably? Confirm spawn order is deterministic (should follow from TASK-002.02's determinism finding) and propose the concrete genId scheme.

Write all of this to a docs/ file (e.g. docs/runtime-map-structure.md) with concrete type names, field names, and any gotchas — this becomes required reading for TASK-003 and TASK-004.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The tile grid's actual runtime shape and accessible fields are documented with field names confirmed via Il2CppInterop access from a running mod, not just dump.cs declarations
- [ ] #2 Tile spacing/size is confirmed to come from StageData.mapParameters by cross-checking the data value against measured in-game tile transform distances for at least 2 stages
- [ ] #3 Whether a NavMeshSurface (or other pathing mechanism) is used is confirmed, and if so, the rebuild/bake trigger a mod can invoke after edits is identified
- [ ] #4 A concrete, deterministic genId scheme for indexing generator-spawned objects is proposed and written up, ready for TASK-004 to implement
- [ ] #5 All findings are written to a docs/ file consumable by TASK-003 and TASK-004 without re-deriving them
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
