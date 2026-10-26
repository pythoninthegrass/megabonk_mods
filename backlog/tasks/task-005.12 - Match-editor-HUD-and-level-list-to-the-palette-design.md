---
id: TASK-005.12
title: Match editor HUD and level list to the palette design
status: Done
assignee: []
created_date: '2026-10-26T21:34:00Z'
updated_date: '2026-10-26T21:51:00Z'
labels: []
dependencies: []
parent_task_id: TASK-005
priority: medium
type: enhancement
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The palette now uses a bordered gray panel with bordered controls and a paged grid, but the middle toolbar HUD and the levels/UserData list on the right still use the old flat black look. The list is also about 140 px taller than the toolbar and moves the selection one file per wheel notch, so it does not scroll like the palette. The toolbar's per-tool hint line costs about 28 px of height and fits better as a cursor tooltip.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Toolbar panel, its buttons and the save-name input use the palette's border and fill colours and bordered controls
- [x] #2 Toolbar shows only the tool row, action row and status; hovering a tool shows a palette-style tooltip under the toolbar with a static description of that tool
- [x] #3 All editor tooltips (toolbar and palette) appear after 3 seconds of hovering, and moving to another tooltip item within 2 seconds of one being visible shows it at once
- [x] #4 Level list panel uses the same styling and is the toolbar's height, top-aligned with it
- [x] #5 Level list shows 4 files per page with a '< n/N >' pager in the title row that pages back and forth
- [x] #6 Mouse wheel over the list moves one page per notch and stops at the first and last page, as in the palette
- [x] #7 Clicking a row selects that file and fills the save-name form; the selected row is highlighted and the hovered row is tinted
- [x] #8 After Save, the list shows the page holding the saved file
- [x] #9 Unit tests cover the tool label, tool descriptions, hover delay and grace, and the row-to-index mapping, and the test suite passes
- [x] #10 docs/development.md describes the tool tooltip, the shared tooltip timing and the paged level list
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
1. Move palette colours, Bordered and PlaceTopLeft into EditorUi; extract EditorTooltip from the palette.
2. TDD: ToolbarText loses the detail line, EditorTools gains ToolLabel and Description, PalettePager gains IndexAt, HoverDelay added; remove unused EditorOverlayModel list helpers.
3. Toolbar: bordered panel and controls, ToolbarHeight 116, per-tool hover slots with static descriptions shown after a shared 3 s delay with a 2 s grace.
4. Level list: bordered panel at toolbar height, 4 rows, title-row pager, wheel pages via PalettePager.Step, click rows via IndexAt, page follows saved file.
5. Docs in docs/development.md; verify in the running game through the megabonk MCP.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified in the running game: restyled panels, tool hover tooltip under the toolbar, 4-row list with 2/2 paging via the > button, row click filling the save name, save landing on the saved file's page. Wheel paging and the < button were not driven (no wheel action in the harness); both use PalettePager.Step, which has unit tests. Tool hint wording changed from live target info to static descriptions at Lance's direction; EditorTools.TileDetail/PlaceDetail/SelectDetail and EditorObjectTools.Detail are now unused but left in place.

The 3 second tooltip delay is unit-tested (HoverDelay) and the tooltip was confirmed absent right after hovering, but the harness pointer injection lasts only a few frames, so the tooltip appearing after 3 s was not observed in the running game.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The toolbar and the levels/UserData list now share the palette's gray bordered style through EditorUi, and the tooltip box is shared through EditorTooltip. The toolbar's hint line became per-tool tooltips (static descriptions), which cut the toolbar to 116 px; the level list matches that height and pages 4 files at a time with a title-row pager and one-page-per-notch wheel scrolling through PalettePager. Every tooltip (toolbar and palette) appears after a 3 s hover, and moving between tooltip items within 2 s of one being visible shows the next at once. Verified with task check (793 .NET and 185 Python tests passing) and in the running game: styling, 2/2 paging via the next button, row click filling the save name, and save landing on the saved file's page. Not observed in game because the harness pointer injection lasts only a few frames: the tooltip appearing after 3 s, the grace behaviour, wheel paging and the previous-page button; these rely on unit-tested HoverDelay and PalettePager logic. Live target info (target (x,z), place at (x,z)) no longer shows anywhere; EditorTools.TileDetail/PlaceDetail/SelectDetail and EditorObjectTools.Detail are unused and left in place.
<!-- SECTION:FINAL_SUMMARY:END -->
