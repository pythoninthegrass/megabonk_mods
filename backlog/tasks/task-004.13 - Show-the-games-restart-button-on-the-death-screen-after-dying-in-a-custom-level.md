---
id: TASK-004.13
title: >-
  Show the game's restart button on the death screen after dying in a custom
  level
status: To Do
assignee: []
created_date: '2026-10-29 05:24'
labels:
  - level-editor
dependencies: []
documentation:
  - docs/development.md
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - src/MegabonkLevels.Mod/custom_level_state.cs
parent_task_id: TASK-004
priority: medium
ordinal: 115000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After dying in a custom level, the player has only Confirm on the end-of-run summary, which returns to the main menu. The game has a native restart button for the death screen, and it is not clear what makes it appear. Show it by default for mod-loaded levels, and make it restart the same custom level (same seed, edits, player start, music and title) with the same character, not a native map.

Findings from reading .tools/il2cpp_dump/dump.cs (regenerate with task re:dump); the method bodies are not yet confirmed in Ghidra, so treat them as leads:
- DeathScreen (RVA 0x531A00 Awake, 0x532450 StartDeathScreen, 0x5324D0 Update) has a public GameObject restartBtn (field 0x98) and a public Restart() (0x532270), next to GoToMenu() (0x531CD0), ShowStats() and a tierVictory flag. The summary screen in the Damage, Summary and Quests layout is this class.
- MapController.RestartRun() (0x4220B0) is a static method that probably re-runs the current RunConfig. PauseUi.Restart() (0x556E90) and the hold-to-reset ResetRunUi also exist.
- Open questions to answer first: what activates restartBtn (a setting, a mode, a victory state or a Steam/leaderboard condition); whether RestartRun goes through MapController.StartNewMap, so that CustomLevelStatePatch and the forced seed apply, or restarts without it; and whether the pending edits, player start and CustomLevelState survive a restart or have to be set again.

The custom level's state is set in LevelLoaderPatch.StartOnce before MapController.StartNewMap (seed, pending edits, music, title, character). A restart has to reproduce all of it, and a custom run must still not submit scores, achievements or stats (CustomLevelState).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Dying in a mod-loaded level shows a restart button on the death screen, confirmed by a harness screenshot
- [ ] #2 Pressing it restarts the same custom level with the same seed, edits, player start, music, title and character, not a native map
- [ ] #3 A restarted custom run still counts as custom: no scores, achievements or stats are submitted
- [ ] #4 What makes the game's restart button appear is documented in docs/development.md
- [ ] #5 Normal (non-custom) runs show the death screen exactly as before
- [ ] #6 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
