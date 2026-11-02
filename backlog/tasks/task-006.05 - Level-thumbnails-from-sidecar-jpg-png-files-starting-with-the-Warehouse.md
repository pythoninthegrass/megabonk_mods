---
id: TASK-006.05
title: 'Level thumbnails from sidecar jpg/png files, starting with the Warehouse'
status: To Do
assignee: []
created_date: '2026-11-02T04:51:00Z'
labels: []
dependencies: []
parent_task_id: TASK-006
priority: medium
type: feature
ordinal: 141000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Custom Map Selection entries show a flat purple placeholder thumbnail today: MapSelectionPatch clones mapEntryPrefab, calls MapEntry.Set with the base MapData, and sets the placeholder after overwriting name and description. When the editor ships to players, installed levels are loose data files, so a level's cover image has to ship as data too — the same model as runtime music (TASK-024): files discovered at startup from UserData with safe lookup rules, referenced by filename, nothing baked into the mod. Read a jpg/png sidecar named after the level file (same base name, next to the .mblevel.json in UserData/Levels) and show it as the entry's thumbnail. The Warehouse ships as the first consumer, and every future distributed level gets the mechanism for free; the level browser (this parent task) can reuse the same image later.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A level with a jpg/png sidecar (same base name as its .mblevel.json, in UserData/Levels) shows that image as its Map Selection thumbnail instead of the purple placeholder
- [ ] #2 Discovery follows the mp3 runtime-catalog rules: case-insensitive extension matching, no path separators or traversal, and invalid or oversized files warn and fall back to the placeholder without breaking the entry
- [ ] #3 A missing sidecar changes nothing: entries without an image look and behave exactly as today
- [ ] #4 The Warehouse ships with a real thumbnail captured from the level, and its Map Selection entry shows it
- [ ] #5 Sidecar naming, supported formats and size limits are documented in docs/level-format.md next to the music reference
- [ ] #6 Verified in game with a harness screenshot: the Warehouse entry on the Map Selection screen displays the image
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
