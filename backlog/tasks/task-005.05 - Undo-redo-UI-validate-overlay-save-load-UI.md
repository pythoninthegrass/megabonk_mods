---
id: TASK-005.05
title: 'Undo/redo UI, validate overlay, save/load UI'
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
labels:
  - level-editor
dependencies:
  - TASK-005.03
  - TASK-005.04
parent_task_id: TASK-005
priority: high
type: feature
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement three UI pieces that complete the editing loop:

1. **Undo/redo**: buttons and keybinds (e.g. Ctrl+Z/Ctrl+Y) calling TASK-003.03's `EditStack.Undo()`/`Redo()`, with the result re-applied live (reuse TASK-004.02's apply logic for the inverse operations too — confirm the live-application layer can apply an "undo" the same way it applies a forward edit, or extend it if needed).
2. **Validate overlay**: a button that runs TASK-003.04's reachability validator against the current live level state and visually highlights (e.g. a colored overlay or outline) any tiles it reports as unreachable from spawn, and separately indicates whether the boss portal is currently reachable.
3. **Save/load UI**: a save dialog (filename input, writes a `.mblevel.json` via TASK-003.01's serializer, capturing the current `EditStack`'s full edit history) and a load dialog (lists existing level files from `UserData/Levels/`, loads one via TASK-004.01's loader).

These three are grouped into one subtask since they're each relatively small, UI-focused wrappers around machinery TASK-003/TASK-004 already built.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Undo/redo buttons and keybinds correctly revert/reapply the most recent edit, visible live in the 3D view
- [ ] #2 A validate action highlights every tile the reachability validator reports as unreachable from spawn, and separately reports boss-portal reachability
- [ ] #3 A save dialog writes the current edit history to a named .mblevel.json file in UserData/Levels/ via TASK-003.01's serializer
- [ ] #4 A load dialog lists existing level files in UserData/Levels/ and loads a selected one via TASK-004.01's loader
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
