---
id: TASK-005
title: In-game editor UI
status: Done
assignee: []
created_date: '2026-10-06 21:42'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-004
priority: high
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: build the actual WYSIWYG, in-game level editor — the user-facing deliverable the maintainer originally asked for — so a non-technical player can open an overlay in-game, place/move/remove tiles and objects visually, undo/redo, see unreachable areas flagged, save their level, and immediately play it. Everything this builds on (level format, edit stack, reachability validator, runtime playback, edit application, navmesh rebuild) was built in TASK-003 and TASK-004; this task is "put a UI in front of it."

## Context

The game's UI stack is UGUI + TextMeshPro with Rewired input (confirmed from earlier research — `RewiredEventSystem`). No UI Toolkit usage was found in game code, so the editor overlay should use the same UGUI+TMP stack the game already ships, for visual consistency and to avoid pulling in a UI framework the game doesn't already have loaded.

Read TASK-003's `docs/level-format.md` and TASK-004's integration docs before starting — this task wires a UI onto TASK-003's `EditStack`/`ReachabilityValidator` and TASK-004's live-application/runtime-save-load machinery, reusing them directly rather than reimplementing editing logic in UI-event-handler code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A player can enter an editor mode in-game via a keybind, freezing gameplay and switching to a free-fly camera
- [x] #2 A catalog palette shows placeable objects/tiles available for the current map, sourced from the real game's prefab catalog
- [x] #3 Tile tools (raise, lower, slope rotate, remove) and object tools (place with grid snap, move, rotate, delete) are usable via mouse/keyboard in the overlay
- [x] #4 Undo/redo is exposed in the UI and backed by TASK-003's EditStack
- [x] #5 A validate action highlights unreachable tiles using TASK-003's reachability validator
- [x] #6 A level can be saved to and loaded from disk via the UI, using TASK-003's file format and TASK-004's load/apply machinery
- [x] #7 F8 toggles editing and live playtesting of the same run with unsaved edits applied, preserving edit history without a stage reload
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every acceptance criterion is delivered by a Done subtask. #1 editor entry, freeze and free-fly camera: TASK-005.01. #2 catalog palette: TASK-005.02, with search/tabs/tooltips in .07, thumbnails in .08 and the compact layout in .11. #3 tile and object tools: TASK-005.03 and .04, with object picking and rings in .04.01 and three-axis rotation in .09. #4 undo/redo, #5 validate overlay and #6 save/load UI: TASK-005.05. #7 F8 same-run edit/playtest toggle: TASK-005.06, confirmed hands-on by the maintainer. HUD and toast layout: TASK-005.10 and .12. Verification: task check passes (804 C# tests, 185 Python tests, markdownlint, ruff).
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
