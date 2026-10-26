---
id: TASK-005.08
title: Palette thumbnails and icon grid
status: In Progress
assignee: []
created_date: '2026-10-10 06:23'
updated_date: '2026-10-26T20:20:00Z'
labels:
  - level-editor
dependencies:
  - TASK-005.07
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/editor_palette.cs
modified_files:
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/palette_filter.cs
  - src/MegabonkLevels.Mod/palette_pager.cs
  - src/MegabonkLevels.Mod/thumbnail_cache.cs
  - src/MegabonkLevels.Mod/prefab_thumbnails.cs
  - tests/MegabonkLevels.Tests/palette_filter_tests.cs
  - tests/MegabonkLevels.Tests/palette_pager_tests.cs
  - tests/MegabonkLevels.Tests/thumbnail_cache_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - docs/development.md
parent_task_id: TASK-005
priority: low
ordinal: 48000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Optional. Read parent TASK-005, TASK-005.07 and the "Catalog palette" section of docs/development.md first.

The palette (TASK-005.02, filtered by TASK-005.07) lists prefabs by name only. TASK-005.02 left thumbnails out because each prefab needs an off-screen camera and lighting to render. Lance's model is the Minecraft "Better Creative Mode" mod: an icon grid with pages and a name/id tooltip, where many items can be recognised at a glance.

This task renders a thumbnail per palette entry and shows the palette as a paged or scrolling icon grid, keeping the search, tabs and tooltip from TASK-005.07. Rendering prefabs to a RenderTexture in this Il2Cpp build is unconfirmed (shader stripping, layer setup, lighting), so prove it in the running game on one prefab before building the grid. Render once per editor entry and cache the result; the cost of a palette rebuild has to stay acceptable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A rendered prefab thumbnail is confirmed visible in the running game before the grid is built, with the method recorded in docs
- [x] #2 Each palette entry shows a thumbnail in a grid; an entry whose prefab cannot be rendered falls back to its name
- [x] #3 Thumbnails are cached so re-entering editor mode on the same map does not re-render them
- [x] #4 Search, category tabs, tooltip and selection from TASK-005.07 keep working in the grid
- [x] #5 docs/development.md Catalog palette section is updated, including the editor-entry cost measured in the game
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
1. Add test-first category filter, PalettePager and ThumbnailCache.
2. Render thumbnails from a proxy copy of each prefab's meshes (no Instantiate) on layer 31, into a 128x128 RenderTexture, and prove it in the running game.
3. Replace the text list with a paged icon grid: category tabs on the left, grayscale scheme, wheel and arrow paging, white-border selection, name/id/stage tooltip.
4. Update the Catalog palette docs; run task check and the harness checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26: Layout follows Lance's Minecraft reference (left menu structure, bottom-right inventory grayscale). Decisions: one tab per category (stage moves into the tooltip), paged grid with n/m footer, white border for the selected slot. Removed PaletteScroll and its tests, and the All/prev/next group cycling.

Runtime check on Forest (75 entries): thumbnails visible in the grid and on tabs; first entry rendered 75 thumbnails in 716 ms, second entry rendered 0 (cached 75); slot click selects with white border; page arrows 1/3 -> 2/3; Flat tiles tab 1/1 with tooltip showing name, id and stage; search 'shrine' filtered to 5 slots and the hidden selection stayed selected; no ERROR/Exception in Latest.log. Four Forest prefabs (Forest0_Prefab4/5, Forest2_Prefab4/5) show the name fallback; the cause per prefab was not checked.

Not verified: physical Esc sequence in the search field (Tick search/Esc code is unchanged but the new layout was only checked through the harness), wheel paging (harness mouse tool has no wheel), and Desert.
<!-- SECTION:NOTES:END -->
