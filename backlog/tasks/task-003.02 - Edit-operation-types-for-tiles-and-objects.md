---
id: TASK-003.02
title: Edit operation types for tiles and objects
status: To Do
assignee: []
created_date: '2026-10-06 21:41'
labels:
  - level-editor
dependencies:
  - TASK-003.01
parent_task_id: TASK-003
priority: high
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-003 first for full context.

Implement the typed edit operations that populate the `edits` array from TASK-003.01's level schema, as pure data types (records/plain classes, no Unity types):

- **Tile operations**: `SetTileHeight {x, z, height}`, `SetTileSlope {x, z, direction | none}`, `AddTile {x, z, height}`, `RemoveTile {x, z}`.
- **Object operations**: `PlaceObject {catalogId, position, rotation, scale}`, `MoveObject {target (catalogId-placed id | genId), newTransform}`, `RemoveObject {target (catalogId-placed id | genId)}`.
- Target references distinguish between a `genId` (a generator-spawned object from TASK-002.03's scheme — format TBD by that task, treat as an opaque string here until confirmed) and an ID assigned to objects the editor itself placed (which this subtask should define — e.g. a simple incrementing placement ID scoped to the edit list).

Each op type needs: construction validation (e.g. rejecting a malformed catalogId format once TASK-003.05 defines that format — if TASK-003.05 hasn't landed yet, use a minimal placeholder validation and revisit), equality semantics for testing, and JSON serialization compatible with TASK-003.01's `edits` array.

TDD throughout: tests for valid construction, invalid construction (and what exception/result type is used for invalid input — decide and be consistent), and serialization round-trips for every op type.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All seven edit operation types (SetTileHeight, SetTileSlope, AddTile, RemoveTile, PlaceObject, MoveObject, RemoveObject) are implemented as pure data types with no Unity dependencies
- [ ] #2 Each op type has unit tests covering valid construction and at least one invalid-construction case
- [ ] #3 A consistent validation/error-reporting convention is used across all op types and documented
- [ ] #4 Object operations correctly distinguish genId targets from editor-assigned placement IDs
- [ ] #5 Every op type round-trips through JSON serialization inside the level schema's edits array from TASK-003.01
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
