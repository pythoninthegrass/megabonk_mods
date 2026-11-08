---
id: DRAFT-003
title: >-
  Console conveniences: position bookmarks, teleport to camera, boss spawn and
  command scripts
status: Draft
assignee: []
created_date: '2026-11-08T07:55:00Z'
labels: []
dependencies:
  - TASK-054.02
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - .tools/il2cpp_dump/dump.cs
parent_task_id: TASK-054
priority: low
type: feature
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Proposed while planning the console and not yet confirmed by the maintainer, so it stays a Draft until approved. These are small quality-of-life verbs for level testing that neither run.py nor the mod offers:
- **`pos.save name` / `pos.goto name` / `pos.list`:** named teleport bookmarks, so a tester can return to a tricky jump or grind rail repeatedly. Today that means copying coordinates out of `state` by hand. Bookmarks could be per level.
- **`tp_camera`:** teleport the player to the editor's free-fly camera position. This is the natural "put me here" after scouting in the editor.
- **`enemies.spawn_boss`:** start the boss fight on demand. The dump has `FinalFightController.SpawnBoss()`; it is unverified and may depend on stage state.
- **`bat file`:** run a text file of console lines, as Fallout's `bat` does, from a fixed folder under `UserData`. Useful for repeatable test setups, such as god mode, spawns off, teleport and freeze.

All of these are gated behind MEGABONK_DEV except possibly `pos.*`. The maintainer decides the gating when approving.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Maintainer approves which verbs to build and their gating before the task leaves Draft
- [ ] #2 Each approved verb works in a live run (evidence: harness state, log lines or screenshots)
- [ ] #3 bat reports the line number and error of the first failing line and stops, and refuses paths outside its folder
- [ ] #4 Testable logic (bookmark storage, script parsing) has tests written first; each verb has a console binding test
- [ ] #5 docs/development.md documents the approved verbs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
