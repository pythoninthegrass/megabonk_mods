---
id: TASK-019
title: Make the toolbar labels clickable in the editor
status: To Do
assignee: []
created_date: '2026-10-27T17:05:00Z'
labels:
  - editor
  - dev-harness
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
documentation:
  - docs/development.md
priority: low
type: enhancement
ordinal: 79000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The editor toolbar's tool labels (Raise, Lower, Slope, Remove, Place, Select) only show a hover hint; tools switch through the 1-9 hotkeys (`EditorTileTools.Tick`, `RefreshHint`). Clicking a label does nothing, which TASK-018.02 found when `click_widget("Tool:Place")` reported success and left the tool unchanged. Make a click on a label select that tool, then list the labels as `Tool:<tool>` widgets in `ui_tree` so `click_widget` can use them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Clicking a toolbar tool label with the mouse selects that tool, the same as its hotkey.
- [ ] #2 A click on a label does not also act on the terrain beneath the toolbar.
- [ ] #3 `ui_tree` lists each label as `Tool:<tool>` and `click_widget("Tool:Place")` changes `state.editorTool` to `Place`.
- [ ] #4 Verified in the real game through the MCP tools.
- [ ] #5 docs/development.md describes the clickable labels and the `Tool:<tool>` widget names; task check passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
