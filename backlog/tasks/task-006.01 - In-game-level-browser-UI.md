---
id: TASK-006.01
title: In-game level browser UI
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
updated_date: '2026-10-29 06:22'
labels:
  - level-editor
dependencies: []
documentation:
  - docs/development.md
parent_task_id: TASK-006
priority: medium
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-006 first for full context.

Build a standalone level browser UI (UGUI+TMP, consistent with TASK-005's editor styling) listing every `.mblevel.json` file in `UserData/Levels/`, showing at minimum: title/filename, map, and a `gameBuildId` mismatch warning (reusing TASK-004.01's build-ID comparison logic) when a level was saved against a different game build than the one currently running. Make it accessible both from within the editor (extending TASK-005.05's basic save/load dialog) and from a standalone entry point usable without first entering editor mode (e.g. a button on the main menu or map-selection screen), so a player who only wants to play other people's levels never has to touch the editor.

Selecting a level loads and starts it via TASK-004.01's loader.

Preferred entry point: the game's own Map Selection screen. It lists maps as entries (Forest, Desert, Graveyard) with a thumbnail, name and description, and a detail panel on the right with Confirm. Add a custom level to that list, starting with the THPS level named Warehouse (see the title and description overrides on LevelFile), so choosing it and pressing Confirm starts the custom run instead of a native map. After that the Character Selection screen follows (TASK-004.12).

Findings from reading .tools/il2cpp_dump/dump.cs (regenerate with task re:dump), not yet confirmed in the running game: MapSelectionWindow.InitButtons (RVA 0x570E30) builds the list from mapEntryPrefab; MapSelectionUi.StartMap (0x570D40) starts the run from its RunConfig; and the right-hand panel (MapStatsWindow, MapStatsInfoUi) shows runs, highscore, speedrun and tiers, which have no data for a custom level. Decide what the detail panel shows for a custom entry and how Confirm hands off to LevelLoaderPatch rather than MapController.StartNewMap with a native MapData.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The browser lists every .mblevel.json in UserData/Levels/ with title/filename, map, and a gameBuildId-mismatch warning where applicable
- [ ] #2 The browser is reachable from a standalone entry point (e.g. main menu or map selection) without requiring editor mode to be entered first
- [ ] #3 Selecting a level loads and starts it via TASK-004.01's existing loader
- [ ] #4 The browser UI is visually consistent with TASK-005's editor UI styling
- [ ] #5 The game's Map Selection screen lists the Warehouse custom level beside the native maps, and confirming it starts that level through the mod's loader
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-004.12 is done. Hook for the Map Selection entry: LevelLoaderPatch.LoadAndStart holds a level when MEGABONK_DEV is unset, restricts the Character Selection screen through CharacterScreenPatch.SetRestricted(true), and a StartNewMap prefix swaps in the held level's RunConfig once a character is confirmed (the saved character preference is restored). Confirming the custom Map Selection entry should queue the level the same way instead of calling MapController.StartNewMap itself; cancelling back to the menu should call LevelLoaderPatch.CancelAwaitingCharacter() and CharacterScreenPatch.SetRestricted(false). See 'Character selection' in docs/development.md. run.py relaunch --no-level (MCP relaunch(no_level=true)) reaches the main menu without a level for testing the screens; the harness cannot press menu buttons, so the menu flow is clicked by hand.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
