---
id: TASK-032.02
title: >-
  Level format: from-scratch baseline, authored grid, spawn and boss spawner
  (schema v4)
status: Done
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 21:35'
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
- [x] #1 A from-scratch file with grid, spawn, bossSpawner and placements round-trips through serialize and deserialize unchanged
- [x] #2 A from-scratch file missing grid, spawn or bossSpawner is rejected with a message naming the missing field
- [x] #3 A from-scratch file containing a tile edit op or a gen: target is rejected; a generated-baseline file containing a grid is rejected
- [x] #4 Out-of-range and duplicate cells are rejected
- [x] #5 Every existing schema version 3 level file in levels/ loads and produces the same edits as before
- [x] #6 The grid converts to a LevelState that the reachability validator accepts, covered by a test
- [x] #7 docs/level-format.md documents the from-scratch format and no longer states that tile ops never apply over an empty grid
- [x] #8 Tests were written before the implementation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/MegabonkLevels.Tests/from_scratch_level_tests.cs: round trip, missing grid/spawn/bossSpawner (message names field), tile op / gen: target in from-scratch, grid in generated baseline, out-of-range and duplicate cells, all levels/*.mblevel.json load with unchanged edits, grid -> LevelState -> ReachabilityValidator, v3 -> v4 migration. Run and confirm red.
2. LevelFile: add Baseline, Grid, Spawn, BossSpawner (optional, omitted when null); update Equals. Types LevelGrid(Width, Depth, Cells) with ToLevelState via LevelState.FromTiles, cell (X, Z, Height, Slope) with slope names, omitted when None; SpawnPoint(Position float[3], Rotation Euler degrees float[3]).
3. CurrentSchemaVersion 4 with a [3] migration step that only bumps the version.
4. level_file_validation.cs LevelFileValidator, called from Deserialize and DeserializeWithMigration. From-scratch means baseline == none; unknown baseline values rejected; seed optional.
5. docs/level-format.md: document from-scratch format, scope the tile-ops-over-generated-grid paragraph to generated baseline, update schemaVersion row and migration paragraph.
6. task check, then one conventional commit without attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added schema v4 from-scratch level format: `baseline`, `grid` (`LevelGrid`/`AuthoredCell`), `spawn` and `bossSpawner` (`SpawnPoint`) on `LevelFile`, all omitted from output when absent so v3 files serialize as before. `LevelFileValidator` runs from both deserialize paths and rejects missing grid/spawn/bossSpawner (naming the field), tile ops and `gen:` targets in from-scratch files, a grid under a generated baseline, unknown baseline values, bad grid size, and out-of-range or duplicate cells. `LevelGrid.ToLevelState()` feeds the existing `ReachabilityValidator`. 3 -> 4 migration only bumps the version. Tests (`from_scratch_level_tests.cs`) were written first and confirmed failing; every `levels/*.mblevel.json` loads with unchanged edits. Docs updated. The Mod project is C# 10 with nullable disabled, so the new types are record structs with a non-generic enum converter. The grid size cap per kit is left to the runtime subtask.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
