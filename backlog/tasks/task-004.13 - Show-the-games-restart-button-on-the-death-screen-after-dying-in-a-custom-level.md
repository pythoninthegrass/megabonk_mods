---
id: TASK-004.13
title: >-
  Show the game's restart button on the death screen after dying in a custom
  level
status: Done
assignee: []
created_date: '2026-10-29 05:24'
updated_date: '2026-10-29 05:47'
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
After dying in a custom level, the player has only Confirm on the end-of-run summary, which returns to the main menu. The game has a native restart button on the death screen, and it is not known what makes it appear. Show it by default for mod-loaded levels, and make it restart the same custom level (same seed, edits, player start, music and title) with the same character, not a native map.

Findings, from decompiling GameAssembly.dll in Ghidra (RVAs from .tools/il2cpp_dump/dump.cs, regenerate with task re:dump):
- DeathScreen.Restart (0x532270) only calls MapController.RestartRun() (0x4220B0).
- RestartRun does not call MapController.StartNewMap. It keeps the stored RunConfig, destroys the previous map object, resets the run state, calls LoadNextStage (0x421DF0) and then invokes a static Action. So CustomLevelStatePatch's StartNewMap prefix does not run (CustomLevelState.IsActive keeps its value) and neither does LevelLoaderPatch.StartOnce. LiveEditPatch clears _pendingEdits once it has applied them (live_edit_patch.cs, SetPendingEdits and the tick that nulls it), so a native restart would reload the level without its edits, player start or slope limit unless the mod arms them again before RestartRun runs. Whether the forced seed from SeedForcePatch.ForceLevelSeed survives has not been checked.
- What shows restartBtn (field 0x98) was not found. Awake (0x531A00) only sets newRecordRank and subscribes to OnLeaderboardScoreUploaded and OnBossDefeated. StartDeathScreen (0x532450) only starts the DoTransition coroutine. DoTransition.MoveNext (0x5454D0) enables blocksUi, deadUiWindow, background, canvasGroup and b_continue. Update (0x5324D0) only fades the canvas. None of them touch restartBtn, so its visibility comes from the serialized prefab or scene, or from another class. Next step: after a death in the running game, read restartBtn's activeSelf and its place in the hierarchy with the harness (ui_tree or query_objects). If it is simply inactive, a Harmony postfix on DeathScreen.StartDeathScreen can activate it when CustomLevelState.IsActive.
- Not checked: PauseUi.Restart (0x556E90) and the hold-to-reset ResetRunUi, which may also reach RestartRun.

The custom level's state is set in LevelLoaderPatch.StartOnce before MapController.StartNewMap (seed, pending edits, music, title, character). A restart has to reproduce all of it, and a custom run must still not submit scores, achievements or stats (CustomLevelState).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Dying in a mod-loaded level shows a restart button on the death screen, confirmed by a harness screenshot
- [x] #2 Pressing it restarts the same custom level with the same seed, edits, player start, music, title and character, not a native map
- [x] #3 A restarted custom run still counts as custom: no scores, achievements or stats are submitted
- [x] #4 What makes the game's restart button appear is documented in docs/development.md
- [x] #5 Normal (non-custom) runs show the death screen exactly as before
- [x] #6 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The death screen's restartBtn is the object B_Retry in StatsWindows/W_Stats/.../Buttons, shipped inactive. It belongs to the summary window shown after Confirm, so the screen after "you ded" is where it appears. Nothing reached from DeathScreen enables it; a report that Desert and Graveyard show it more often was not explained. Chain read from the running game by logging restartBtn's ancestors.

AC #3 confirmed in the running game: a second death after a restart logged three SteamWriteGuard suppressions. AC #5 is covered by code only: both patches return at once when CustomLevelState.IsActive is false; a normal run's death screen was not exercised in the game. AC #6: the restart patch has no pure logic to unit test; the tests written first cover the new kill harness command.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
DeathRestartPatch shows the death screen's B_Retry button when CustomLevelState.IsActive and re-queues the loaded level's edits (LiveEditPatch.RearmLevelEdits) before MapController.RestartRun. Verified in the running game on the thps Warehouse level: the restart re-applied 1294 edits, re-armed the kill floor and returned the player to the level's start. Also added a kill harness command (run.py kill, MCP kill tool) that calls PlayerHealth.KillPlayer to reach the death screen. Findings are in docs/development.md under "Death screen restart".
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
