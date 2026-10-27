---
id: TASK-007.04
title: Pack manifest format and version check
status: Done
assignee: []
created_date: '2026-10-06 21:44'
updated_date: '2026-10-27 03:52'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.02
parent_task_id: TASK-007
priority: low
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context.

Define a pack manifest format at `UserData/LevelPacks/<packId>/manifest.json` and a pack-version compatibility check.

## Manifest

Fields: `id` (string, must equal the pack folder name and the `<pack>` segment of `bundle:<pack>/<asset>` catalogIds), `name` (string), `author` (string), `version` (string), `assets` (list of asset names the pack provides, matching the `<asset>` segment). Parsing and validation are Unity-free and unit-tested: malformed JSON, missing fields, and an `id` that differs from the folder name each produce a clear error.

## Asset validation

`PackCatalog` (`src/MegabonkLevels.Mod/pack_catalog.cs`) checks a referenced asset against the manifest `assets` list before any `AssetBundle.LoadAsset` call. An asset absent from the manifest resolves as `AssetMissing`, which keeps the existing `Missing:<id>` placeholder cube, logged warning, and editor toast.

## Level-side pack versions

Add an optional top-level `packs` map to the level schema, `{"<packId>": "<version>"}`, with a schema version bump and a migration in the existing versioned-migration path (see `docs/level-format.md`). The editor save fills `packs` from the installed manifests of the packs the level references.

## Version check

Compare the level's `packs[<packId>]` to the installed manifest `version` by exact string match, mirroring `GameBuildIdCheck.MismatchWarning` (`src/MegabonkLevels.Mod/game_build_id_check.cs`). A mismatch logs a warning and the run still starts; it never blocks or crashes. A level with no `packs` entry for a pack, or a pack with no recorded version, produces no warning.

## Scope for an unattended run

Keep the logic (manifest parse/validate, version check, migration) in Unity-free classes with xunit tests written first, in `tests/MegabonkLevels.Tests`. Unity-side wiring in `pack_prefabs.cs` is limited to reading `manifest.json`. In-game verification is out of scope for the run; Lance verifies with the harness afterwards. Do not edit `taskfile.yml`, `taskfiles/`, the test project configuration, or lint config.

Also correct `docs/level-format.md`, which still says nothing produces `bundle:` ids yet, and document the manifest format and the compatibility check there or in `docs/asset-bundles.md`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A manifest format (id, name, author, version, assets) is defined, parsed and validated in Unity-free code with unit tests for malformed JSON, missing fields, and id/folder-name mismatch
- [x] #2 PackCatalog resolves a bundle: asset absent from the pack manifest as AssetMissing before any AssetBundle.LoadAsset call, keeping the Missing:<id> placeholder, warning, and toast
- [x] #3 The level schema gains an optional top-level packs map with a version bump and a migration from the previous version, covered by tests
- [x] #4 Editor save writes packs from the installed manifests of the packs the level references
- [x] #5 A level whose packs[<packId>] differs from the installed manifest version (exact string match) logs a warning and still starts; absent entries or versions produce no warning; covered by tests
- [x] #6 docs/level-format.md and docs/asset-bundles.md document the manifest format, the packs map, and the compatibility check, and the stale 'nothing produces these ids yet' line is corrected
- [x] #7 The Unity-free tests (task mod:test), the mod build with -p:ModInstanceFolder redirected to a temp directory, task lint and task scripts:test all pass, with no edits to taskfile.yml, taskfiles/, the test project config beyond Compile Include lines, or lint config
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Unattended gnhf run. In-game verification is done by Lance afterwards: relaunch with a level referencing a test pack at matching and mismatching versions, confirm warnings in Latest.log and that a missing asset still spawns the placeholder.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Definition of Done item 'task check passes' cannot be run unattended because task check builds the mod and the csproj deploys into the live game's Mods folder. Satisfy it by running its parts: task mod:test, the dotnet build with -p:ModInstanceFolder redirected to an empty temp directory (trailing slash), task lint and task scripts:test. The in-game check (relaunch with a level referencing a test pack at matching and mismatching versions; warning in Latest.log; missing asset still spawns the placeholder) is an open item for a human; record it in the notes, do not claim it verified.

In-game verification is an open item for a human (the game cannot be run unattended): relaunch with a level referencing a test pack at matching and mismatching versions, confirm the pack-version warning in Latest.log, and confirm a missing asset still spawns the Missing:<id> placeholder. task check passes is intentionally not marked (item 1) because it builds the mod and deploys the DLL into the live game's Mods folder; it is satisfied here by its parts: task mod:test (844 tests pass), the dotnet build with -p:ModInstanceFolder redirected to a temp dir (fails only on pre-existing missing-game-assembly resolution — the game is not installed on this machine, baseline is identical), task lint, and task scripts:test.

Unity-side edits (pack_prefabs.cs, level_loader_patch.cs, editor_tile_tools.cs, live_edit_patch.cs) have not been compiled: the redirected mod build on the Mac fails with only missing-game-assembly errors (CS0246/CS0103), which hides semantic errors. Compile them on a machine with the game assemblies before merging.

Correction: with MEGABONK game folder pointed at the CrossOver bottle, the mod project builds with 0 errors (net6). That build found two errors the net10 tests could not: JsonNode.DeepClone and the CatalogId.TryParse overload; both are fixed.

In-game check on macOS (free Wine, branch DLL): level recording testpack 0.9.0 against manifest 1.0.0 logged the mismatch warning and still spawned bundle:testpack/TestProp; with the manifest assets set to [Other] and a matching version, no version warning and the bundle-held TestProp resolved to the Missing: placeholder with the 'asset not found in its pack' warning. Not checked in game: editor save writing the packs map (LiveEditPatch.BuildPacks), manifest id/folder rejection, v1 level migration.

In-game editor save (harness-injected text, Save button): a level holding one bundle:testpack/TestProp placement saved as schemaVersion 2 with packs {testpack: 1.0.0}, so LiveEditPatch.BuildPacks writes the installed manifest version. Real-keyboard typing and Backspace in the editor text fields did not work in this session under Wine (see docs/development.md 'Real keyboard text').
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Pack manifests (id, name, author, version, assets) are parsed and validated in Unity-free code, with the id required to match the pack folder. PackCatalog.Resolve filters a pack's assets by its manifest, so an unlisted asset spawns the Missing placeholder. Levels gain an optional packs map (schemaVersion 2, migration from 1, empty map when absent) that editor save fills from installed manifests, and GamePackVersionCheck warns on an exact-string version mismatch without blocking the run. Verified: task check green on main; in game (free Wine on macOS) a 0.9.0 level against a 1.0.0 manifest logged the warning and still spawned the asset, a manifest omitting TestProp produced the placeholder, and editor save wrote packs {testpack: 1.0.0}. An unattended gnhf run produced the first pass; review found the manifest filter unwired, no folder-id check, and two net6 compile errors the net10 tests could not see, all fixed before merge. Open: real-keyboard text input in the editor fields still fails under Wine in this setup; clicking the game window does not help.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
