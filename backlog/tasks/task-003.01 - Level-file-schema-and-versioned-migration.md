---
id: TASK-003.01
title: Level file schema and versioned migration
status: To Do
assignee: []
created_date: '2026-10-06 21:41'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-003
priority: high
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-003 first for full context, including the "seed + edits" rationale and the project layout decision this subtask must make.

Decide and document (in docs/level-format.md) whether the core library lives in `src/MegabonkLevels.Mod`'s non-Unity-dependent files (compile-linked into tests, per xeno_mods's pattern) or as a dedicated `src/MegabonkLevels.Core` project referenced by both the Mod project and the test project. Either is acceptable; pick based on which keeps the Unity-free boundary clearest, and note the reasoning.

Implement, using `System.Text.Json`:

- A level file root type: `schemaVersion` (int), `gameBuildId` (string — compared against the running game's build at load time by TASK-004, not used here), `map` (the `EMap` identifier), `stageIndex`, `tier`, `seed` (int), and `edits` (an ordered array — the op types themselves are TASK-003.02's job; this subtask can use a placeholder/minimal op shape and TASK-003.02 will flesh it out, or coordinate ordering with that task).
- A migration mechanism: given a JSON document with an older `schemaVersion`, transform it to the current version before deserializing into the current types. Write this so adding a "version 2" later is a matter of adding one migration step function, not rewriting the reader.
- Round-trip tests: serialize a level, deserialize it, assert equality. A test for loading a "version 1" fixture file through at least one migration step to prove the mechanism works (even if version 2 doesn't exist yet — write a synthetic test-only "next version" to exercise the migration path, documented as such).

TDD: write the failing round-trip test first, confirm it fails, then implement.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented decision exists (docs/level-format.md) on single-project vs Core-project layout for the Unity-free library, with reasoning
- [ ] #2 The level file root type includes schemaVersion, gameBuildId, map, stageIndex, tier, seed, and edits fields, serialized via System.Text.Json
- [ ] #3 A migration mechanism transforms an older-schemaVersion document to current types before use, demonstrated by a test migrating a synthetic older-version fixture
- [ ] #4 Round-trip serialize/deserialize tests pass for at least one representative level document
- [ ] #5 docs/level-format.md documents the schema fields and the migration approach
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
