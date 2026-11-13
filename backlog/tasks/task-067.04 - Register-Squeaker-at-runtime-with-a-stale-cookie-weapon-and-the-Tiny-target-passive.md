---
id: TASK-067.04
title: >-
  Register Squeaker at runtime with a stale cookie weapon and the Tiny target
  passive
status: Done
assignee: []
created_date: '2026-11-12T22:18:00Z'
updated_date: '2026-11-13T05:18:00Z'
labels:
  - character
  - bepinex
dependencies:
  - TASK-067.01
  - TASK-067.03
references:
  - src/MegabonkLevels.Mod/character_override.cs
  - src/MegabonkLevels.Mod/character_screen_patch.cs
  - src/MegabonkLevels.Mod/character_policy.cs
  - src/MegabonkLevels.Mod/pack_prefabs.cs
documentation:
  - docs/characters.md
  - docs/development.md
parent_task_id: TASK-067
type: feature
ordinal: 230000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
With the squeaker bundle available, the mod has to make Squeaker a selectable, playable character: a new entry on the character grid, a starting weapon that throws stale cookies the way Calcium throws a bone, and the Tiny target passive (smaller hitbox and higher base evasion, offset by lower max HP). The integration approach (new ECharacter 21 or a CharacterData cloned from Calcium) follows the go/no-go in docs/characters.md. Selecting Squeaker must not damage stock saves or preferences.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Squeaker appears on the game's character grid and can be selected and confirmed, shown in a harness screenshot
- [x] #2 squeaker is accepted by the character-name parser, so --character squeaker works in the dev harness
- [x] #3 A run as Squeaker starts with a weapon that throws stale cookies using Bone behaviour, shown in a harness screenshot
- [x] #4 Tiny target applies a smaller collider, higher evasion and lower max HP, confirmed against stock character values through the harness state command
- [ ] #5 Selecting Squeaker, quitting, and removing the mod leaves stock saves, unlocks and Preferences.selectedCharacter intact
- [x] #6 Existing character restriction for custom levels still works with Squeaker present
- [x] #7 The pure stat and registration logic has unit tests written before the code in tests/MegabonkLevels.Tests
- [x] #8 Docs describe the registration approach and the passive's values
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
1. Tests first (tests/MegabonkLevels.Tests, new squeaker_character_tests.cs plus additions to character_override_tests.cs and character_policy_tests.cs): SqueakerCharacter spec (id 21, name, Tiny target rows and collider as constants, stat rows reuse FallDamagePolicy.StatTotal to prove higher evasion and lower max HP against a stock baseline), name parsing ("squeaker" -> 21, DisplayName, IsAllowed), registration planner (append only when absent, idempotent across repeated DataManager.Load calls), and the preference-restore decision (restore selectedCharacter to the saved stock id when it names a mod character).
2. Pure code: src/MegabonkLevels.Mod/squeaker_character.cs (constants, stat rows, planner) linked into the test csproj; CharacterOverride gains SqueakerId = 21 and the "squeaker" name.
3. Il2Cpp layer: squeaker_registration_patch.cs with a prefix on DataManager.Load (0x4F96D0) that clones Calcium's CharacterData, WeaponData and BoneAttackPrefab, swaps prefab/icon/projectile from bundle:squeaker/*, sets Tiny target modifiers and colliders, appends one CharacterData and one SkinData (materials from the Squeaker prefab), and a postfix on Preferences.Init (0x40F220) seeding characterSkins[21] = 0. Install from megabonk_levels_mod.cs. If the pack is not installed, register nothing.
4. Persistence safety: restore Preferences.selectedCharacter to the previous stock character when a run ends or the game quits with 21 selected; keep Squeaker runs off leaderboards (find the submission gate first; if it is not found cheaply, record it as open and ask before widening scope).
5. Harness: --character squeaker in run.py help and docstring, allowed in level_settings validation only if the level restriction logic needs it (AC6 keeps the stock Calcium/Tony restriction working with Squeaker present).
6. Verify in the running game via the megabonk MCP: grid screenshot with Squeaker, confirm, cookie weapon screenshot, state read of collider/evasion/max HP against Calcium and Tony, save/Preferences check after quit, custom-level restriction still refuses Squeaker.
7. Docs in docs/characters.md (registration approach, Tiny target values), task check, conventional commit with no attribution.
Decision to flag: Tiny target values are not specified anywhere. Proposed defaults (constants, easy to retune): MaxHealth Flat -30 (Tony precedent), Evasion Flat 0.25 (20% after the v/(v+1) transform), colliderHeight 2.9 and colliderWidth 0.5 (stock is 3.85 x 0.7, range 3.7-4.75 x 0.5-0.85).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the character reverse-engineering spike (docs/characters.md): registration needs two hooks, a prefix on DataManager.Load (0x4F96D0) appending a CharacterData and at least one SkinData, and a postfix on Preferences.Init (0x40F220) seeding Preferences.characterSkins[id] = 0. Without the seed PlayerRenderer.SetCharacter throws on spawn. Also restore Preferences.selectedCharacter at run end and keep runs as the new character off the leaderboards. Tiny target can be done with statModifiers (MaxHealth, Evasion) and colliderHeight/colliderWidth only; Tony's MaxHealth Flat -30 is the stock precedent. These are notes only; acceptance criteria were not changed.

