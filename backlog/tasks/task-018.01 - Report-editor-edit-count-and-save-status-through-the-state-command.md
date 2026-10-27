---
id: TASK-018.01
title: Report editor edit count and save status through the state command
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
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The `state` command returns editor tool, selection and palette count, but not the edit count or save status — the docs 'Not covered' section already says the edit stack is not reported. During TASK-016 AC#4, dirty/saved state had to be read from a screenshot and the log. Add an `edits` object to the state result with the current edit count, whether the level is dirty (unsaved edits) vs saved, the last saved level name, and the save status. This is a small mod-side change in the state command / editor_tile_tools.cs; verify in the real game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `state` reports the current edit count and whether the level is dirty (unsaved edits) or saved.
- [ ] #2 `state` reports the last saved level name and the save status.
- [ ] #3 Verified in the real game after `task mod:build` + `run.py relaunch`: edit a tile to make the level dirty, then Save, and confirm state reflects dirty then saved.
- [ ] #4 docs/development.md documents the new state fields; task check passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
