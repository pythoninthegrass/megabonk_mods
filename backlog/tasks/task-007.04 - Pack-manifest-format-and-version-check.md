---
id: TASK-007.04
title: Pack manifest format and version check
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
updated_date: '2026-10-27 00:42'
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
- [ ] #1 A manifest format (id, name, author, version, assets) is defined, parsed and validated in Unity-free code with unit tests for malformed JSON, missing fields, and id/folder-name mismatch
- [ ] #2 PackCatalog resolves a bundle: asset absent from the pack manifest as AssetMissing before any AssetBundle.LoadAsset call, keeping the Missing:<id> placeholder, warning, and toast
- [ ] #3 The level schema gains an optional top-level packs map with a version bump and a migration from the previous version, covered by tests
- [ ] #4 Editor save writes packs from the installed manifests of the packs the level references
- [ ] #5 A level whose packs[<packId>] differs from the installed manifest version (exact string match) logs a warning and still starts; absent entries or versions produce no warning; covered by tests
- [ ] #6 docs/level-format.md and docs/asset-bundles.md document the manifest format, the packs map, and the compatibility check, and the stale 'nothing produces these ids yet' line is corrected
- [ ] #7 The Unity-free tests (task mod:test), the mod build with -p:ModInstanceFolder redirected to a temp directory, task lint and task scripts:test all pass, with no edits to taskfile.yml, taskfiles/, the test project config beyond Compile Include lines, or lint config
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Unattended gnhf run. In-game verification is done by Lance afterwards: relaunch with a level referencing a test pack at matching and mismatching versions, confirm warnings in Latest.log and that a missing asset still spawns the placeholder.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Definition of Done item 'task check passes' cannot be run unattended because task check builds the mod and the csproj deploys into the live game's Mods folder. Satisfy it by running its parts: task mod:test, the dotnet build with -p:ModInstanceFolder redirected to an empty temp directory (trailing slash), task lint and task scripts:test. The in-game check (relaunch with a level referencing a test pack at matching and mismatching versions; warning in Latest.log; missing asset still spawns the placeholder) is an open item for a human; record it in the notes, do not claim it verified.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
