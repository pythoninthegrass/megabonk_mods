---
id: TASK-004.12
title: >-
  Pick Calcium or Tony McZoom on the game's character select screen for custom
  levels
status: Done
assignee:
  - Claude
created_date: '2026-10-28T21:02:00Z'
updated_date: '2026-10-29 06:22'
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
- [x] #1 The game's Character Selection screen shows Calcium and Tony McZoom pinned at the top left, with every other character greyed out and unselectable, when a custom level is being started
- [x] #2 Only Calcium and Tony McZoom can be confirmed, and the run starts as the chosen character, confirmed by a harness screenshot of each
- [x] #3 A normal (non-custom) run from the main menu still shows the stock character order with nothing greyed out
- [x] #4 With the dev flag on, a harness load or editor launch skips the screen, defaults to Tony McZoom and can name Calcium instead, without blocking
- [x] #5 The player's saved character preference is unchanged after a mod-loaded run
- [x] #6 How Calcium's skateboard look is applied is documented in docs/development.md
- [x] #7 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Decision: harness-only trigger now (option B). A harness command sets the "custom run pending" state and opens the character screen; TASK-006.01 later calls the same state setter.
2. Tests first (pure logic): CharacterOverride allowed set (Calcium=1, TonyMcZoom=13), default Tony, name-to-id parse; pin-order function (stock order in, Calcium/Tony first out); dev-flag resolver (off = show screens, on = Tony default, on + name = Calcium or Tony, anything else rejected).
3. Harmony postfix on CharacterMenu.TryInit, active only while a custom run is pending: move Calcium and Tony buttons to sibling indices 0 and 1 under characterGridParent; set canUseCharacter=false, cantUseCharacterReason, black icon tint and unavailableOverlay on all others. Restore the stock grid when the pending state clears.
4. Confirm OnSelectCharacter does not write Preferences.selectedCharacter; patch if it does.
5. Dev flag (MEGABONK_DEV via EnvFlag) plus optional character name: LoadAndStart skips the screen and sets selectedCharacter directly.
6. Harness command to enter the pending state; MCP tool and run.py wrapper.
7. Document the Calcium skateboard look and the character screen behaviour in docs/development.md; verify with harness screenshots of each character.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: CharacterScreenPatch (pin, grey out, rebuild navigation, focus Calcium, restore stock), held load swapped in through a StartNewMap prefix, MEGABONK_DEV flag with load-level character field, saved preference restored on run start. Option B chosen: harness-only trigger; TASK-006.01 should call CharacterScreenPatch.SetRestricted(true) and LevelLoaderPatch's held-load path.

Findings: the game derives keyboard and controller navigation from the private characterButtons list, not sibling order, so the list is reordered and SetupButtonNavigation re-run. OnConfirmCharacter saves the confirmed character to Preferences.selectedCharacter at once (config.json changed to TonyMcZoom), so it is put back with SaveManager.SaveConfig; verified by confirming Calcium with TonyMcZoom saved and reading config.json after quit. The map and tier chosen on the stock screens are discarded in favour of the level file. A title-screen controller hiccup on one launch was not reproduced.

The refusal tooltip flash came from the reason string set on greyed-out buttons; a stock locked character (Roberto) has none and shows no popup, so the reason is no longer set. AC #3 was confirmed by eye on a --no-level launch. Added run.py relaunch --no-level and MCP relaunch(no_level=true) to reach the main menu without a level.

Open: which asset carries Calcium's skateboard (CharacterData.prefab or a skin) is not traced; no mod code applies it.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The game's own Character Selection screen is now restricted to Calcium and Tony McZoom for custom runs, replacing the forced Tony McZoom of TASK-004.07.

What changed:
- CharacterScreenPatch pins Calcium and Tony McZoom first, greys out every other character the way a locked one appears (canUseCharacter false, black icon, unavailableOverlay, no reason string), reorders the game's characterButtons list and rebuilds navigation so keyboard and DS5 follow the grid, focuses Calcium explicitly, and restores the stock grid when the restriction ends.
- With MEGABONK_DEV unset, a harness load is held until a character is confirmed; a first-priority prefix on MapController.StartNewMap then swaps in the held level's RunConfig. The confirmed character's saved preference is put back with SaveManager.SaveConfig, since the game saves it on confirm.
- MEGABONK_DEV=true skips the screen: Tony McZoom by default, or the character named by the new load-level character field (run.py load/relaunch --character, MCP load character).
- New harness command character-screen on|off (run.py, MCP character_screen); run.py relaunch --no-level and MCP relaunch(no_level=true) stop at the main menu.
- Pure logic (allowed set, name parsing, grid order, dev-flag resolution, load command parsing) was written test first. Docs updated in docs/development.md, AGENTS.md and .env.example.

Verified: task check passes (1181 C# tests, 482 Python tests). In the running game: restricted grid, keyboard and DS5 navigation, confirming Calcium and Tony each starts the run as that character, saved preference unchanged after confirming a different character and quitting, dev flag with and without a named character, stock grid on a normal run, no tooltip on greyed-out characters.

Follow-ups: TASK-006.01 must call CharacterScreenPatch.SetRestricted(true) and the held-load path from its map selection entry. The asset carrying Calcium's skateboard was not traced. A title-screen controller hiccup on one launch was not reproduced.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
