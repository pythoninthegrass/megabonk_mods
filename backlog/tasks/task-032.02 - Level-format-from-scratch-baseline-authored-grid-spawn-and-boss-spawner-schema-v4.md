---
id: TASK-032.02
title: >-
  Level format: from-scratch baseline, authored grid, spawn and boss spawner
  (schema v4)
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 20:37'
labels: []
dependencies:
  - TASK-032.01
parent_task_id: TASK-032
priority: high
ordinal: 155000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032: levels are an edit stack over the game's generated baseline map. This task defines the file format for a from-scratch level and its validation; the runtime that consumes it is a separate subtask.

Agreed format, schemaVersion 4: a "baseline" key (absent or "generated" keeps today's behaviour, "none" means from-scratch); map, stageIndex and tier still choose the kit (tile prefabs, stage data, enemies, music); "grid" holds width, depth and a sparse list of cells {x, z, height, slope}, where a missing cell is empty and slope defaults to none; "spawn" and "bossSpawner" each carry a position and rotation and replace playerStart and the generated boss spawner for from-scratch files; edits remain for object placements. The seed stays optional for from-scratch files.

Rules: a from-scratch file requires grid, spawn and bossSpawner. A grid is rejected in a generated-baseline file. Tile edit ops and gen: object targets are rejected in a from-scratch file, because the grid is the single source of truth. Cells must lie inside width by depth and may not repeat. Width and depth are capped by the kit's stock generator size (Forest is 15 by 15) when the level loads. Files at schema version 3 must load and behave exactly as before.

The grid must convert to the LevelState that the reachability validator and live edit plan already consume, so those are reused. Existing code: src/MegabonkLevels.Mod/level_file.cs, level_file_serialization.cs, level_file_migration.cs; docs/level-format.md. Write the tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A from-scratch file with grid, spawn, bossSpawner and placements round-trips through serialize and deserialize unchanged
- [ ] #2 A from-scratch file missing grid, spawn or bossSpawner is rejected with a message naming the missing field
- [ ] #3 A from-scratch file containing a tile edit op or a gen: target is rejected; a generated-baseline file containing a grid is rejected
- [ ] #4 Out-of-range and duplicate cells are rejected
- [ ] #5 Every existing schema version 3 level file in levels/ loads and produces the same edits as before
- [ ] #6 The grid converts to a LevelState that the reachability validator accepts, covered by a test
- [ ] #7 docs/level-format.md documents the from-scratch format and no longer states that tile ops never apply over an empty grid
- [ ] #8 Tests were written before the implementation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
