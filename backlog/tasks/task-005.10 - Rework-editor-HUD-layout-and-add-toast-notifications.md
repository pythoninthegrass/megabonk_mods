---
id: TASK-005.10
title: Rework editor HUD layout and add toast notifications
status: In Progress
assignee: []
created_date: '2026-10-23T16:06:00Z'
updated_date: '2026-10-23T16:07:00Z'
labels: []
dependencies: []
modified_files:
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/toast_stack.cs
parent_task_id: TASK-005
priority: medium
type: enhancement
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The editor's lefthand palette and top-center toolbar reserved more width than their content needed, and the save/load status text sat in leftover toolbar space where it overlapped the status line. The layout should fit its content, with the toolbar centered between the palette and the level list. Save/load feedback should be a transient toast under the toolbar. Failures (save, load, validate) currently show only as small text in the status band and are easy to miss; they are candidates for toasts in an error color. Toasts stack with the newest on top.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Palette column width fits its longest label, including the worst-case selected title line
- [x] #2 Top-center toolbar width fits its content instead of a fixed width
- [x] #3 Top-center toolbar is centered between the palette column and the level list
- [x] #4 Level list sits flush against the right screen edge
- [x] #5 Save and load success messages show as a toast directly under the toolbar
- [x] #6 A toast clears automatically after 3 seconds
- [x] #7 Clicking a toast dismisses it and the click does not reach the map underneath
- [x] #8 Save, load and validate failures show as toasts in a color distinct from success toasts
- [x] #9 Toasts stack with the newest on top
- [x] #10 docs/development.md describes the toolbar layout and toast behaviour
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
