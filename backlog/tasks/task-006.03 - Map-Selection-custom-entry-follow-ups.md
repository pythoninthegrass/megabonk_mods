---
id: TASK-006.03
title: Map Selection custom entry follow-ups
status: Done
assignee: []
created_date: '2026-10-29T18:30:00Z'
updated_date: '2026-11-01T01:33:00Z'
labels:
  - level-editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/map_selection_patch.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - src/MegabonkLevels.Mod/character_screen_patch.cs
documentation:
  - docs/development.md
parent_task_id: TASK-006
priority: low
type: bug
ordinal: 118000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-006 and TASK-006.01 first. Two known gaps remain on the custom Map Selection entry, see "Map Selection entries" in docs/development.md.

1. Backing out of Map Selection (or Character Selection) after Confirm holds a level, but the held load is only cleared by the next native Confirm. Backing out should call LevelLoaderPatch.CancelAwaitingCharacter() and CharacterScreenPatch.SetRestricted(false).
2. The right-hand detail panel (MapStatsWindow, MapStatsInfoUi) still shows the base map's runs, highscore and speedrun for a custom entry, because the entry carries that map's MapData. Decide whether it shows nothing or level text.

Code: src/MegabonkLevels.Mod/map_selection_patch.cs, level_loader_patch.cs, character_screen_patch.cs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Backing out of Map Selection or Character Selection after a custom level is held cancels the held load and lifts the character restriction, so the next native map starts unrestricted
- [x] #2 For a custom entry the detail panel no longer shows the base map's runs, highscore or speedrun
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
1. Verify native back/confirm lifecycle before choosing cancellation hooks; preserve legitimate character-to-map transitions and successful starts.
2. Write tests first for cancellation state/decision logic, then wire menu patches to cancel held loads and restore character restrictions on back-out.
3. Blank only MapStatsInfoUi.t_mapRuns, t_highscore and t_fastestTime for custom selections; preserve all other detail content and native stats.
4. Run focused tests, task check, build and live verification where available; update docs and commit scoped changes.

Native GameAssembly inspection confirms MainMenu.GoToMapSelection activates tabMaps before disabling the character tab. Use CharacterMenu.OnDisable with a map-tab-active exemption (no confirm call-stack flags); MapSelectionUi.OnDisable cancels only an outstanding hold/restriction. MapStatsInfoUi.SetConfig refreshes texts each call, so a postfix can blank the three fields and native selection repopulates them. No component lookup is needed: postfix receives __instance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User decision: strictly blank the three stats (runs, highscore, speedrun); leave name, specs, tier and icons unchanged.

Tests written first: MenuBackoutTests failed to compile because MenuBackout did not exist; implemented the helper and menu hooks afterward. Final task check passed: 1549 C# tests, 900 Python tests, build/deploy, markdownlint and Ruff.

Live Wine checks using OS-level mouse/Escape input: Warehouse selection blanked only the three stat values; Forest selection restored 173 Runs, 5,226 highscore and 04:35.9 speedrun. Evidence: .tools/evidence/megabonk-1793496568514843000.png (custom) and megabonk-1793496576630268000.png (native restored). Labels/name/tier/icons preserved.

With MEGABONK_DEV=false, loaded thps into a held restricted setup. Character Confirm -> maps preserved hold (no cancellation log). Clicking map X cancelled the held load at 20:30:32.209, restored saved TonyMcZoom and stock grid (megabonk-1793496634468693000.png). Holding again and pressing Escape from characters cancelled at 20:30:41.531 (megabonk-1793496643997192000.png). Next normal menu start logged CustomLevelState IsActive=False and native Forest StartNewMap at 20:30:53, not a held custom run. Successful native menu closure did not cancel startup.

At user's request, relaunched Warehouse through the harness afterward; kill floor armed, 1241 edits loaded, spawnsOff=false, invulnerable=false. Left in editor mode (frozen) without further game interaction. Honcho unavailable in this session.

Implementation committed as 380174b (fix: cancel abandoned custom loads and hide base map records).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Cancelled held custom-load setup and restored character restrictions when backing out of either selection screen, while preserving character-to-map navigation. Blanked only custom entries' runs/highscore/speedrun values after SetConfig; native selections restore their own records. Added test-first cancellation policy coverage and updated development docs. Live checks verified both back-outs, forward transition, native start and custom/native stat switching. task check passes (1549 C# and 900 Python tests, build and lint).
<!-- SECTION:FINAL_SUMMARY:END -->
