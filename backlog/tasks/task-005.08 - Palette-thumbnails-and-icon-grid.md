---
id: TASK-005.08
title: Palette thumbnails and icon grid
status: To Do
assignee: []
created_date: '2026-10-10 06:23'
labels:
  - level-editor
dependencies:
  - TASK-005.07
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/editor_palette.cs
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
- [ ] #1 A rendered prefab thumbnail is confirmed visible in the running game before the grid is built, with the method recorded in docs
- [ ] #2 Each palette entry shows a thumbnail in a grid; an entry whose prefab cannot be rendered falls back to its name
- [ ] #3 Thumbnails are cached so re-entering editor mode on the same map does not re-render them
- [ ] #4 Search, category tabs, tooltip and selection from TASK-005.07 keep working in the grid
- [ ] #5 docs/development.md Catalog palette section is updated, including the editor-entry cost measured in the game
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
