---
id: TASK-004.12
title: >-
  Pick Calcium or Tony McZoom on the game's character select screen for custom
  levels
status: To Do
assignee: []
created_date: '2026-10-28T21:02:00Z'
updated_date: '2026-10-29 05:24'
labels:
  - level-editor
dependencies:
  - TASK-004.07
references:
  - src/MegabonkLevels.Mod/env_flag.cs
documentation:
  - docs/development.md
  - src/MegabonkLevels.Mod/character_override.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
parent_task_id: TASK-004
priority: medium
ordinal: 112000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-004.07 forces Tony McZoom on every mod-loaded level (CharacterOverride.TryApply sets CharacterMenu.selectedCharacter to 13 in LevelLoaderPatch). Replace the forced choice with the game's own Character Selection screen, restricted to Calcium (the skateboarder, ECharacter.Calcium = 1) and Tony McZoom (ECharacter.TonyMcZoom = 13). Pin those two at the top left of the grid and show every other character greyed out and unselectable, the way a locked character such as Roberto already appears. Do not build a separate picker.

Findings from reading .tools/il2cpp_dump/dump.cs (regenerate with task re:dump); the bodies are not yet confirmed in Ghidra:
- CharacterMenu (Window) builds the grid in TryInit (RVA 0x54A8E0) from characterPrefabUi under characterGridParent and keeps the buttons in a private List<MyButtonCharacter> characterButtons. Confirm is OnConfirmCharacter (0x549C90), which sets the static CharacterMenu.selectedCharacter.
- Grid order probably comes from UnlockableBase.CompareTo (0x418480) using sortingPriority (0x2C) on each CharacterData. Confirm whether that is true or whether TryInit orders them another way.
- MyButtonCharacter already has canUseCharacter (0xA0), cantUseCharacterReason (0xB0) and an unavailableOverlay (0x60), which look like a native greyed-out-with-reason state. Check whether setting them also blocks Confirm. This is separate from the locked Roberto look, which comes from CharacterData.IsBlackedOutInCharacterSelectionScreen (0x3819E0) and shows a silhouette with ??? requirements.
- Preferences.selectedCharacter is the saved setting and must not be overwritten.

Open question: the character select screen is the main menu's normal screen, so the mod needs a way to know the player opened it to start a custom level, and normal runs must keep the stock grid. Decide how a custom run is entered from the menu (this overlaps TASK-006.01, whose map selection screen lists Warehouse).

Skipping the menu: unattended harness loads and editor sessions must not block on the screen. A DEV=true style flag (read like the existing MEGABONK_* settings, see src/MegabonkLevels.Mod/env_flag.cs) launches straight into the editor or the level with a default character (Tony McZoom) or a character named by the harness. With the flag off, the player goes through the screens.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The game's Character Selection screen shows Calcium and Tony McZoom pinned at the top left, with every other character greyed out and unselectable, when a custom level is being started
- [ ] #2 Only Calcium and Tony McZoom can be confirmed, and the run starts as the chosen character, confirmed by a harness screenshot of each
- [ ] #3 A normal (non-custom) run from the main menu still shows the stock character order with nothing greyed out
- [ ] #4 With the dev flag on, a harness load or editor launch skips the screen, defaults to Tony McZoom and can name Calcium instead, without blocking
- [ ] #5 The player's saved character preference is unchanged after a mod-loaded run
- [ ] #6 How Calcium's skateboard look is applied is documented in docs/development.md
- [ ] #7 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
