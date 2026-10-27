---
id: TASK-018.03
title: Save and list custom levels through harness commands
status: To Do
assignee: []
created_date: '2026-10-27T07:23:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
documentation:
  - docs/development.md
parent_task_id: TASK-018
priority: medium
type: enhancement
ordinal: 78000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The editor's Save is reached via an injected click, and reloading a saved level needs a hand-written harness command file whose path must be known. Add harness commands `save_level(level?)` (invokes the editor save, optionally naming the target level) and `list_levels` (returns the saved custom-level files). This makes the save/reload loop verifiable via typed commands instead of clicks + disk reads, and removes the need to know the save path. Mod-side; verify in the real game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `save_level` saves the current editor level, optionally to a named level file, and returns the result.
- [ ] #2 `list_levels` returns the saved custom-level files.
- [ ] #3 Verified in the real game: edit, save_level, list_levels shows the file, reload it.
- [ ] #4 docs/development.md documents the commands; task check passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
