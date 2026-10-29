---
id: TASK-004.12
title: >-
  Pick Calcium or Tony McZoom on the game's character select screen for custom
  levels
status: To Do
assignee: []
created_date: '2026-10-28T21:02:00Z'
updated_date: '2026-10-29 05:37'
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

Findings, from decompiling GameAssembly.dll in Ghidra (RVAs from .tools/il2cpp_dump/dump.cs, regenerate with task re:dump):
- CharacterMenu.TryInit (0x54A8E0) runs once, because it returns when characterButtons already exists. It sorts the CharacterData list with UnlockableBase.CompareTo (0x418480), which orders by GetPrice() and then by sortingPriority; creates one MyButtonCharacter per entry under characterGridParent; and calls MyButtonCharacter.SetCharacter (0x552190) on each. It then appends placeholder buttons with null data, finds the button for the saved selected character, and subscribes OnSelectCharacter and OnConfirmCharacter to MyButtonCharacter.A_Select and A_Confirm.
- Pinning: the grid order follows price, not a display-order field. Reordering the existing buttons' sibling indices under characterGridParent after TryInit looks safer than changing CharacterData.sortingPriority, which every user of CompareTo (such as the unlocks shop) would also see. This is a suggestion, not yet tried.
- Greying: SetCharacter clears canUseCharacter (0xA0) and sets it only for an unlocked character. A locked character gets a black icon tint and a ??? name, and IsBlackedOutInCharacterSelectionScreen (0x3819E0) also shows unavailableOverlay (0x60). A character that needs buying shows requiresPurchaseOverlay (0x78) and its price. CharacterMenu.OnConfirmCharacter (0x549C90) refuses a button whose canUseCharacter is false: it passes cantUseCharacterReason (0xB0) and the button's position to a popup call and does not select. So after TryInit, set canUseCharacter to false, a reason string, a black icon tint and the overlay on every button except Calcium and Tony McZoom. The popup itself has not been seen in the running game.
- Not yet checked: where the confirmed character is stored. OnSelectCharacter (0x54A290) is the likely writer of CharacterMenu.selectedCharacter; confirm whether it also writes the saved Preferences.selectedCharacter, which must not change.

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
