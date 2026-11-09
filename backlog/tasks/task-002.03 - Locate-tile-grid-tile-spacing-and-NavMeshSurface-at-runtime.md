---
id: TASK-002.03
title: 'Locate tile grid, tile spacing, and NavMeshSurface at runtime'
status: Done
assignee:
  - pythoninthegrass
created_date: '2026-10-06 21:40'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-002.01
parent_task_id: TASK-002
priority: high
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
- [x] #1 The tile grid's actual runtime shape and accessible fields are documented with field names confirmed via Il2CppInterop access from a running mod, not just dump.cs declarations
- [x] #2 Tile spacing/size is confirmed to come from StageData.mapParameters by cross-checking the data value against measured in-game tile transform distances for at least 2 stages
- [x] #3 Whether a NavMeshSurface (or other pathing mechanism) is used is confirmed, and if so, the rebuild/bake trigger a mod can invoke after edits is identified
- [x] #4 A concrete, deterministic genId scheme for indexing generator-spawned objects is proposed and written up, ready for TASK-004 to implement
- [x] #5 All findings are written to a docs/ file consumable by TASK-003 and TASK-004 without re-deriving them
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

Static analysis first (ilspycmd decompile of `.tools/il2cpp_dump/DummyDll/*.dll` declarations), then runtime verification against the live, already-running CrossOver Megabonk instance (mod already loaded from TASK-002.02 work).

Static findings so far:
- `ProceduralTileGeneration.proceduralTiles` is `ProceduralTile[][]` (dense jagged 2D array) — confirms AC#1's "dense 2D array" hypothesis at the declaration level; runtime check needed to confirm it's actually populated post-generation (vs. the `tiles`/`flatTiles`/`fillTiles` lists which TASK-002.02 already proved are live at `A_GenerationComplete`).
- `StageData.mapParameters` (type `MapParameters`) has `tileWidth`/`tileHeight`/`scale`/`scaledTileWidth`/`scaledTileHeight`/`size`. `ProceduralTileGeneration.currentStage`/`currentMapParameters` are the live instance fields set by `Generate()` but are C# `private` — readable via reflection (`BindingFlags.NonPublic`) same as any interop proxy field, no IL2CPP-specific blocker.
- `MapGenerator.GenerateMap(MapData, StageData, int seed = 105)` takes an explicit `seed` parameter — this is very likely the actual seed source for `ProceduralMesh` maps (Desert) that TASK-002.02 left unresolved (debugSeed force had no effect there). Worth confirming/patching as a bonus, not required for this task's AC.
- NavMesh: `Unity.AI.Navigation.NavMeshSurface` is referenced by exactly one type in the whole decompiled `Assembly-CSharp`: `RsgController.navmeshSurface`. `RsgController` is a room-piece ("Rsg") dungeon generator used for the **crypt/graveyard boss dungeon** (`MapGenerationController.cryptParent`/`cryptExitOutside`/`rsgController`/`CryptGeneration()`), not the main Tiles/ProceduralMesh map types (`EMapType` only has `Tiles`/`ProceduralMesh` — crypt is a special-cased side-dungeon, not a third map type). `EnemyMovementRb` (main enemy movement) has no NavMeshAgent-style fields — it's direct Rigidbody-based chase, confirming the open-world maps don't use navmesh at all.

## Remaining work

