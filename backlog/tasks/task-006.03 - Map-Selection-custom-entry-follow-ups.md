---
id: TASK-006.03
title: Map Selection custom entry follow-ups
status: To Do
assignee: []
created_date: '2026-10-29T18:30:00Z'
labels:
  - level-editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/map_selection_patch.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - src/MegabonkLevels.Mod/character_screen_patch.cs
documentation:
  - docs/development.md
parent_task_id: TASK-006
priority: low
type: bug
ordinal: 118000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-006 and TASK-006.01 first. Two known gaps remain on the custom Map Selection entry, see "Map Selection entries" in docs/development.md.

1. Backing out of Map Selection (or Character Selection) after Confirm holds a level, but the held load is only cleared by the next native Confirm. Backing out should call LevelLoaderPatch.CancelAwaitingCharacter() and CharacterScreenPatch.SetRestricted(false).
2. The right-hand detail panel (MapStatsWindow, MapStatsInfoUi) still shows the base map's runs, highscore and speedrun for a custom entry, because the entry carries that map's MapData. Decide whether it shows nothing or level text.

Code: src/MegabonkLevels.Mod/map_selection_patch.cs, level_loader_patch.cs, character_screen_patch.cs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Backing out of Map Selection or Character Selection after a custom level is held cancels the held load and lifts the character restriction, so the next native map starts unrestricted
- [ ] #2 For a custom entry the detail panel no longer shows the base map's runs, highscore or speedrun
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
