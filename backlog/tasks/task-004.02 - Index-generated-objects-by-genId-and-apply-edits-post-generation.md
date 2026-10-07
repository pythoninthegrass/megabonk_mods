---
id: TASK-004.02
title: Index generated objects by genId and apply edits post-generation
status: In Progress
assignee:
  - '@pythoninthegrass'
created_date: '2026-10-06 21:42'
updated_date: '2026-10-07 23:28'
labels:
  - level-editor
dependencies:
  - TASK-004.01
parent_task_id: TASK-004
priority: high
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context.

On `A_GenerationComplete`, walk the real spawned tiles/objects (using TASK-002.03's documented runtime tile grid location and shape) and assign each a `genId` using the scheme TASK-002.03 proposed, building an index from `genId` to the actual live GameObject/tile. Then apply the loaded level file's edit operations (TASK-003.02's op types) against this live index:

- Tile ops (`SetTileHeight`, `SetTileSlope`, `AddTile`, `RemoveTile`) mutate or instantiate/destroy the real tile GameObjects, respecting the real tile spacing/size from `StageData.mapParameters` (per TASK-002.03 — never hardcode spacing here).
- Object ops (`PlaceObject`, `MoveObject`, `RemoveObject`) resolve `catalogId` references (TASK-003.05's format) against the real prefab catalog (`DataManager.Instance.maps → stages → ...`) to instantiate new objects, and resolve `genId`/placement-id targets against the index built above for move/remove.

This is the core "apply the edit list to the live game" logic — reuse TASK-003's op types and `LevelState` semantics directly rather than reimplementing edit logic against live GameObjects from scratch; the live application should mirror what TASK-003's `EditStack.Apply` does against the in-memory model, just targeting real objects instead of data records.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every spawned tile/object after generation completes is assigned a genId per TASK-002.03's scheme and indexed for lookup
- [ ] #2 At least one tile height/slope edit from a loaded level file is applied and visibly changes the real, running map
- [ ] #3 At least one object add and one object remove/move edit from a loaded level file is applied and visibly changes the real, running map
- [x] #4 Tile spacing/size used when instantiating/moving tiles is read from StageData.mapParameters at runtime, never a hardcoded constant
- [ ] #5 catalogId-referenced prefabs are resolved against the real game's prefab catalog (DataManager.Instance.maps -> stages -> ...), not a hand-maintained duplicate list
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

1. Pure core (xUnit, tests first): `GenIdAssigner` assigns `{category}:{index}` ids over ordered sequences; `LiveEditPlan` replays `level.Edits` through a fresh `EditStack`/`LevelState` and emits flat live actions (set/remove tile at x,z; move/remove genId target; spawn catalogId at transform).
2. Mod layer (`live_edit_patch.cs`): on `A_GenerationComplete`, build genId -> GameObject index (tiles/flatTiles/fillTiles, then spawner lists found at runtime), apply plan. Tile spacing from `currentMapParameters.scaledTileWidth`/`scaledTileHeight`; catalogId resolved by walking `DataManager.Instance.maps -> stages -> ...` per `catalog_id.cs` grammar, no duplicate list.
3. Wire-up: `LevelLoaderPatch` stashes loaded edits; apply only when a level file started the run. Tiles-type maps only; warn on others.
4. Verify on macOS/CrossOver via osascript: deploy, Forest test level (tile height edit, object remove/move, object place), F6, check Latest.log + screenshot.
5. Docs (`runtime-map-structure.md`, `level-format.md`), conventional commit, no attribution.

## Risks
- Live tile height/slope encoding unknown; inspect `ProceduralTile` at runtime first. Fill-piece consistency for Add/RemoveTile.
- Spawner lists' live field names unconfirmed.
- osascript driving may be unwieldy; stop and tell Lance if so.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified live on macOS/CrossOver (Forest, seed 20261007, game 1.0.69). MelonLoader 0.7.3 was missing from the Mac install and was installed with task game:melonloader:install. Log evidence: index built with 1474 objects (identical counts across loads); tile (9,7) moved -20 -> 60 (scaledTileHeight=20 read at runtime); gen:object:Tree0:0047 removed; gen:object:Tree0:0289 moved; interactable/chest spawned as placement:0; 'applied 4 edit(s)', no errors.

NOT verified: a clear screenshot of the edits in the running map. Driving the game with osascript key presses (no reliable mouse input, level-up dialog, idle player dying within ~20s, death-cam) made the visual check unreliable, so AC #2 and #3 are left unchecked pending a visual confirmation by Lance. AC #5 left unchecked: only the interactable/chest route was exercised live; the DataManager.Instance.maps -> stages -> randomMapObjects/stageTilePrefabs/shrines routes compile and are unit-tested for parsing but were not run live.

Not supported yet (logged as warnings): non-None slope edits, AddTile on a cell with no live tile. Height edits do not adjust neighbouring wall/fill pieces. Edit-stack ops RemoveTile has no representation in LevelState (it just deletes the record), so LiveEditPlan emits it directly from the op.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
