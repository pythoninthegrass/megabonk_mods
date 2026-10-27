---
id: TASK-018.02
title: Target editor widgets without guessing screenshot pixel coordinates
status: Done
assignee:
  - Claude
created_date: '2026-10-27T07:23:00Z'
updated_date: '2026-10-27T17:00:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
documentation:
  - docs/development.md
modified_files:
  - src/MegabonkLevels.Mod/ui_widgets.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_ui.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_palette.cs
  - scripts/run.py
  - scripts/mcp_server.py
  - docs/development.md
  - tests/MegabonkLevels.Tests/ui_widgets_tests.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/test_run.py
  - tests/test_mcp_server.py
parent_task_id: TASK-018
priority: medium
type: enhancement
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every `mouse` interaction needs guessed screenshot pixel coordinates. During TASK-016 AC#4, a click meant for the Save toolbar hit the terrain instead, repeatedly, because the toolbar sits in the top ~150px and the mod already knows its own widget geometry. Add a way to target widgets by name so an agent can click the Save button, Undo, or a palette entry without coordinate math, and a way to query what a pixel is over. Mod-side; verify in the real game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A `click_widget(name)` tool clicks a named editor widget (Save, Undo, a palette entry) without pixel coordinates.
- [x] #2 A `ui_tree`/`element_at` tool reports which widget a pixel is over, or lists the editor widgets and their rects.
- [x] #3 Verified in the real game: click Save by name and confirm the save status changes.
- [x] #4 docs/development.md documents the new tools; task check passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Pure logic (tests first): `UiWidget` record (Name, X, Y, Width, Height in screenshot pixels, top-left origin) with `Centre`, and `UiWidgets.At(widgets, x, y)` / `UiWidgets.Find(widgets, name)` (case-insensitive, error lists known names on a miss).
2. Harness commands (tests first): `click-widget` (required `name`) and `ui-tree` (optional `x`,`y` both or neither) in harness_command.cs.
3. Mod side: give `ClickRegion` a name; register tool slots, load rows, toasts, palette slots/tabs/pager/chevron/search with names (`Tool:Raise`, `Save`, `Undo`, `Palette:<entry id>`, `Tab:<label>`...). `EditorTileTools`/`EditorPalette` expose active widget rects converted from RectTransform world corners to screenshot space. dev_harness: `ui-tree` returns widgets (plus `at` when x,y given); `click-widget` queues the existing mouse move + click at the widget centre, so the click goes through the normal overlay input path.
4. Python: run.py builders + CLI verbs (`ui-tree [X Y]`, `click-widget NAME`), MCP tools `ui_tree(x=None,y=None)` and `click_widget(name)`; tests in tests/test_run.py and tests/test_mcp_server.py.
5. Docs: docs/development.md command table and MCP section.
6. Verify in the real game: relaunch, `ui_tree`, `click_widget("Save")`, confirm `state.edits.saveStatus` changes. `task check` passes.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `ui-tree` and `click-widget` harness commands, `run.py` verbs and MCP tools `ui_tree(x?, y?)` and `click_widget(name)`. Widgets are named (`Tool:Raise`, `Save`, `Undo`, `Palette:<id>`, `Tab:<label>`, ...) and their rects reported in screenshot pixels; `click-widget` queues a normal mouse move and click at the widget centre. Unit tests (UiWidgets geometry and lookup, command parsing, Python builders and MCP payloads) written first. Verified in the real game: `ui-tree` listed 70+ widgets, `ui-tree 833 86` reported `SaveInput`, and `click-widget Save` changed `state.edits` from `saveStatus:none` to `saved` with `lastSavedName:level.mblevel.json`. An unknown name returns the list of known names. `task check` passes. Disabled buttons (Undo/Redo with nothing to undo) and off-page palette entries are not listed; documented in docs/development.md. The MCP server process must be restarted to pick up the new tools.
<!-- SECTION:FINAL_SUMMARY:END -->
