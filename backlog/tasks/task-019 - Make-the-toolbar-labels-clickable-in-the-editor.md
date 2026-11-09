---
id: TASK-019
title: Make the toolbar labels clickable in the editor
status: Done
assignee:
  - claude
created_date: '2026-10-27T17:05:00Z'
updated_date: '2026-10-27T19:13:00Z'
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
- [x] #1 Clicking a toolbar tool label with the mouse selects that tool, the same as its hotkey.
- [x] #2 A click on a label does not also act on the terrain beneath the toolbar.
- [x] #3 `ui_tree` lists each label as `Tool:<tool>` and `click_widget("Tool:Place")` changes `state.editorTool` to `Place`.
- [x] #4 Verified in the real game through the MCP tools.
- [x] #5 docs/development.md describes the clickable labels and the `Tool:<tool>` widget names; task check passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Test first: EditorTools.WidgetName(tool) returns "Tool:<tool>" for every tool (tests/MegabonkLevels.Tests/editor_tool_tests.cs).
2. editor_tool.cs: add WidgetName.
3. editor_tile_tools.cs BuildToolbar: register a ClickRegion per tool slot named WidgetName(tool) with OnClick = SetTool(tool). Click regions already feed HandleOverlayInput (consumes the click; the terrain path is already skipped while the pointer is over the toolbar) and ListWidgets (so ui_tree lists them and click_widget finds them).
4. task mod:build, relaunch, verify in the live game through MCP: ui_tree lists Tool:*, click_widget("Tool:Place") sets state.editorTool, a real mouse click on a label does the same, and no edit lands on the terrain.
5. Docs: docs/development.md (clickable labels, Tool:<tool> names, correct the 'tools are not widgets' notes incl. the click_widget docstring in scripts/mcp_server.py). task check.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Each toolbar tool label is now a click region named Tool:<tool> (EditorTools.WidgetName), registered in BuildToolbar with OnClick = SetTool. HandleOverlayInput consumes the click and the terrain path is already skipped over the toolbar. Verified live through MCP after relaunch: ui_tree lists Tool:Raise..Tool:Select, click_widget("Tool:Place") set state.editorTool to Place, and a raw mouse click on the Raise label set it to Raise with edits.count still 0. Unit test for WidgetName added first; task check passes. docs/development.md and the click_widget docstring updated (an MCP server restart picks up the new docstring).
<!-- SECTION:FINAL_SUMMARY:END -->
