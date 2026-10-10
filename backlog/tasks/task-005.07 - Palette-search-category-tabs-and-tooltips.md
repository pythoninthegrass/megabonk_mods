---
id: TASK-005.07
title: 'Palette search, category tabs and tooltips'
status: To Do
assignee: []
created_date: '2026-10-10 06:23'
updated_date: '2026-10-10 06:33'
labels:
  - level-editor
dependencies:
  - TASK-005.02
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/palette_catalog_builder.cs
parent_task_id: TASK-005
priority: medium
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 and the "Catalog palette" section of docs/development.md first.

TASK-005.02 gives the editor a scrolling text list of every placeable prefab for the current map, grouped by stage and category (`PaletteCatalogBuilder`). For a large catalog that is slow to browse. Lance pointed at the Minecraft "Better Creative Mode" mod as the model: a text search box that filters entries live, category tabs, and a hover tooltip that shows the item name and its id.

Whether this pays off depends on catalog size. Before starting, read `EditorPalette: built <n> entries for <map>` in `MelonLoader/Latest.log` for a few maps and record the counts in the task notes. If they are small (a few dozen), say so and ask Lance whether to proceed.

Constraints carried over from the palette:
- Input is read from Unity's `Input` directly, not through a UGUI `EventSystem`, so the game's Rewired input module stays untouched. Text entry has to follow the same rule (`Input.inputString` is available).
- Editor mode binds W/A/S/D/Space/Left Ctrl/Left Shift to the free-fly camera and the digit keys to tile tools (TASK-005.03). While the search box has focus those keys must type, not fly or switch tools.
- The palette is rebuilt on each editor entry; the filter state may reset then.

Thumbnails and an icon grid are a separate task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A search box in the palette filters entries by display name and catalogId as the user types, case-insensitively
- [ ] #2 While the search box has focus, typed keys do not move the camera or switch editor tools; Esc or a click outside the box ends focus
- [ ] #3 Category tabs (or equivalent toggles) built from the existing stage/category groups restrict the list to one group, with an All option
- [ ] #4 Hovering an entry shows a tooltip with its display name and catalogId
- [ ] #5 Selection still works on filtered results, and a selection hidden by a filter stays selected
- [ ] #6 Pure filtering and focus logic is unit tested; docs/development.md Catalog palette section is updated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: Forest (seed 20261007) palette logged `EditorPalette: built 75 entries for Forest`. Other maps not measured yet.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