1. Extend the mod (`src/MegabonkLevels.Mod/`) to log, on `A_GenerationComplete`: `proceduralTiles` shape (row count + per-row lengths), the resolved `MapParameters` values via reflection, and a measured world-distance between two adjacent non-null tiles in the grid, to cross-check against `scaledTileWidth`/`scaledTileHeight`.
2. Add a Harmony postfix on `Unity.AI.Navigation.NavMeshSurface.BuildNavMesh` (and log `RsgController.Generate`/`MapGenerationController`'s crypt path if reachable) to empirically confirm whether/when a navmesh bake actually fires, rather than assuming from the referenced-field static finding alone.
3. Build + deploy, ask the maintainer to retrigger Forest and Desert generation (same restart-the-run method as TASK-002.02) to capture new log lines for AC#1/#2, and enter a crypt dungeon if feasible to capture AC#3 runtime confirmation.
4. Propose a concrete `genId` scheme (doc-only, per AC#4): `"{category}:{sequentialIndex}"` per deterministic spawn-order source list (`tile`, `flatTile`, `fillTile`, `randomObject:{spawnerName}`, `tileObject`, `chest`, `shrine`, `rail`), relying on TASK-002.02's confirmed determinism.
5. Write `docs/runtime-map-structure.md` consolidating all of the above for TASK-003/TASK-004.
6. Commit mod changes + docs with conventional commit, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Runtime verification completed against the live CrossOver/macOS instance (game 1.0.69), mod extended with grid_shape_patch.cs (grid shape + measured spacing) and navmesh_patch.cs (BuildNavMesh hook). Full detail in docs/runtime-map-structure.md.

proceduralTiles is a dense, fully-populated size x size jagged array for Tiles maps (Forest 15x15=225, Graveyard 19x19=361, both matching tiles.Count exactly). Desert (ProceduralMesh) never populates it at all - currentStage/currentMapParameters stay null, confirming ProceduralMesh maps don't use this grid/spacing model.

currentStage/currentMapParameters are declared private in the dumped declarations but Il2CppInterop generates them as public properties - no reflection needed, direct access works. First attempt used reflection against the dump's declaration and silently returned null.

Measured adjacent-tile world distance matched MapParameters.scaledTileWidth exactly (40.0 units) on both Forest and Graveyard.

NavMesh confirmed via Harmony postfix on NavMeshSurface.BuildNavMesh: fires exactly once, on RSG_Controller, only during Graveyard's crypt/boss-dungeon generation. Never fires for Forest or Desert. Rebuild trigger for future mods: call rsgController.navmeshSurface.BuildNavMesh() directly.

Regression found and fixed: Harmony-patching RsgController.Generate(int, EDungeonType, out float) crashed the IL2CppInterop native-managed trampoline with a NullReferenceException on every crypt entry, hanging the game at a black screen (reproduced twice). Not the patch body itself (ruled out via try/catch + a prefix log line that never fired before the crash). Removed that patch; crypt now loads normally with only the BuildNavMesh hook active. Documented as a do-not-patch gotcha.

genId scheme proposed (doc-only, not implemented): {category}:{sequentialIndex} per deterministic spawn-order source list, relying on TASK-002.02's confirmed determinism.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extended the mod with `grid_shape_patch.cs` and `navmesh_patch.cs`, rebuilt/redeployed against the live CrossOver install, and captured runtime log evidence across Forest, Desert, and Graveyard (crypt) generations.

**Confirmed (docs/runtime-map-structure.md):**
- `proceduralTiles` is a dense, fully-populated `size x size` jagged array for Tiles maps (Forest 15x15=225, Graveyard 19x19=361, exactly matching `tiles.Count`); Desert (ProceduralMesh) never populates it - confirms the tile-grid model doesn't apply to that map type at all.
- `currentStage`/`currentMapParameters` look private in the dumped declarations but Il2CppInterop generates them as public properties - direct access, no reflection needed (first attempt wrongly used reflection and silently got null).
- Measured adjacent-tile world distance matched `MapParameters.scaledTileWidth` exactly (40.0 units) on both Forest and Graveyard - confirmed spacing source for 2 stages per AC#2.
- NavMesh bake confirmed via Harmony postfix on `NavMeshSurface.BuildNavMesh`: fires once, on `RSG_Controller`, only for the Graveyard map's crypt/boss dungeon - never for Forest or Desert. Rebuild trigger for a future mod: call `rsgController.navmeshSurface.BuildNavMesh()` directly.
- genId scheme proposed (doc-only): `{category}:{sequentialIndex}` per deterministic spawn-order list, built on TASK-002.02's confirmed determinism.

**Regression found and fixed along the way:** Harmony-patching `RsgController.Generate(int, EDungeonType, out float)` crashed the IL2CppInterop trampoline with a NullReferenceException on every crypt entry (reproduced twice, black-screen hang). Ruled out the patch body (try/catch + a prefix log line that never fired before the crash), removed that one patch, kept only the `BuildNavMesh` hook - crypt now loads normally. Documented as a do-not-patch gotcha.

**Tests:** existing xUnit suite still green (8/8, no new pure-logic code introduced - genId is a documented proposal, not implemented code). `dotnet build` clean, `markdownlint` clean on the new doc.

**Follow-ups not in scope here:** ProceduralMesh (Desert) seed control is still unconfirmed (noted as a lead: `MapGenerator.GenerateMap(MapData, StageData, int seed = 105)`); genId scheme is unimplemented, and only proposed for Tiles maps.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
