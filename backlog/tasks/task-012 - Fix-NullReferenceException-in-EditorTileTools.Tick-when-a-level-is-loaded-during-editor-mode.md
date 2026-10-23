---
id: TASK-012
title: >-
  Fix NullReferenceException in EditorTileTools.Tick when a level is loaded
  during editor mode
status: Done
assignee:
  - claude
created_date: '2026-10-23T00:52:00Z'
updated_date: '2026-10-23T02:10:00Z'
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
- [x] #1 A test or log-based check reproduces the errors by sending load to a game already in editor mode, and the cause is identified
- [x] #2 Loading a level while in editor mode logs no NullReferenceException and ends with the editor on, frozen and the kill floor armed
- [x] #3 No change to the first-load path from relaunch
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
1. Reproduced on the running game (relaunch, then a second `load`): four NullReferenceException from EditorMode.Tick line 48 between `EditorMode: entered` and the new generation's `LiveEdit: indexed`.
2. Suspected cause: LiveEditPatch._session survives until OnGenerationComplete, so while the reloaded level generates, FindTarget calls GroundCollider() -> `_session.TileGen.collider` on the destroyed old ProceduralTileGeneration (`?.` does not catch a Unity-destroyed object).
3. Fix: LiveEditPatch accessors read the session through a property that returns null once its TileGen is destroyed. No unit test is possible (Il2Cpp types are not referenced by the test project), so verify in game: relaunch, load, expect zero errors, editor on, frozen, kill floor armed; relaunch path unchanged.
4. Docs: note the behaviour in docs/development.md if a relevant section exists.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Cause confirmed by before/after in the running game: with the old DLL a second load logged 4 NullReferenceExceptions between `EditorMode: entered` and `LiveEdit: indexed`; with the guard, zero. LiveEditPatch._session survived until OnGenerationComplete, so FindTarget -> GroundCollider() read `TileGen.collider` on the destroyed old ProceduralTileGeneration.

No unit test: the guarded code depends on Il2Cpp types the test project does not reference. Verified in game instead.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
LiveEditPatch now reads its session through a LiveSession property that returns null once the session's tile generator is destroyed. Previously the stale session stayed until the next generation completed, and the editor's per-frame target lookup dereferenced the destroyed ProceduralTileGeneration, throwing four NullReferenceExceptions. Verified on the running game: relaunch then a second load logs no NullReferenceException (before the fix: four), ends with editor on, frozen, kill floor armed; the relaunch first-load path logs no new errors. `task check` passes. Docs updated in docs/development.md. No unit test (Il2Cpp-dependent code).
<!-- SECTION:FINAL_SUMMARY:END -->
