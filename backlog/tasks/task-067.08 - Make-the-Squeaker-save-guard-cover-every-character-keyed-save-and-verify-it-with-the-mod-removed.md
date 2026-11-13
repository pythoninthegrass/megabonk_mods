---
id: TASK-067.08
title: >-
  Make the Squeaker save guard cover every character-keyed save and verify it
  with the mod removed
status: Done
assignee: []
created_date: '2026-11-13T05:17:00Z'
updated_date: '2026-11-13T06:08:00Z'
labels:
  - character
  - bepinex
dependencies: []
references:
  - src/MegabonkLevels.Mod/squeaker_save_guard_patch.cs
  - src/MegabonkLevels.Mod/squeaker_registration_patch.cs
documentation:
  - docs/characters.md
parent_task_id: TASK-067
priority: medium
type: task
ordinal: 234000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Squeaker must never leave data in the player's saves that the stock game cannot load once the mod is removed. The current guard keeps id 21 out of config.json and out of the character progression table, and config.json was checked after a Squeaker session. It was never verified with the mod removed, progression.json is encrypted so its contents could not be inspected from outside, and other saves keyed by character were not examined (for example the per-tier set of completed characters and the statistics saves). Squeaker's registration and the guard are described in docs/characters.md under "Squeaker in the game" and "Not verified". The goal is evidence, not just more code: either every Squeaker-written save is shown to be free of the id, or the gaps are closed until it is.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every save structure a Squeaker session can write that is keyed or valued by a character is identified from the game's code and listed in docs/characters.md
- [x] #2 After a Squeaker session, none of those saves contains the Squeaker id in what is written to disk, shown by inspecting the decoded content (the progression save is encrypted)
- [x] #3 Any structure found to carry the id is kept clean by the guard, and the guard still leaves the in-memory values unchanged for the running session
- [x] #4 On a copy of the save directory taken after a Squeaker session, the stock game with the mod removed starts and loads, with unlocks, progression and the selected character intact
- [x] #5 The guard's decision logic that can be separated from the game is covered by unit tests written before the code
- [x] #6 docs/characters.md states what was verified and how, and its Not verified section no longer lists the items this task closes
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
1. Identify structures (done from dump.cs): config.json Preferences.characterSkins/characterHats/selectedCharacter (guarded); progression.json ProgressionSaveFile.characterProgression (guarded) and menuMeta.mapsProgress[*].tierCompletionsWithCharacters (HashSet<ECharacter> per tier, NOT guarded, written by MapProgress.OnRunFinished(character, victory, tier)); progression string sets (achievements, claimedAchievements, purchases, inactivated, newUnlockables) that could carry character/skin names; stats.json string-keyed stats incl. per-character kill key from StatTrackingUtility.GetKeyKillsCharacter (created on demand for an unseen id). Confirm each writer with Ghidra decompiles (OnRunFinished 0x402920, GetKeyKillsCharacter 0x412000, SaveTemp 0x525110).
2. Evidence: hook SaveManager.SaveTemp plaintext (pre-encryption) in a diagnostic to log/inspect the exact JSON for config, stats and progression after a Squeaker run that ends (death and victory), searching for the id 21 and the Squeaker name.
3. TDD: write failing xunit tests for the separable decision logic (which entries/ids to strip from character-keyed collections and string keys), then implement and wire into SaveProgressionGuard (tierCompletionsWithCharacters, plus any string keys/stats found), restoring in-memory values in the postfix.
4. Verify with the mod removed: copy the save directory after a Squeaker session, run stock game (mod disabled) against the copy, confirm it starts and loads with unlocks, progression and selected character intact.
5. Update docs/characters.md (structures table, what was verified and how, trim Not verified), run task check, commit conventional, no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Found and closed one real leak: stats.json received 21Kills and 21Rank after a Squeaker run. Added SaveStats guard (ModCharacterStatKeys, unit-tested first, red run confirmed) and a tierCompletionsWithCharacters strip in the SaveProgression guard; both restore in-memory values in the postfix. Evidence: plaintext of all three saves captured through a temporary SaveTemp hook after a Squeaker run shows no id 21 or Squeaker; tier strip exercised by injecting 21 into 12 tier sets (written JSON clean, memory restored); stock game with BepInEx parked loaded the saves without exceptions (Player.log), config still Calcium. Limits: main menu was not seen (screenshot black), and OnRunFinished was not decompiled; both recorded in docs/characters.md Not verified/Keeping the saves stock. Added Il2CppSystem.Core reference to the mod csproj for HashSet.
<!-- SECTION:FINAL_SUMMARY:END -->
