---
id: TASK-005
title: In-game editor UI
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
labels:
  - level-editor
dependencies:
  - TASK-004
priority: high
type: feature
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: build the actual WYSIWYG, in-game level editor — the user-facing deliverable Lance originally asked for — so a non-technical player can open an overlay in-game, place/move/remove tiles and objects visually, undo/redo, see unreachable areas flagged, save their level, and immediately play it. Everything this builds on (level format, edit stack, reachability validator, runtime playback, edit application, navmesh rebuild) was built in TASK-003 and TASK-004; this task is "put a UI in front of it."

## Context

The game's UI stack is UGUI + TextMeshPro with Rewired input (confirmed from earlier research — `RewiredEventSystem`). No UI Toolkit usage was found in game code, so the editor overlay should use the same UGUI+TMP stack the game already ships, for visual consistency and to avoid pulling in a UI framework the game doesn't already have loaded.

Read TASK-003's `docs/level-format.md` and TASK-004's integration docs before starting — this task wires a UI onto TASK-003's `EditStack`/`ReachabilityValidator` and TASK-004's live-application/runtime-save-load machinery, reusing them directly rather than reimplementing editing logic in UI-event-handler code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A player can enter an editor mode in-game via a keybind, freezing gameplay and switching to a free-fly camera
- [ ] #2 A catalog palette shows placeable objects/tiles available for the current map, sourced from the real game's prefab catalog
- [ ] #3 Tile tools (raise, lower, slope rotate, remove) and object tools (place with grid snap, move, rotate, delete) are usable via mouse/keyboard in the overlay
- [ ] #4 Undo/redo is exposed in the UI and backed by TASK-003's EditStack
- [ ] #5 A validate action highlights unreachable tiles using TASK-003's reachability validator
- [ ] #6 A level can be saved to and loaded from disk via the UI, using TASK-003's file format and TASK-004's load/apply machinery
- [ ] #7 A playtest action reloads the stage with the current edits applied and lets the player walk it immediately, without leaving the game
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
