---
id: TASK-032.01
title: 'Spike: replace the game''s map generation for from-scratch levels'
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
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
- [ ] #1 Each of the four questions is answered in docs/runtime-map-structure.md under a new section on replacing generation, with the evidence source (dump field, Ghidra RVA or in-game log)
- [ ] #2 A throwaway patch is shown in the running game to load a small authored flat grid with no generated props, the player at the spawn portal and a boss spawner present, or the doc records exactly what blocked it
- [ ] #3 The doc states a go or no-go for replacing generation and names the fallback if no-go
- [ ] #4 The doc states whether the boss portal needs its own authored position or follows the boss spawner
- [ ] #5 No throwaway patch code is left in the shipped mod
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
