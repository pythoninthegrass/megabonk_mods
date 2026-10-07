---
id: TASK-003.05
title: Catalog ID parsing and validation
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:41'
updated_date: '2026-10-07 21:24'
labels:
  - level-editor
dependencies:
  - TASK-003.01
parent_task_id: TASK-003
priority: medium
type: feature
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-003 first for full context.

Define and implement the `catalogId` format used by `PlaceObject` edits (TASK-003.02) to reference placeable prefabs, plus parsing/validation:

- Game-asset namespace: stable string keys identifying existing game prefabs, e.g. `forest/stage0/randomMapObjects/2/Tree_03` or `interactable/chest` — the exact structure should be driven by however TASK-002's findings describe the game's prefab catalog being organized (`DataManager.Instance.maps → stages → randomMapObjects[].prefabs`, `stageTilePrefabs`, `MapData.shrines`, `SpawnInteractables`'s chest/rail fields) — read TASK-002's docs before finalizing the exact segments.
- Reserved future namespace: `bundle:<pack>/<asset>` for TASK-007's custom asset packs. Nothing produces these IDs yet, but parsing/validation must accept the format now so TASK-007 doesn't need to revisit this task's validation logic later.
- A parser that splits a raw string into a typed representation (namespace + segments) and a validator that rejects malformed IDs (empty segments, invalid characters, unknown namespace prefix, etc. — define the exact character/segment rules and document them).

TDD: write tests for valid game-asset IDs, valid reserved `bundle:` IDs, and a table of malformed inputs (empty string, missing namespace, invalid characters, trailing/leading separators) each expected to fail validation with a clear reason.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The catalogId format is defined and documented in docs/level-format.md, covering both the game-asset namespace and the reserved bundle: namespace
- [x] #2 A parser converts a raw catalogId string into a typed representation distinguishing namespace and segments
- [x] #3 A validator accepts well-formed game-asset and bundle: IDs and rejects a documented set of malformed inputs, each with a clear validation failure reason
- [x] #4 Unit tests cover valid IDs in both namespaces and a table-driven set of malformed inputs
- [x] #5 The game-asset ID structure is cross-checked against TASK-002's documented prefab catalog organization rather than invented independently
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
Research (via TASK-002 docs/dump cross-check, see notes) confirms the prefab catalog's actual shape:
- `DataManager.Instance.maps[]` (`MapData`) -> `stages[]` (`StageData`) -> `randomMapObjects[]` (`RandomMapObject`) -> `.prefabs[]` (`GameObject[]`, no name field)
- `StageData.stageTilePrefabs` (`StageTilePrefabs`): `flatTilePrefabs[]`, `mapSpecificTilesPrefabs[]` (both `GameObject[]`, no name field)
- `MapData.shrines[]` (`GameObject[]`, map-scoped, not stage-scoped, not on SpawnInteractables)
- `SpawnInteractables`: singular `chest`/`chestFree` fields (not arrays) plus `rails[]` (`GameObject[]`)
- No field anywhere exposes a human-readable prefab name string (confirmed via dump.cs + grep) — the task description's `Tree_03`-style example is illustrative, not sourced. catalogId segments for game-asset entries must therefore be allowed to be numeric indices, not just names.

Design (purely syntactic parser/validator — does not enforce which map/category names are real; that's TASK-004/005's catalog-building concern):

`CatalogId` (`src/MegabonkLevels.Mod/catalog_id.cs`), a `readonly record struct` with `Namespace` (`CatalogNamespace.GameAsset | Bundle`) and `Segments` (`IReadOnlyList<string>`, manual Equals/GetHashCode like LevelFile.Edits since list equality is reference-based by default).

Grammar:
- `bundle:<pack>/<asset...>` -> Bundle namespace, parsed by stripping the `bundle:` prefix then splitting the remainder on `/` (>=2 segments: pack + at least one asset segment).
- any other string containing `:` -> rejected, "unknown namespace prefix" (colon reserved for `bundle:`).
- anything else -> GameAsset namespace, split on `/` (>=2 segments), documented recommended shapes in docs/level-format.md: `{map}/stage{N}/randomMapObjects/{objectIndex}/{prefabIndex}`, `{map}/stage{N}/stageTilePrefabs/flat|specific/{index}`, `{map}/shrines/{index}`, `interactable/chest`, `interactable/chestFree`, `interactable/rail/{index}`.
- Segment charset: `^[A-Za-z0-9_-]+$`, non-empty (catches leading/trailing/doubled `/`).
- `CatalogId.TryParse`/`Parse` (throws `ArgumentException` with a clear reason per EditOpValidation convention) and `Serialize()` (round-trip back to string).

Wire into `edit_operations.cs`: replace `EditOpValidation.RequireNonBlankCatalogId`'s placeholder non-blank-only check with `CatalogId.Parse(catalogId)` (keep `PlaceObject.CatalogId` as a `string` field — no schema/JSON shape change, just stricter construction-time validation).

TDD: tests/MegabonkLevels.Tests/catalog_id_tests.cs first (valid game-asset ids incl. the documented shapes, valid bundle: ids, table-driven malformed inputs: empty, whitespace, missing namespace content, unknown prefix, invalid chars, leading/trailing/doubled slash, too-few-segments), then implement. Add a PlaceObject test confirming a malformed catalogId now throws via the real validator (replacing reliance on the placeholder).

Docs: update docs/level-format.md's "Validation convention" section (currently says catalogId check is a placeholder) with the real format, both namespaces, and the recommended game-asset segment shapes, citing this cross-check against TASK-002's confirmed catalog structure and noting prefabs have no name field (indices only).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Research agent cross-check (a90e8dd8397be8641) confirmed via dump.cs + docs grep: GameObject[] prefab arrays (RandomMapObject.prefabs, StageTilePrefabs.flatTilePrefabs/mapSpecificTilesPrefabs, MapData.shrines, SpawnInteractables.rails) have no name field anywhere in the game's data -- only array indices. The task description's 'Tree_03' example is illustrative, not a real field. Game-asset catalogId segment shapes documented in docs/level-format.md reflect this: final segment is numeric, not a descriptive name.

Updated 3 pre-existing test fixtures (edit_operations_tests.cs, edit_stack_tests.cs) that used a colon-style placeholder catalogId ('prefab:rock_small') which is now invalid under the real grammar (colon reserved for 'bundle:') -- changed to 'props/rock_small'. Added MalformedCatalogId_Throws to PlaceObjectTests to prove the real validator (not just the old non-blank check) is wired in.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Defined and implemented the `catalogId` format used by `PlaceObject` edits.

Added `src/MegabonkLevels.Mod/catalog_id.cs`: `CatalogId`, a `readonly record struct` (`Namespace`, `Segments`) with `Parse`/`TryParse`/`Serialize`. Two namespaces:
- `GameAsset` (default, no prefix): `segment/segment{/segment...}`, >= 2 segments.
- `Bundle` (reserved for TASK-007's custom asset packs): `bundle:segment/segment{/segment...}`, >= 2 segments after the prefix.

Segment charset `^[A-Za-z0-9_-]+$`, non-empty (catches leading/trailing/doubled `/`); `:` is reserved exclusively for the `bundle:` prefix, so any other colon is rejected as an unknown namespace prefix. Each failure mode returns a specific, human-readable reason via `ArgumentException`.

Game-asset segment shapes are cross-checked against TASK-002's confirmed catalog organization (not invented): `{map}/stage{N}/randomMapObjects/{objectIndex}/{prefabIndex}`, `{map}/stage{N}/stageTilePrefabs/flat|specific/{index}`, `{map}/shrines/{index}`, `interactable/chest`, `interactable/chestFree`, `interactable/rail/{index}` — all documented in docs/level-format.md along with the confirmed finding that the game's prefab arrays (`GameObject[]`) have no name field, only indices.

Wired into `edit_operations.cs`: `EditOpValidation.RequireNonBlankCatalogId` now calls `CatalogId.Parse` instead of a non-blank-only placeholder check. `PlaceObject.CatalogId` stays a plain `string` — no schema/JSON shape change.

Tests: `tests/MegabonkLevels.Tests/catalog_id_tests.cs` (new, written first) covers valid ids in both namespaces (including every documented game-asset shape), round-trip via `Serialize`, equality, and a table-driven set of malformed inputs (empty/whitespace, unknown namespace prefix, empty segment, invalid characters, too-few-segments) each asserted against its specific failure reason. Updated 3 pre-existing test fixtures that used an now-invalid colon-style placeholder catalogId (`prefab:rock_small` → `props/rock_small`), and added `PlaceObjectTests.MalformedCatalogId_Throws`.

Verification: `task check` passes clean — net6.0 Mod build, 93/93 xunit tests (net10.0), tools tests, markdownlint, ruff. No regressions to existing op types or `EditStack`.
<!-- SECTION:FINAL_SUMMARY:END -->