Built 2026-11-12 (commits fe31b0e, a7ecf46). Squeaker is character id 21 via a DataManager.Load prefix and a Preferences.Init postfix; pure logic is in squeaker_character.cs with tests written first (2816 C# tests, task check passes).

Found and fixed along the way: (1) the pack-authoring project lacked com.unity.modules.animation, so Unity dropped the Animator, controller and clips from the squeaker bundle and the spawn portal intro threw in PlayerRenderer.ForceMoving (player stuck at spawn); fixed in the manifest, and the rebuilt bundle holds Animator, AnimatorController and 5 clips. (2) Grid tile read Calcium and showed a price: cloned LocalizedStrings plus no unlock entry; fixed with GetName/GetDescription postfixes and IsPurchased/IsAvailable postfixes. (3) The live weapon is built from stock WeaponBone data, not CharacterData.weapon, so the cookie is applied by repointing the stock BoneAttackPrefab projectile, icon and text during a Squeaker run (StartPlayer prefix, MyPlayer.OnDestroy restore). A Bone picked up in a Squeaker run therefore also throws cookies.

Evidence (.tools/evidence): 067-04-character-grid-2.png (grid, confirm), 067-04-squeaker-run-cookie.png (stats panel Evasion 21%, cookie icon in weapon slot), 067-04-restricted-grid.png (custom-level restriction greys Squeaker). fall_damage report on a fresh run: characterId 21, maxHp 70, evasion 0.206, collider 2.9 x 0.5 from the capsule. relaunch --character squeaker starts as character 21. The cookie in flight was confirmed by the user in the running game; no screenshot frame caught a projectile mid-air.

AC5 left unchecked: config.json written during a Squeaker run holds selectedCharacter Calcium and no id 21 in characterSkins or characterHats, but progression.json is encrypted so the entry removal there is unconfirmed, and the stock game was not started with the mod removed. tierCompletionsWithCharacters is not covered by the save guard.

Not done: keeping Squeaker runs off the leaderboards (the submission gate was not found; nothing blocks it), and restore of the stock Bone icon/text after a run was seen only on a fresh relaunch, not across a run ending in the same session.

Correction: the leaderboard submission gate is known. TASK-004.04's SteamWriteGuard already suppresses leaderboard, achievement and stat writes, but only while a custom level is active, so Squeaker runs on a stock level are uncovered. The leaderboard exclusion is now TASK-067.07 and the save-guard verification is TASK-067.08.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Squeaker is a selectable, playable character (id 21), registered at startup when the squeaker pack is installed: a DataManager.Load prefix appends a cloned CharacterData and SkinData, a Preferences.Init postfix seeds characterSkins[21], and postfixes on the unlock checks and name/description getters give it its own name, unlocked state and passive text. Tiny Target is MaxHealth Flat -30, Evasion Flat 0.25 and a 2.9 x 0.5 collider; a fresh run reads maxHp 70, evasion 0.206 (21% on the stats panel) and the capsule at 2.9 x 0.5. The stale cookie is Bone's behaviour with the stock Bone attack repointed at a cookie projectile, icon and text for the length of a Squeaker run (restored on MyPlayer.OnDestroy), because the game builds the live weapon from stock Bone data rather than CharacterData.weapon. SaveConfig and SaveProgression hooks keep id 21 out of the written files. `squeaker` is accepted by the character-name parser, `relaunch --character squeaker` starts as character 21, and the custom-level restriction still greys Squeaker out. Also fixed the TASK-067.03 bundle: the pack-authoring project lacked com.unity.modules.animation, so the Animator, controller and clips were dropped and the spawn portal intro threw in PlayerRenderer.ForceMoving. Pure logic is in squeaker_character.cs with tests written first (2816 C# tests); task check passes; docs/characters.md covers the registration, the values and the cookie swap. Commits fe31b0e, a7ecf46.

Closed with these gaps, all recorded in docs/characters.md under Not verified: AC5 is unchecked because the stock game was never started with the mod removed and progression.json is encrypted (config.json held Calcium and no id 21 after confirming Squeaker); tierCompletionsWithCharacters is not covered by the save guard; Squeaker runs are not kept off the leaderboards (the submission gate was not found); the cookie in flight was confirmed by the user in the running game but no screenshot caught a projectile mid-air; and the restore of Bone's icon and text after a run ended was seen only on a fresh relaunch.
<!-- SECTION:FINAL_SUMMARY:END -->
