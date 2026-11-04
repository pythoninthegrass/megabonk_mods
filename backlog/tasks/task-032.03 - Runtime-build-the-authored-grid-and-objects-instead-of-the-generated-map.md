---
id: TASK-032.03
title: 'Runtime: build the authored grid and objects instead of the generated map'
status: Done
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 22:03'
labels: []
dependencies:
  - TASK-032.01
  - TASK-032.02
parent_task_id: TASK-032
priority: high
ordinal: 156000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. When a loaded level is from-scratch (format subtask), the game must build the authored grid and objects and show none of the stock map's generated tiles, props or interactables, with no generate-then-tear-down pass.

Approach follows the spike's go/no-go: if go, replace the generator's output with the authored grid using the game's own tile instantiation, skip the generated object phases, and place the spawn portal and boss spawner at the authored positions before they are instantiated where the game allows. If no-go, generate the stock map and clear it in one step under the startup cover.

Constraints from existing work: the startup gate and cover (src/MegabonkLevels.Mod/startup_gate.cs, startup_cover.cs) exist because the generated spawn portal moves the player to a cached baseline position after the mod places them; for a from-scratch level the portal must land at the authored spawn, so the final placement is a no-op when the player is already in place. Keep the gate and do not fork it. A death-screen restart (MapController.RestartRun) is a second startup and must still work. Generated-baseline levels must be untouched. Reuse TilePlacement and the slope conventions in edit_operations.cs. Keep pure layout logic (cell to tile arguments, slope direction, size cap) Unity-free and unit tested; write those tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Loading a from-scratch level shows only the authored tiles and placed objects; no generated props, chests, shrines or tile objects exist in the scene
- [x] #2 The player starts at the authored spawn with no spawn reset and no visible stock-map flash
- [x] #3 The boss spawner exists at the authored position and spawns a boss that can reach ground
- [x] #4 A grid larger than the kit's stock size is refused at load with a logged reason
- [x] #5 A death-screen restart returns the player to the authored spawn
- [x] #6 Generated-baseline levels, including levels/thps.mblevel.json and levels/example-forest.mblevel.json, load exactly as before
- [x] #7 Pure layout logic has unit tests written first, including a startup_gate case for the already-in-place spawn
- [x] #8 docs/development.md and docs/runtime-map-structure.md describe the from-scratch load path
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (tests/MegabonkLevels.Tests): FromScratchLayout (grid size cap with refusal reason, cell to tile arguments, slope direction via TilePlacement.UphillVector, spawn cell/direction) and a startup_gate case where PlacementCompleted is a no-op when the player is already at the authored spawn. Confirm they fail, then implement.
2. Runtime: from_scratch_generation_patch.cs, active only for a from-scratch custom level. Prefix on ProceduralTileGeneration.Generate builds the authored grid with the game's InstantiateTile, a cloned MapParameters sized to the grid, CollisionRebuild for collider, no edge fill, and returns the authored spawn position/direction.
3. Skip prefixes on GenerateTileObjects.Generate, SpawnRails, SpawnChests, SpawnShrines, SpawnOther and RandomObjectSpawner; the mod places the boss spawner at the authored bossSpawner position.
4. Player start for from-scratch levels comes from level.Spawn; gate and cover are kept, not forked. LevelLoaderPatch refuses a grid over the stage's stock MapParameters.size with a logged reason before StartNewMap.
5. Verify the death-screen restart (RestartRunPrefix re-arms the cover) regenerates the from-scratch level and lands at the authored spawn.
6. Add a hand-written from-scratch fixture under levels/ (approved) for in-game checks; verify with relaunch, log, query_objects, screenshots, death restart, and thps/example-forest regression loads.
7. Update docs/development.md and docs/runtime-map-structure.md; task check; conventional commit with no attribution. Stop and ask if the spike's open items (grass, minimap, teal tint/walls) need real work.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
From-scratch levels now build their authored grid instead of the generated map (spike verdict "go"). FromScratchGenerationPatch replaces ProceduralTileGeneration.Generate with the authored cells via the game's InstantiateTile on a cloned MapParameters sized to the longer grid side, rebuilds the collider with CollisionRebuild, skips the rail/chest/shrine/other/random-object phases and GenerateTileObjects.Generate, and instantiates the stage's bossSpawner at the authored position. LevelLoaderPatch arms the patch per load and refuses a grid over the stage's stock MapParameters.size with a logged reason. The startup gate is unchanged; StartupCover.AttemptPlace skips the teleport when the body is within 0.5 of the start. Pure logic is in from_scratch_layout.cs with tests written first (size cap, tile arguments, in-place check) plus a startup_gate already-in-place case. Added levels/from-scratch-fixture.mblevel.json (7x7, one ramp). Verified in the running game: tiles=49 objects=0, 49 tile clones and no clone chests, player at the spawn on first load and after a death-screen restart, oversize 16x7 refused, example-forest (tiles=225 objects=848) and thps (1241 edits) load as before, a summoned boss walks across the grid. Not verified: the absence of a visible flash was concluded from no stock map being generated, not by frame capture; boss y stays at the spawner prefab's pivot offset so ground contact is inferred from it chasing across the grid. Open and uninvestigated from the spike: the teal tint and translucent walls around the grid, and grass placement. Tiles are not static-batched and no edge fill is built; bossSpawnerFinal is not used.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
