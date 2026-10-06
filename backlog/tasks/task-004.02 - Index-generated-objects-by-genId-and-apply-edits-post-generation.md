---
id: TASK-004.02
title: Index generated objects by genId and apply edits post-generation
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
labels:
  - level-editor
dependencies:
  - TASK-004.01
parent_task_id: TASK-004
priority: high
type: feature
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
- [ ] #1 Every spawned tile/object after generation completes is assigned a genId per TASK-002.03's scheme and indexed for lookup
- [ ] #2 At least one tile height/slope edit from a loaded level file is applied and visibly changes the real, running map
- [ ] #3 At least one object add and one object remove/move edit from a loaded level file is applied and visibly changes the real, running map
- [ ] #4 Tile spacing/size used when instantiating/moving tiles is read from StageData.mapParameters at runtime, never a hardcoded constant
- [ ] #5 catalogId-referenced prefabs are resolved against the real game's prefab catalog (DataManager.Instance.maps -> stages -> ...), not a hand-maintained duplicate list
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
