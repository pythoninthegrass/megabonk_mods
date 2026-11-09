---
id: TASK-006.01
title: Custom levels on the Map Selection screen
status: Done
assignee: []
created_date: '2026-10-06 21:44'
updated_date: '2026-10-29T18:30:00Z'
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

Custom levels are reached through the game's own Map Selection screen. Every titled `.mblevel.json` in `UserData/Levels/` is listed after the native maps, with a placeholder thumbnail and the level's mapDescription (else description). Confirm holds the level for LevelLoaderPatch's StartNewMap prefix, the stock Character Selection screen follows (restricted by the level's `allowedCharacters`), and the run starts through the mod's loader.

A separate level browser, an entry point inside the editor, and a gameBuildId-mismatch warning in the UI were dropped: the stock Map Selection and Character Selection screens are enough. The loader still logs the build-ID mismatch.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The game's Map Selection screen lists the Warehouse custom level beside the native maps, and confirming it starts that level through the mod's loader
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-004.12 is done. Hook for the Map Selection entry: LevelLoaderPatch.LoadAndStart holds a level when MEGABONK_DEV is unset, restricts the Character Selection screen through CharacterScreenPatch.SetRestricted(true), and a StartNewMap prefix swaps in the held level's RunConfig once a character is confirmed (the saved character preference is restored). See 'Character selection' and 'Map Selection entries' in docs/development.md.

Done and confirmed in the running game: the Map Selection screen lists every titled level in UserData/Levels after the native maps (MapSelectionPatch, CustomMapEntries), with a placeholder thumbnail, the level's mapDescription (else description), Tier 1 only and a controller-reachable entry. Confirm holds the level for the StartNewMap call that StartMap makes at once; the character is picked before the map on the stock screens, so the check is made at Confirm against the level's allowedCharacters and a refusal shows through MenuNotice. Restrictions are per level: LevelFile.allowedCharacters (absent means anyone) applied by CharacterPolicy.

Open gaps (backing out after a held load, base map stats in the detail panel) moved to TASK-006.03.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Custom levels are chosen on the game's own Map Selection screen. MapSelectionPatch clones a native map entry per titled level in UserData/Levels, Confirm holds the level for the StartNewMap prefix, and the stock Character Selection screen (restricted by the level's allowedCharacters) picks the character before the run starts through the mod's loader. A standalone browser, an in-editor entry point and a UI build-ID warning were dropped as unnecessary. Follow-ups are in TASK-006.03.
<!-- SECTION:FINAL_SUMMARY:END -->
