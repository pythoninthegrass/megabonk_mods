---
id: TASK-002
title: 'Spike: prove the hook surface'
status: To Do
assignee: []
created_date: '2026-10-06 21:39'
labels:
  - level-editor
dependencies:
  - TASK-001
priority: high
type: spike
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: prove, with a running MelonLoader mod against the real game, the three assumptions every later task depends on. This is a gate — TASK-003 through TASK-007 should not start until this is Done, because each assumes MelonLoader hooking works, map generation is seed-deterministic, and the tile/navmesh surface is reachable from a mod.

## Project context

Megabonk is Unity 2023.2.22f1, IL2CPP, metadata v29 (Steam app 3405340, build 21750826). No mod loader is currently installed. TASK-001 scaffolds the build/tooling (taskfile, PEP 723 scripts, C# project skeleton, `task re:dump` for Il2CppDumper output) that this task's mod code will be built with and deployed through.

From an Il2CppDumper pass run manually earlier in this session (dump.cs / script.json, ~203k methods, now superseded by `task re:dump` output in `.tools/il2cpp_dump/`):

- **Map generation is driven by `MapGenerationController`** (MonoBehaviour), coroutine `GenerateMap()`, with static fields `mapSeed` and `isGenerating`, and static Actions `A_PreGeneration` / `A_GenerationComplete` — these are the intended hook points for forcing a seed and for post-processing the generated map.
- It holds references to `ProceduralTileGeneration`, `RandomObjectPlacer`, `GenerateTileObjects`, `SpawnInteractables`, `GrassChunkManager`, `MapEdges`, `MapGenerator`.
- **`ProceduralTileGeneration.Generate(out firstTileDirection, StageData, MapParameters, bool useDebugSeed)`** builds a grid of `ProceduralTile` objects (`proceduralTiles[][]`, `tiles`, `flatTiles`, `fillTiles` lists). Height comes from `MazeHeightGenerator.GenerateHeight`.
- **`MapParameters`** (a ScriptableObject field on `StageData`) holds `size`, `scale`, `tileWidth`/`tileHeight`, `volatility`, `slopeStrength`, `flatMapBias`, `heightGenerationStrategy` — i.e. tile spacing/sizing is data-driven, not hardcoded, and must be read at runtime rather than assumed.
- **`SpawnInteractables.SpawnShit()`** calls `SpawnChests`, `SpawnShrines`, `SpawnOther`, `SpawnRails` (46 chests, 14 shrines per stage are the defaults seen in code).
- **`MapController`** (static) exposes `StartNewMap(RunConfig)`, `LoadNextStage()`, `TestMap(MapData, StageData)`, `TestMap(RunConfig)`, `RestartRun()`.
- The engine assemblies list includes `Unity.AI.Navigation` (NavMeshSurface) — levels likely rebuild/bake a navmesh for enemy pathing, relevant once edits need to keep enemies able to path.
- No existing save/load of map layout exists; `MapGenerator`/`ProceduralTileGeneration` default seed is 105, with a `debugSeed` field. This is the entire basis for the "seed + edits" level model — it has NOT yet been confirmed deterministic.

All of the above comes from reading type/field/method declarations in the Il2CppDumper output, NOT from decompiling method bodies or observing runtime behavior. Treat it as a strong hypothesis to verify, not a confirmed fact — this task's entire purpose is to convert it into verified fact (or correct it).

## What this spike must establish

1. MelonLoader actually loads and can hook this game, on both CrossOver/macOS and Windows.
2. Whether `MapGenerationController`'s generation is deterministic given the same seed, map, and stage (this determines whether "seed + edits" is viable at all, or whether a fallback to full-layout snapshots is needed).
3. Where the runtime tile grid, per-tile transform/position data, tile spacing/size source, and the scene's NavMeshSurface actually live, so TASK-004 can index objects by a stable `genId` and TASK-004/TASK-005 can rebuild navigation after edits.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A MelonLoader mod built from TASK-001's scaffold loads successfully in Megabonk on CrossOver/macOS, logging a message when MapGenerationController.A_GenerationComplete fires
- [ ] #2 The same mod, built and run unmodified, also loads and logs successfully on a Windows install of Megabonk
- [ ] #3 A documented test generates the same map/stage/seed twice and compares a hash of all spawned tile and object transforms; the result (deterministic or not) is recorded in docs/, with a fallback decision documented if not deterministic
- [ ] #4 The runtime location of the tile grid, the authoritative source of tile spacing/size (confirmed against StageData.mapParameters, not assumed), and the scene's NavMeshSurface are documented with concrete type/field names verified against the running game (not just dump.cs declarations)
- [ ] #5 Findings are written to a docs/ file that TASK-003 and TASK-004 can cite directly
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
