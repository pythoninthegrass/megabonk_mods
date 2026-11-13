---
id: TASK-067.01
title: 'Reverse engineer how the game defines, registers and persists characters'
status: Done
assignee: []
created_date: '2026-11-12T22:18:00Z'
updated_date: '2026-11-13T04:06:00Z'
labels:
  - character
  - research
dependencies: []
references:
  - .tools/il2cpp_dump/dump.cs
  - src/MegabonkLevels.Mod/character_override.cs
  - src/MegabonkLevels.Mod/character_screen_patch.cs
documentation:
  - docs/development.md
modified_files:
  - docs/characters.md
parent_task_id: TASK-067
type: spike
ordinal: 227000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Squeaker needs a new character slot, and nothing in the repo records how the game builds its character list, what keys off ECharacter, or how Calcium's weapon and a passive are wired. Whether an out-of-range ECharacter (21) is safe decides the whole integration approach for the remaining subtasks, so it has to be settled from the game's native code before anything is built. Game logic exists only as native code in GameAssembly; the Il2Cpp interop assemblies are stubs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 docs/characters.md exists and records, from Ghidra decompiles through REA, how the game builds its character list (DataManager or equivalent) and registers CharacterData
- [x] #2 docs/characters.md covers CharacterData.Init, CharacterMenu.TryInit and MyButtonCharacter.SetCharacter, with RVAs
- [x] #3 docs/characters.md lists every place Preferences.selectedCharacter, unlock state, achievements and run stats key off ECharacter
- [x] #4 docs/characters.md documents Calcium's starting WeaponData (Bone) and where its projectile prefab or mesh comes from
- [x] #5 docs/characters.md documents PassiveData and EPassive, and how evasion, max HP and collider size are applied to the player
- [x] #6 docs/characters.md states a written go/no-go on registering ECharacter 21 at runtime, covering save, unlock, achievement and stats paths, and a concrete fallback design (CharacterData cloned from Calcium) if no-go
- [x] #7 docs/characters.md lists the rig, Animator and prefab-structure requirements that stock character prefabs impose
- [x] #8 docs/characters.md describes the content only, with no task ids
- [x] #9 markdownlint passes on docs/characters.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirm .tools/il2cpp_dump/dump.cs exists (regenerate with task re:dump if not) and locate RVAs with rg -u for DataManager, CharacterData, CharacterMenu, MyButtonCharacter, PassiveData, EPassive, WeaponData, MyPlayer.StartPlayer.
2. Open GameAssembly through REA with provider_id ghidra, using the existing snapshot in .tools/GameAssembly.
3. Decompile: DataManager character-list construction, CharacterData.Init (0x3817E0), CharacterMenu.TryInit (0x54A8E0), MyButtonCharacter.SetCharacter (0x552190), the MyPlayer spawn path, and the passive and weapon wiring for Calcium.
4. Trace every ECharacter consumer (Preferences.selectedCharacter, unlocks, achievements, run stats) to judge whether ECharacter 21 is safe.
5. Write docs/characters.md (content only, no task ids) with the go/no-go and fallback design, run markdownlint, and record findings in implementation notes.
6. Stop at the go/no-go and report to the user before any build work.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ghidra via REA works (Ghidra 12.1.4, GameAssembly.dll opened with provider ghidra; first query waited out auto-analysis). Findings so far, VAs = 0x180000000 + RVA:
- DataManager.Load (0x4F96D0) walks the serialized lists and fills the runtime dictionaries. For characters it iterates unsortedCharacterData (DataManager+0x30); each entry whose byte at +0x18 is non-zero is inserted into the characterData dictionary (DataManager+0x98) keyed by the int at CharacterData+0x50 (eCharacter), then CharacterData.Init is called on it. Skins (+0x70) are grouped into skinData (+0xC8) keyed by the character enum in SkinData (+0x60). Load ends by invoking the static A_DataLoaded action.
- DataManager.GetCharacterData (0x4F9030) is a bare Dictionary lookup on +0x98 with no fallback, so an ECharacter missing from the dictionary throws.
- CharacterData.Init (0x3817E0) builds categoryRatios (+0xA0) from StatCategoryRatios (+0xA8), then if passive (+0x88) is set and passive+0x38 (dummyPassive) is null it instantiates the passive through FUN_180476f20 and stores it.
- CharacterData.IsBlackedOutInCharacterSelectionScreen (0x3819E0): when achievementRequirement (+0xB0) is null, visibility falls to a comparison of a progress count against numQuestsRequiredForVisibilityInCharacterSelection (+0xB8). Null requirement plus 0 appears to leave a character visible and unlocked; confirm the count function before relying on it.
- Provisional reading: the character table is a plain Dictionary keyed by the enum int, so a value of 21 is storable. Still unverified: the character-select UI, spawn path, save and unlock keyed by ECharacter, and any enum-sized arrays.

