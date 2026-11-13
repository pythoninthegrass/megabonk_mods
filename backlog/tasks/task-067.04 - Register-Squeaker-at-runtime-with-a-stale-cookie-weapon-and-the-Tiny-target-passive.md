---
id: TASK-067.04
title: >-
  Register Squeaker at runtime with a stale cookie weapon and the Tiny target
  passive
status: To Do
assignee: []
created_date: '2026-11-12T22:18:00Z'
updated_date: '2026-11-13T04:06:00Z'
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
- [ ] #1 Squeaker appears on the game's character grid and can be selected and confirmed, shown in a harness screenshot
- [ ] #2 squeaker is accepted by the character-name parser, so --character squeaker works in the dev harness
- [ ] #3 A run as Squeaker starts with a weapon that throws stale cookies using Bone behaviour, shown in a harness screenshot
- [ ] #4 Tiny target applies a smaller collider, higher evasion and lower max HP, confirmed against stock character values through the harness state command
- [ ] #5 Selecting Squeaker, quitting, and removing the mod leaves stock saves, unlocks and Preferences.selectedCharacter intact
- [ ] #6 Existing character restriction for custom levels still works with Squeaker present
- [ ] #7 The pure stat and registration logic has unit tests written before the code in tests/MegabonkLevels.Tests
- [ ] #8 Docs describe the registration approach and the passive's values
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the character reverse-engineering spike (docs/characters.md): registration needs two hooks, a prefix on DataManager.Load (0x4F96D0) appending a CharacterData and at least one SkinData, and a postfix on Preferences.Init (0x40F220) seeding Preferences.characterSkins[id] = 0. Without the seed PlayerRenderer.SetCharacter throws on spawn. Also restore Preferences.selectedCharacter at run end and keep runs as the new character off the leaderboards. Tiny target can be done with statModifiers (MaxHealth, Evasion) and colliderHeight/colliderWidth only; Tony's MaxHealth Flat -30 is the stock precedent. These are notes only; acceptance criteria were not changed.
<!-- SECTION:NOTES:END -->
