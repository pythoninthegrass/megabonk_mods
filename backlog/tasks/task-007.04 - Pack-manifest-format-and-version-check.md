---
id: TASK-007.04
title: Pack manifest format and version check
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.02
parent_task_id: TASK-007
priority: low
type: feature
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context.

Define a pack manifest format (e.g. `UserData/LevelPacks/<pack>/manifest.json`) covering: pack identity (a stable pack ID matching the `bundle:<pack>/...` catalogId namespace), a human-readable name/author, a pack version, and the list of assets the pack provides (so the pack loader from TASK-007.02 can validate a level's referenced `bundle:` assets actually exist in the installed pack before attempting to load them, producing a clearer error than a failed `AssetBundle.LoadAsset` call).

Implement a basic compatibility check analogous to the level file's `gameBuildId` check (TASK-003.01/TASK-004.01): if a level references a pack version the installed pack does't match, surface a clear warning rather than a silent failure or crash.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A pack manifest format is defined and documented, covering pack ID, name/author, version, and provided asset list
- [ ] #2 The pack loader validates a level's referenced bundle: assets against the installed pack's manifest before attempting to load, with a clear error for a missing asset
- [ ] #3 A pack-version mismatch between a level's expectations and the installed pack produces a clear warning, analogous to the gameBuildId check
- [ ] #4 The manifest format and compatibility check are documented alongside the level-format docs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
