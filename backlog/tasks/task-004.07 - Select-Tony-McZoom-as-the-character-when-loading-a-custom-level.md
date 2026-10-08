---
id: TASK-004.07
title: Select Tony McZoom as the character when loading a custom level
status: To Do
assignee: []
created_date: '2026-10-08 02:39'
labels:
  - level-editor
dependencies:
  - TASK-004.06
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
- [ ] #1 Loading a level through the mod starts the run as Tony McZoom, confirmed by a harness screenshot of the running scene
- [ ] #2 The player's saved character preference is unchanged after a mod-loaded run
- [ ] #3 If the character cannot be applied, the loader logs a warning and the run still starts with the game's default character
- [ ] #4 The mechanism found (which field or call the spawn reads) is documented in docs/level-format.md or docs/development.md
- [ ] #5 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
