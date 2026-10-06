---
id: TASK-006.01
title: In-game level browser UI
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-006
priority: medium
type: feature
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-006 first for full context.

Build a standalone level browser UI (UGUI+TMP, consistent with TASK-005's editor styling) listing every `.mblevel.json` file in `UserData/Levels/`, showing at minimum: title/filename, map, and a `gameBuildId` mismatch warning (reusing TASK-004.01's build-ID comparison logic) when a level was saved against a different game build than the one currently running. Make it accessible both from within the editor (extending TASK-005.05's basic save/load dialog) and from a standalone entry point usable without first entering editor mode (e.g. a button on the main menu or map-selection screen), so a player who only wants to play other people's levels never has to touch the editor.

Selecting a level loads and starts it via TASK-004.01's loader.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The browser lists every .mblevel.json in UserData/Levels/ with title/filename, map, and a gameBuildId-mismatch warning where applicable
- [ ] #2 The browser is reachable from a standalone entry point (e.g. main menu or map selection) without requiring editor mode to be entered first
- [ ] #3 Selecting a level loads and starts it via TASK-004.01's existing loader
- [ ] #4 The browser UI is visually consistent with TASK-005's editor UI styling
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
