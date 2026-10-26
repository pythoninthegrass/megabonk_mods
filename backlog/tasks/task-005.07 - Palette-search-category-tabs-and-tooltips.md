---
id: TASK-005.07
title: 'Palette search, category tabs and tooltips'
status: Done
assignee:
  - OpenCode
created_date: '2026-10-10 06:23'
updated_date: '2026-10-26T18:30:00Z'
labels:
  - level-editor
dependencies:
  - TASK-005.02
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/palette_catalog_builder.cs
modified_files:
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/palette_filter.cs
  - src/MegabonkLevels.Mod/palette_search_input.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_mode.cs
  - tests/MegabonkLevels.Tests/palette_filter_tests.cs
  - tests/MegabonkLevels.Tests/palette_search_input_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - docs/development.md
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
- [x] #1 A search box in the palette filters entries by display name and catalogId as the user types, case-insensitively
- [x] #2 While the search box has focus, typed keys do not move the camera or switch editor tools; Esc or a click outside the box ends focus
- [x] #3 Category tabs (or equivalent toggles) built from the existing stage/category groups restrict the list to one group, with an All option
- [x] #4 Hovering an entry shows a tooltip with its display name and catalogId
- [x] #5 Selection still works on filtered results, and a selection hidden by a filter stays selected
- [x] #6 Pure filtering and focus logic is unit tested; docs/development.md Catalog palette section is updated
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
1. Measure live palette sizes and confirm proceeding for modest catalogs before implementation.
2. After approval, inspect palette/shared editor text-focus routing and write failing unit tests for pure filtering, grouping and focus logic.
3. Implement direct-input name/catalogId search, All/group toggles and hover tooltips. Preserve hidden selections and suppress camera/tool shortcuts while typing.
4. Update Catalog palette docs, run task check and runtime harness verification, and finalize with a conventional commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: Forest (seed 20261007) palette logged `EditorPalette: built 75 entries for Forest`. Other maps not measured yet.

2026-10-26: Started; dependency 005.02 completed. Measured stageIndex=0, tier=0, seed=20261007: Forest 75 entries (fresh relaunch succeeded); Desert 73 entries (Latest.log repeatedly recorded EditorPalette: built 73 entries for Desert). Desert relaunch helper failed after readiness retries despite building the palette; this is not a successful end-to-end check. Catalogs are modest, roughly 70 entries. Paused for Lance to confirm proceeding per task description. No implementation changes or criteria checked. Existing untracked task-015 and scratch level files left untouched.

2026-10-26: Lance approved proceeding despite the modest catalog sizes. Continuing with the recorded implementation plan.

2026-10-26: Implemented live case-insensitive name/catalogId search, stage/category cycling with a direct All reset, empty-result feedback and name/id hover tooltip. Existing rows are hidden/relaid out without replacing the full PaletteSelection catalog. Search focus state captures keyboard through the blur frame; shared editor guard suppresses camera/look/centering, tool digits, object shortcuts and undo/redo while search or save text is active. No EventSystem/Rewired changes. Updated Catalog palette docs.

Verification: wrote filtering/focus tests before implementation; initial task mod:test failed on missing PaletteFilter/PaletteSearchInput types. Added 13 test cases and verified task check passes: mod build, 703 C# tests, 185 Python tests, markdownlint and ruff. git diff --check passes.

Runtime verification on fresh Forest relaunch: rOcK showed only rock names; FOREST/SHRINES matched the five shrine ids despite case; selecting filtered rock_medium_01 showed name + forest/stage0/randomMapObjects/3/0 tooltip, and remained selected while hidden by shrine/group filters. While focused, held W/Space and tapped Alpha1/C left camera framing and Select unchanged. Escape ended focus; clicking group controls outside search ended focus and subsequent Alpha2 selected Lower. Stage 0 flat tiles showed only its nine entries; incompatible query/group showed No matching entries; previous-group from All wrapped to Interactables; All reset restored the full catalog and selection highlight. No ERROR/Exception lines in the current launch log. Screenshots are under the approved OpenCode temporary directory: palette-name-filter-focus.png, palette-selected-tooltip.png, palette-id-filter-hidden-selection.png, palette-group-no-results.png, palette-flat-group.png, palette-interactables-wrap.png and palette-all-restored.png.

Implementation committed as fb2f89e (feat(editor): add palette search, group filters and tooltips), with no attribution. All six acceptance criteria and four Definition of Done items verified.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added live case-insensitive palette name/id search, stage/category cycling with an All reset, empty results feedback and full name/id hover tooltips. Filtering preserves hidden selections; text focus blocks camera and editor shortcuts without touching Rewired/EventSystem. Added 13 test cases and updated Catalog palette docs. Verified in the running Forest editor and with task check (703 C# tests, 185 Python tests, build and lint). Implementation commit: fb2f89e. Thumbnails/icon grid remain out of scope.
<!-- SECTION:FINAL_SUMMARY:END -->
