---
id: TASK-004.12
title: Pick Calcium or Tony McZoom when a custom level loads
status: To Do
assignee: []
created_date: '2026-10-28T21:02:00Z'
labels:
  - level-editor
dependencies:
  - TASK-004.07
documentation:
  - docs/development.md
  - src/MegabonkLevels.Mod/character_override.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
parent_task_id: TASK-004
priority: medium
type: feature
ordinal: 112000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-004.07 forces Tony McZoom on every mod-loaded level (CharacterOverride.TryApply sets CharacterMenu.selectedCharacter to 13 in LevelLoaderPatch.LoadAndStart). Replace the forced choice with a player select shown when a custom level loads, offering Calcium (the skateboarder, ECharacter.Calcium = 1) and Tony McZoom (ECharacter.TonyMcZoom = 13).

Context for a fresh implementer: ECharacter values are in .tools/il2cpp_dump/dump.cs (regenerate with task re:dump). Research whether Calcium has a skateboard skin or variant and how it is selected. Preferences.selectedCharacter is the saved setting and must not be overwritten. Unattended harness loads must not block on the picker, so they need a default (Tony McZoom) or a harness argument that names the character.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A picker offering Calcium and Tony McZoom appears when a level loads through the mod, and the run starts as the chosen character, confirmed by a harness screenshot of each
- [ ] #2 The harness load command can name the character or defaults to Tony McZoom without blocking on the picker
- [ ] #3 The player's saved character preference is unchanged after a mod-loaded run
- [ ] #4 How Calcium's skateboard look is applied is documented in docs/development.md
- [ ] #5 Any pure logic added is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