Second batch of decompiles:
- CharacterMenu.TryInit (0x54A8E0) builds the grid from DataManager.unsortedCharacterData (not from the enum): it instantiates one MyButtonCharacter per entry, calls DataManager.GetCharacterData(eCharacter) for each and MyButtonCharacter.SetCharacter (0x552190), then pads the rest of the grid with empty buttons up to a static slot count. A CharacterData added to that list therefore gets a grid button. The selected button is matched by comparing eCharacter with Preferences.selectedCharacter.
- MyButtonCharacter.SetCharacter (0x552190) reads name, icon and unlock state from the CharacterData and calls ProgressionSaveFile.GetCharacterProgression (0x40FCF0). That method creates and stores a missing entry on demand, so progression is safe for an unseen id.
- StatTrackingUtility.GetKeyKillsCharacter (0x412000) also creates a missing cache entry on demand (safe). DataManager.GetCharacterData and GetCharacterName (0x3E3A20) are bare lookups: safe once registered.
- DataManager.GetSkins (0x4F9580) is a bare Dictionary.get_Item on skinData (DataManager+0xC8) and GetSkin (0x4F9450) indexes the resulting list, falling back to index 0. skinData only gets a key when at least one SkinData names that character, so a character with no SkinData would throw KeyNotFound. Squeaker needs at least one SkinData (character set to the new id) in unsortedSkins.
- Preferences (0x20 selectedCharacter, dictionaries characterSkins and characterHats) and ProgressionSaveFile.characterProgression are keyed by ECharacter, so a saved value of 21 persists in the save. Open risks: how those dictionaries deserialise an unknown enum value once the mod is removed, and what the game does on boot when Preferences.selectedCharacter names a missing character. The existing CharacterScreenPatch already saves and restores Preferences.selectedCharacter around its restriction; the same restore-on-exit pattern is the mitigation.
- 0x4B7C50 and 0x4B7B80 (PlayerMovement multiplier helpers) are not decompilable functions in Ghidra (invalid selector); read them from the dump or skip.

docs/characters.md written (markdownlint clean, no task ids or host paths). Third batch of findings, now in the doc:
- MyPlayer.StartPlayer (0x4B6A90) -> PlayerInventory ctor (0x4E0800) grants CharacterData.weapon through WeaponInventory.AddWeapon and instantiates CharacterData.passive; PlayerRenderer.SetCharacter (0x3474F0) instantiates CharacterData.prefab and reads an Animator, a SkinnedMeshRenderer and child transforms named exactly 'hips' and 'torso' (names confirmed from stringliteral.json); MyPlayer.RefreshSize (0x4B62F0) sets the capsule from colliderHeight and colliderWidth.
- Tiny target is expressible as data: EStat.MaxHealth (0) and EStat.Evasion (5) in statModifiers plus the two collider fields. No new PassiveAbility code is required; passive text for a custom passive is an open question (LocalizedString).
- WeaponData.attack (0xD0) is a prefab carrying WeaponAttack; its prefabProjectile (0x20) is the projectile. A stale cookie is a Bone-behaviour WeaponData copy whose attack prefab copy has prefabProjectile swapped.
- Registration path: prefix on DataManager.Load (unique RVA 0x4F96D0) appending a CharacterData and a SkinData to unsortedCharacterData and unsortedSkins; restore Preferences.selectedCharacter at run end.
- Verdict: GO for a new ECharacter value, with the stock-id clone as fallback.
Left unchecked on purpose: #3 (not every ECharacter consumer was decompiled: achievements, leaderboards, skin-achievement cache), #4 (Calcium's starting weapon is assumed Bone, not read from the running game), #5 (PlayerStatsNew handling of statModifiers not decompiled). Ghidra session left open on GameAssembly.dll for follow-up queries.

