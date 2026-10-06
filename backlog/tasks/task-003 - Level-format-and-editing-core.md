---
id: TASK-003
title: Level format and editing core
status: To Do
assignee: []
created_date: '2026-10-06 21:40'
labels:
  - level-editor
dependencies:
  - TASK-002
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: build the Unity-free, fully unit-testable core library that represents a user-built level as "seed + edits", can apply/undo/redo edits, and can validate that every tile on the resulting map is reachable. This is the foundation TASK-004 (runtime playback) and TASK-005 (editor UI) both build on, and it must be buildable and testable without Unity, Megabonk, or MelonLoader loaded — per TASK-001's scaffold, this lives in `src/MegabonkLevels.Mod`'s non-Unity-dependent files (or a dedicated `src/MegabonkLevels.Core` project if that split proves cleaner — decide and document in TASK-003's first subtask), compile-linked into `tests/MegabonkLevels.Tests` the same way xeno_mods links pure-logic files into its test project.

## Why "seed + edits"

Megabonk levels are fully procedural — there are no level files. `MapGenerationController.GenerateMap()` builds a stage from `MapData`/`StageData` ScriptableObjects plus a seed. The decided level model is: start from a generated map (map, stage, seed), then layer user edits (tile height/slope changes, object placement/removal) on top. TASK-002 is the gating spike that confirms generation is actually seed-deterministic (required for this model to work at all) and documents the runtime tile grid shape, tile spacing source, and a `genId` scheme for referencing generator-spawned objects. **Read TASK-002's findings docs before starting** — this task's design assumes TASK-002 passed with determinism confirmed; if TASK-002 instead concluded a full-layout-snapshot fallback was needed, this task's scope changes and should be re-scoped before starting.

## AlexK terrain-generator reference (for the reachability rule only)

A third-party Unity project (`.tools/mb_terrain_generator`, paid Patreon content — reference only, never copy its code or redistribute it) recreates Megabonk-style terrain with a "maze chain" algorithm: blocks are spawned one at a time into adjacent free grid cells; height rises by at most one step per chain step, and every rise places a slope block, guaranteeing every block in a chain is reachable from the previous one; cliffs (unreachable-without-help gaps) only occur between different chains. This is the model for the reachability validator in this task: a move between adjacent tiles is legal if the height difference is 0, or 1 via a slope facing that direction.

## What this task must produce

1. A level file format (suggest `.mblevel.json`, versioned schema, migratable) capturing: schema version, `gameBuildId` (for staleness warnings — see TASK-004), map/stage/tier identifiers, the seed, and an ordered list of edit operations.
2. A typed set of edit operations covering tile edits (set height, set/clear slope direction, add/remove a tile) and object edits (place from catalog, move, remove), each referencing targets either by a stable `catalogId` (for placeable prefabs) or `genId` (for referencing a specific generator-spawned object, per TASK-002.03's scheme).
3. An edit stack supporting apply/undo/redo over an in-memory level state model (pure data, no Unity types).
4. A reachability validator implementing the chain/slope rule above via BFS/graph search over the tile grid, reporting any unreachable tiles and whether a path exists from the spawn tile to the boss portal tile.
5. Catalog ID parsing/validation, reserving a `bundle:<pack>/<asset>` namespace for TASK-007's future custom-asset packs even though nothing produces those IDs yet.

Everything in this task is TDD: write a failing test, confirm it fails, implement the minimum to pass, refactor. No Unity APIs, no MelonLoader, no game process required to develop or run these tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A level file schema is implemented with round-trip serialize/deserialize tests and at least one documented migration path from schema version 1 to a hypothetical version 2
- [ ] #2 All edit operation types (tile height/slope/add/remove, object place/move/remove) are implemented as pure data types with unit tests covering valid and invalid construction
- [ ] #3 The edit stack supports apply, undo, and redo with tests covering multi-step sequences, undo-past-the-start, and redo-after-a-new-edit-invalidates-the-redo-stack
- [ ] #4 The reachability validator correctly identifies unreachable tiles and spawn-to-boss-portal connectivity on hand-built test grids, including a deliberate cliff-between-chains case and a case fixed by a slope
- [ ] #5 Catalog ID parsing validates the reserved namespaces (including bundle: for future use) and rejects malformed IDs, with unit tests
- [ ] #6 docs/level-format.md documents the schema, versioning/migration approach, and every edit operation
- [ ] #7 The entire core library builds and its test suite runs without Unity, Megabonk, or MelonLoader present, verified by running `task mod:test` in an environment with the game not running
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
