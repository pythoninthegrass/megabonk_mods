---
id: TASK-012
title: >-
  Fix NullReferenceException in EditorTileTools.Tick when a level is loaded
  during editor mode
status: To Do
assignee: []
created_date: '2026-10-23T00:52:00Z'
labels:
  - editor
  - dev-harness
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_mode.cs
  - scripts/run.py
priority: low
type: bug
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while checking TASK-010.06 against the real game (plain Wine, macOS). Sending `load` (MCP `load` tool or `run.py load`) to a running game that is already in editor mode logs four `Il2CppInterop.Runtime.Il2CppException: System.NullReferenceException` errors from `MegabonkLevels.EditorMode.Tick` (editor_mode.cs:48, which is the `EditorTileTools.Tick()` call or an inlined frame under it), about 40 ms apart.

Sequence in `MelonLoader/Latest.log`: `DevHarness: load-level`, `EditorMode: re-enter requested after level load`, `EditorMode: exited`, `EditorMode: entered`, then the four errors, then `KillFloor: armed`. The errors stop once the level finishes loading and the game stays usable (state afterwards: editor on, frozen, level loaded), so the editor appears to re-enter and tick before the reloaded level's tile data exists.

Not reproduced on the first load from `relaunch` (fresh process): zero errors. `docs/development.md` and AGENTS.md already say to use `relaunch` instead of a second `load`; this task is about the mod not throwing, not about changing that guidance.

Open question: confirm which call at line 48 actually throws (the Il2Cpp stack has no managed frames below `EditorMode.Tick`) before choosing the fix, for example deferring the re-enter until the level reports loaded versus guarding the tool's tick against a missing tile grid.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A test or log-based check reproduces the errors by sending load to a game already in editor mode, and the cause is identified
- [ ] #2 Loading a level while in editor mode logs no NullReferenceException and ends with the editor on, frozen and the kill floor armed
- [ ] #3 No change to the first-load path from relaunch
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
