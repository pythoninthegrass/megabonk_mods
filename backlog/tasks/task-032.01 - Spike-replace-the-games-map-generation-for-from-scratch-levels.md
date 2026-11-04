---
id: TASK-032.01
title: 'Spike: replace the game''s map generation for from-scratch levels'
status: Done
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 21:26'
labels: []
dependencies: []
parent_task_id: TASK-032
priority: high
ordinal: 154000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032 makes a level able to declare itself from-scratch: the file authors the whole tile grid and objects, and nothing is generated and then torn down. Agreed approach: replace the game's tile generation with the authored grid rather than generating a stock map and deleting it. This spike decides whether that is viable before any format or runtime code is written.

Today the game generates a full stock map (MapGenerationController.GenerateMap, ProceduralTileGeneration.Generate, then the object phases), and the mod replays edits after A_GenerationComplete. Read fields and signatures in .tools/il2cpp_dump/dump.cs (task re:dump); method bodies are native code, so use Ghidra through REA (docs/development.md, "Using Ghidra through REA").

Questions to answer with evidence: (1) What Generate sets besides proceduralTiles (current stage and map parameters, tile parent, collider, fill and edge passes, world edges), and what GenerateMap does with the returned spawn position, first-tile direction and tileSpawnPosition. (2) Whether skipping GenerateTileObjects.Generate, SpawnInteractables.SpawnChests and SpawnShrines, and RandomObjectPlacer.GenerateInteractables still lets GenerateMap finish and A_GenerationComplete fire. (3) Where the spawn portal, spawn platform, boss spawner and boss portal are instantiated and from what position. (4) How the catch floor trigger, minimap, map edges and grass are sized: from the grid array or from map parameters.

Go/no-go: if replacing generation breaks GenerateMap and needs more than localized patches, the runtime subtask switches to generating the stock map and clearing it in one step, and the maintainer is told before work continues. No shipped code comes from this task; a throwaway patch proving a small authored grid is fine.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the four questions is answered in docs/runtime-map-structure.md under a new section on replacing generation, with the evidence source (dump field, Ghidra RVA or in-game log)
- [x] #2 A throwaway patch is shown in the running game to load a small authored flat grid with no generated props, the player at the spawn portal and a boss spawner present, or the doc records exactly what blocked it
- [x] #3 The doc states a go or no-go for replacing generation and names the fallback if no-go
- [x] #4 The doc states whether the boss portal needs its own authored position or follows the boss spawner
- [x] #5 No throwaway patch code is left in the shipped mod
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Static pass (read-only). Open GameAssembly.dll in Ghidra through REA (provider_id ghidra, ~12 min first analysis). Decompile MapGenerationController.GenerateMap (RVA 0x49A640 plus the <GenerateMap>d__39 MoveNext), ProceduralTileGeneration.Generate (0x5208A0), GenerateTileObjects.Generate (0x495870), RandomObjectPlacer.GenerateInteractables (0x49C020), SpawnInteractables.SpawnChests/SpawnShrines (0x49CF60/0x49E180), MapEdges.Set (0x499B80), TilePositionToWorldPosition (0x5220E0). Answer Q1-Q4 from pseudocode, with dump fields (spawnPortal 0x58, bossPortal 0x60, spawnPlatform 0x68, colliderBox 0x50, minimapMesh 0x48, grassRenderer 0x90, mapEdges 0x98, tileSpawnPosition/tileSpawnDir statics) as the field-level evidence.
2. Dynamic pass. Throwaway Harmony prefix on ProceduralTileGeneration.Generate in a scratch file (not committed) that fills proceduralTiles/tiles with a small flat grid, sets the return spawn position/direction, and skips the object phases. Build with task mod:build, task game:editor / relaunch, check Latest.log for GenerationComplete, spawn portal, boss spawner, and screenshot via the megabonk MCP.
3. Write a new section on replacing generation in docs/runtime-map-structure.md: Q1-Q4 answers with evidence source, go/no-go, fallback if no-go, and whether the boss portal needs its own authored position.
4. Delete the throwaway patch, confirm git diff shows only the doc and backlog changes, run task check, commit as docs(...) with no attribution.

Open risk: the dynamic pass needs MEGABONK_DEV=true and the game running on this box (CrossOver bottle); if it cannot launch, AC #2 records what blocked it.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Static pass (Ghidra via REA) and dynamic pass both done; results are in docs/runtime-map-structure.md, section 'Replacing generation for from-scratch levels'. Verdict: go. GenerateMap ignores the return values of GenerateTileObjects.Generate and the SpawnInteractables/RandomObjectSpawner phases; Generate must leave a collider with a mesh; world size comes from MapParameters.size * scaledTileWidth plus tile heights; the boss portal on Tiles maps is part of the boss spawner prefab (no own position). Throwaway 5x5 patch in the running game: A_GenerationComplete fired with objects=0, kill floor armed, player at the centre cell, one PlayerSpawnPortal and the boss spawner present. Not checked: grass placement and minimap content. The earlier startup hang cleared once accessibility access was granted to the host app. Throwaway patch removed from the tree; a copy is at .tools/evidence/spike_authored_grid.cs.txt (gitignored).
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