Gaps closed after the first report:
- Calcium's starting weapon read live with query_objects on CharacterData (21 objects, ids 0-20): eWeapon 1 (Bone), attack prefab BoneAttackPrefab, passive SpeedDemon (2). Monke is Banana/WallClimb, Tony is BluetoothBlade/Zap. Stock modifiers and collider sizes are tabulated in docs/characters.md.
- PlayerStatsNew recompute (0x446290) walks PlayerInventory.characterData.statModifiers first; total is (base + Flat) * (1 + Addition) * Multiplication; Evasion is stored as v/(v+1)*0.999, MaxHealth floors at 1. Tony's MaxHealth Flat -30 is the stock precedent for a lower-HP trait.
- NEW BLOCKER FOUND, now a required registration step: Preferences.Init (0x40F220) loops over Enum.GetValues(ECharacter) and seeds characterSkins and characterHats only for defined values. PlayerRenderer.SetCharacter reads characterSkins[eCharacter] through the throwing Dictionary<ECharacter,int> getter, so an unseeded id throws on spawn. GetCharacterHat (0x40F180) is guarded and safe. Fix: seed characterSkins[id] = 0 after Preferences.Init (postfix, unique RVA).
- GetSkinAchievementName (0x3D6DC0) and HatSelection.OnSelectCharacter (0x5683A0) create or guard missing entries, so they are safe. Leaderboard and rich-presence readers pass the integer through; an entry with an unknown id would be decoded by clients without the character, so runs as the new character must stay off the leaderboards.
- Verdict unchanged: GO for a new ECharacter value, with the required skin-preference seed and the stock-id clone as fallback.
Definition of Done #2 (tests written first) is not applicable to a documentation spike and is left unchecked.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Documented how the game defines, lists, spawns and persists characters in docs/characters.md, from Ghidra decompiles of GameAssembly.dll through REA and live query_objects reads. A character is a CharacterData in DataManager.unsortedCharacterData, loaded by DataManager.Load into a dictionary keyed by ECharacter; the select grid, the spawn path and stat totals all read from it. Verdict: GO for registering a new ECharacter value at runtime, via a prefix on DataManager.Load that appends a CharacterData and a SkinData, plus a postfix on Preferences.Init that seeds Preferences.characterSkins for the new id (found during this task: without it PlayerRenderer.SetCharacter throws). The fallback is cloning a stock id. Tiny target needs no passive code: MaxHealth and Evasion are statModifiers and the hitbox is colliderHeight and colliderWidth. A stale cookie is a Bone WeaponData copy whose BoneAttackPrefab copy has prefabProjectile swapped. The model prefab needs an Animator, a SkinnedMeshRenderer and bones named exactly hips and torso. Verification: markdownlint clean, task check exits 0 (1550 passed, 1 skipped), Calcium's weapon and stock stats read from the running game. Open risks recorded in the doc: behaviour with the mod removed after a run as the new character, untyped readers of the enum, leaderboard submission gating, custom passive text, and the throw helper behind the skin getter not being decompiled.
<!-- SECTION:FINAL_SUMMARY:END -->
