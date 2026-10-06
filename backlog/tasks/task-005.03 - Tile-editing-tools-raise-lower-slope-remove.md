---
id: TASK-005.03
title: 'Tile editing tools (raise, lower, slope, remove)'
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
labels:
  - level-editor
dependencies:
  - TASK-005.01
parent_task_id: TASK-005
priority: high
type: feature
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement mouse-driven tile tools while in editor mode: raise, lower, rotate-slope, and remove, operating on the tile the player's cursor/raycast is over. Each tool action should construct the corresponding TASK-003.02 edit op (`SetTileHeight`, `SetTileSlope`, `RemoveTile`, `AddTile`) and push it through TASK-003.03's `EditStack`, then apply it live using TASK-004.02's live-application logic (reuse directly — do not reimplement tile mutation logic in UI code) so the change is immediately visible.

Include basic tool-mode UI (a toolbar or hotkeys to switch between raise/lower/slope/remove) and a visible cursor/highlight showing which tile is currently targeted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Raise, lower, slope-rotate, and remove tools are selectable and operate on the tile under the player's cursor via raycast
- [ ] #2 Each tool action constructs the correct TASK-003.02 edit op and applies it through TASK-003.03's EditStack and TASK-004.02's live-application logic
- [ ] #3 Changes are immediately visible in the 3D view when a tool is used
- [ ] #4 A visible highlight indicates which tile is currently targeted before an action is taken
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
