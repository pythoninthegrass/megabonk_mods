---
id: TASK-007.02
title: 'Pack loader and bundle: catalog ID resolution'
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.01
parent_task_id: TASK-007
priority: low
type: feature
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context.

Implement a pack loader that discovers and loads AssetBundles from `UserData/LevelPacks/<pack>/` at game startup or on demand, extending TASK-003.05's `catalogId` parsing (which already reserves the `bundle:<pack>/<asset>` namespace) to resolve a `bundle:` ID to an asset inside a loaded pack's AssetBundle. Wire this into TASK-004.02's existing `catalogId` resolution logic (the same code path that resolves game-asset IDs against `DataManager.Instance`) so `PlaceObject` edits referencing `bundle:` IDs work through the exact same mechanism as built-in game assets, with no special-casing needed elsewhere in the edit-application pipeline.

Handle the failure case explicitly: a level referencing a `bundle:` asset from a pack the player doesn't have installed should produce a clear, non-crashing error (e.g. a placeholder object + a logged/visible warning), not a silent failure or a crash.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AssetBundles are discovered and loaded from UserData/LevelPacks/<pack>/
- [ ] #2 A bundle: catalogId resolves to the correct asset inside its pack's loaded AssetBundle
- [ ] #3 TASK-004.02's existing catalogId resolution path handles bundle: IDs through the same code path as game-asset IDs, without special-casing elsewhere in edit application
- [ ] #4 A level referencing a bundle: asset from a pack that isn't installed produces a clear warning and a placeholder rather than crashing or silently failing
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
