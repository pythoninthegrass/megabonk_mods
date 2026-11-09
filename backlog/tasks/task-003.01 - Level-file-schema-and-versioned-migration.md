---
id: TASK-003.01
title: Level file schema and versioned migration
status: Done
assignee: []
created_date: '2026-10-06 21:41'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-003
priority: high
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
- [x] #1 A documented decision exists (docs/level-format.md) on single-project vs Core-project layout for the Unity-free library, with reasoning
- [x] #2 The level file root type includes schemaVersion, gameBuildId, map, stageIndex, tier, seed, and edits fields, serialized via System.Text.Json
- [x] #3 A migration mechanism transforms an older-schemaVersion document to current types before use, demonstrated by a test migrating a synthetic older-version fixture
- [x] #4 Round-trip serialize/deserialize tests pass for at least one representative level document
- [x] #5 docs/level-format.md documents the schema fields and the migration approach
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Layout decision confirmed with the maintainer: single-project (src/MegabonkLevels.Mod, compile-linked into tests/MegabonkLevels.Tests), matching the existing TASK-002 pattern. No MegabonkLevels.Core project.

Files to add (lowercase_snake_case.cs, per existing convention):
- level_file.cs: LevelFile root record (schemaVersion, gameBuildId, map, stageIndex, tier, seed, edits), an EMap enum mirroring the game's EMap flags (None=0, Forest=1, Desert=2, Hell=4, Graveyard=8, confirmed via .tools/il2cpp_dump/dump.cs), and a minimal placeholder EditOp record (TASK-003.02 replaces this with the real typed set).
- level_file_migration.cs: migration mechanism — read raw JSON, branch on schemaVersion, apply ordered migration steps up to current version, then deserialize into LevelFile. Includes one synthetic test-only "v2" migration step/type to prove the mechanism (documented as synthetic, not a real future schema).
- level_file_serialization.cs (or fold into level_file.cs if small): System.Text.Json read/write helpers.

Tests (tests/MegabonkLevels.Tests/level_file_tests.cs), TDD order:
1. Round-trip test: construct a LevelFile, serialize, deserialize, assert equality (write first, confirm fails pre-implementation).
2. Migration test: synthetic v1 JSON fixture -> migrate -> current-version LevelFile, assert fields carried over correctly.

Wire new files into tests/MegabonkLevels.Tests.csproj Compile Include/Link list alongside the existing three.

docs/level-format.md: new doc covering the schema fields, the project-layout decision + reasoning, and the migration approach. (Edit-operation docs land in TASK-003.02.)

seed field note: per docs/map-generation-determinism.md, this is the Tiles-map debugSeed (not MapGenerationController.mapSeed, which is disconnected from generation) — document this explicitly so TASK-004 doesn't wire the wrong field.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Record struct, not record class: LevelFile is compiled into both the net10.0 xunit project and the net6.0 Mod project (Nullable disable, Il2Cpp NullableAttribute ctor is broken). A record **class**'s compiler-synthesized `Equals(T? other)` needs nullable-attribute metadata even under `disable` and fails with CS0656; `readonly record struct` sidesteps this since struct equality takes the type non-nullably. Discovered by running `task mod:build` after the xunit tests passed — don't assume xunit-green means the Mod project also builds when touching shared compile-linked files.

JsonNamingPolicy.CamelCase applied consistently in LevelFileSerializer: without it, Serialize() emits PascalCase keys (`SchemaVersion`) but SchemaMigrator/DeserializeWithMigration reads lowercase `schemaVersion` off the raw JsonObject, so the two must agree.

Edits uses IReadOnlyList<EditOp> with manual Equals/GetHashCode (SequenceEqual) since record-struct default equality compares the list reference, which differs after a deserialize produces a new List instance.

EditOp is a minimal placeholder shape (OpType/Target/Payload as strings) per the subtask description; TASK-003.02 replaces it with the real typed operation set without needing to touch the root schema or migration mechanism.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the level file root schema and schemaVersion migration mechanism as a Unity-free library in `src/MegabonkLevels.Mod`, compile-linked into `tests/MegabonkLevels.Tests` (confirmed with the maintainer: single-project layout, not a separate Core project — matches the existing TASK-002 compile-link pattern).

Added:
- `level_file.cs`: `EMap` (value mirror of the game's `EMap` flags enum), `EditOp` placeholder record struct, and `LevelFile` (schemaVersion, gameBuildId, map, stageIndex, tier, seed, edits) as a `readonly record struct` with hand-written `Equals`/`GetHashCode` (sequence-compares `Edits`).
- `level_file_migration.cs`: `SchemaMigrator.Migrate` — generic, registry-driven schemaVersion -> schemaVersion+1 step loop over `JsonObject`, throws if a step is missing for the document's current version.
- `level_file_serialization.cs`: `LevelFileSerializer` (`Serialize`/`Deserialize`/`DeserializeWithMigration`) using `System.Text.Json` with `JsonNamingPolicy.CamelCase`; production migration-steps registry is currently empty (schema version 1 is the only version that has shipped).
- `docs/level-format.md`: schema field reference, the project-layout decision and reasoning (including the record-struct-vs-record-class Nullable-disable gotcha), and the migration approach.
- `tests/MegabonkLevels.Tests/level_file_tests.cs`: round-trip test, a no-op-migration-at-current-version test, and two tests exercising `SchemaMigrator` directly with a synthetic test-local step (documented in both the test and the doc as synthetic — no real schema version 2 exists).

TDD: wrote `level_file_tests.cs` and wired it into the csproj first, confirmed `dotnet test` failed with CS2001 (missing source files), then implemented until green.

Verification: `task check` (build + `dotnet test` for both the Mod and Tests projects + lint) passes clean, 12/12 tests green. `task mod:build` (net6.0, MelonLoader/Il2Cpp references, Nullable disabled) also verified separately since it initially failed (CS0656) until `LevelFile` became a `record struct`.

No regressions to existing TASK-002 files; no Unity/Il2Cpp/MelonLoader types referenced anywhere in the new files.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
