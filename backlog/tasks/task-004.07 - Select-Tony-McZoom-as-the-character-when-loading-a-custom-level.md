---
id: TASK-004.07
title: Select Tony McZoom as the character when loading a custom level
status: Done
assignee:
  - Claude
created_date: '2026-10-08 02:39'
updated_date: '2026-10-29 06:22'
labels:
  - level-editor
dependencies:
  - TASK-004.06
modified_files:
  - src/MegabonkLevels.Mod/character_override.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - tests/MegabonkLevels.Tests/character_override_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - docs/development.md
parent_task_id: TASK-004
priority: medium
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A level started through the mod (the F6 key or the dev harness `load-level` command, both via LevelLoaderPatch.LoadAndStart) always spawns the default hazmat character, because the RunConfig it builds carries no character choice. Unattended runs against a custom level last longer with Tony McZoom, so the loaded run should use him by default.

Context for a fresh implementer: the game's ECharacter enum has TonyMcZoom = 13 (see `.tools/il2cpp_dump/dump.cs`, regenerate with `task re:dump` if absent). `CharacterMenu.selectedCharacter` is a public static ECharacter and is the likely hook; whether the player spawn reads it is unconfirmed. `Preferences.selectedCharacter` is the player's saved setting and must not be overwritten. The dev harness (docs/development.md, scripts/run.py) can load a level and capture a frame to confirm which character spawned.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Loading a level through the mod starts the run as Tony McZoom, confirmed by a harness screenshot of the running scene
- [x] #2 The player's saved character preference is unchanged after a mod-loaded run
- [x] #3 If the character cannot be applied, the loader logs a warning and the run still starts with the game's default character
- [x] #4 The mechanism found (which field or call the spawn reads) is documented in docs/level-format.md or docs/development.md
- [x] #5 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add pure helper `CharacterOverride` (src/MegabonkLevels.Mod/character_override.cs, no Il2Cpp refs so the test project can compile it): `TonyMcZoomId = 13` and `TryApply(Action<int> setSelected)` returning a warning string or null (catches exceptions from the setter).
2. Tests first (tests/MegabonkLevels.Tests/character_override_tests.cs, linked in the csproj): id value, setter receives 13, setter exception yields a warning and does not throw. Run to confirm failure, then implement.
3. In LevelLoaderPatch.LoadAndStart, before StartNewMap, call TryApply with a setter that assigns CharacterMenu.selectedCharacter; log the warning if any. Never touch Preferences.selectedCharacter.
4. Verify on CrossOver with the harness (run.py cycle) and read the screenshot. If the static is not what the spawn reads, find and hook the real read, then update this plan.
5. Confirm the saved preference is unchanged after the run (compare save/prefs before and after).
6. Document the mechanism in docs/development.md. Run task check. Commit with a conventional message, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified on CrossOver: harness load-level of levels/example-forest.mblevel.json spawned a human character on a hoverboard while the saved selectedCharacter is Fox. Saved config.json unchanged after the run. No control run without the override was done; the saved-vs-spawned difference is the evidence. AC #3 (warning path) is covered by the unit test for a throwing setter, not exercised live.

Lance tested manually after the change and confirmed Tony McZoom spawns as expected, which supersedes the missing control run noted above.

Superseded by TASK-004.12: the forced Tony McZoom now applies only with MEGABONK_DEV=true; otherwise the player picks Calcium or Tony McZoom on the game's Character Selection screen. See 'Character selection' in docs/development.md.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Mod-loaded runs now start as Tony McZoom. LevelLoaderPatch.LoadAndStart sets the static CharacterMenu.selectedCharacter (13) before MapController.StartNewMap, via the unit-tested CharacterOverride.TryApply, which returns a warning (logged by the loader) if the assignment throws. Preferences.selectedCharacter is untouched; the saved config.json still reads Fox after a run. Mechanism documented in docs/development.md.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
