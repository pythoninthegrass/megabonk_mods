---
id: TASK-003
title: Level format and editing core
status: Done
assignee: []
created_date: '2026-10-06 21:40'
updated_date: '2026-10-07 21:50'
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
- [x] #1 A level file schema is implemented with round-trip serialize/deserialize tests and at least one documented migration path from schema version 1 to a hypothetical version 2
- [x] #2 All edit operation types (tile height/slope/add/remove, object place/move/remove) are implemented as pure data types with unit tests covering valid and invalid construction
- [x] #3 The edit stack supports apply, undo, and redo with tests covering multi-step sequences, undo-past-the-start, and redo-after-a-new-edit-invalidates-the-redo-stack
- [x] #4 The reachability validator correctly identifies unreachable tiles and spawn-to-boss-portal connectivity on hand-built test grids, including a deliberate cliff-between-chains case and a case fixed by a slope
- [x] #5 Catalog ID parsing validates the reserved namespaces (including bundle: for future use) and rejects malformed IDs, with unit tests
- [x] #6 docs/level-format.md documents the schema, versioning/migration approach, and every edit operation
- [x] #7 The entire core library builds and its test suite runs without Unity, Megabonk, or MelonLoader present, verified by running `task mod:test` in an environment with the game not running
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Work through the five subtasks in order (.01-.05), each with its own TDD plan recorded on the subtask. High-level approach:

- .01 Level file schema: level-root type + System.Text.Json + schemaVersion migration mechanism. Decide project layout here (see below).
- .02 Edit operation types: tile height/slope/add/remove + object place/move/remove, as pure data types referencing catalogId or genId.
- .03 Undo/redo stack over an in-memory level-state model built by replaying edits.
- .04 Reachability validator: BFS over the tile grid using the chain/slope rule (height diff 0, or 1 via a slope facing that direction).
- .05 Catalog ID parsing/validation, including the reserved `bundle:<pack>/<asset>` namespace for TASK-007.

Project layout decision (recorded here, detailed in docs/level-format.md): keep the Unity-free core in `src/MegabonkLevels.Mod` alongside the existing TASK-002 files (generation_report.cs, generation_hash.cs, placeholder_logic.cs), compile-linked into tests/MegabonkLevels.Tests per the pattern already proven there. A separate MegabonkLevels.Core project would duplicate the MSBuild plumbing (Directory.Build.props deploy target, MelonLoader/Il2Cpp HintPaths) for no isolation benefit, since the Unity-free boundary is already enforced by simply not referencing Unity/Il2Cpp types in these files — the existing compile-link into the net10.0 xunit project is itself proof the boundary holds.

Each subtask file naming follows existing convention: lowercase_snake_case.cs in src/MegabonkLevels.Mod, compile-linked by relative path into tests/MegabonkLevels.Tests.csproj.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All five subtasks complete: level file schema + migration (.01), typed edit operations (.02), undo/redo edit stack (.03), reachability validator (.04), catalogId parsing/validation (.05).

Verified: `task check` passes clean (net6.0 Mod build, 93/93 xunit tests on net10.0 with no Unity/Megabonk/MelonLoader present, tools tests, markdownlint, ruff). docs/level-format.md documents the schema, versioning/migration mechanism, all seven edit operation types, the undo/redo EditStack, the ReachabilityValidator's chain/slope rule, and the catalogId grammar.

The Unity-free core now provides the full "seed + edits" model TASK-004 (runtime playback) and TASK-005 (editor UI) build on.
<!-- SECTION:FINAL_SUMMARY:END -->
