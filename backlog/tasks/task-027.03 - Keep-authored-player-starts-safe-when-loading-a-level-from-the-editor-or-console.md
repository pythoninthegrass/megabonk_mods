---
id: TASK-027.03
title: >-
  Keep authored player starts safe when loading a level from the editor or
  console
status: In Progress
assignee: []
created_date: '2026-11-09 01:50'
updated_date: '2026-11-09 01:54'
labels:
  - startup
  - editor
  - thps-warehouse
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_load_plan.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/startup_cover.cs
  - levels/thps.mblevel.json
documentation:
  - docs/development.md
modified_files:
  - src/MegabonkLevels.Mod/editor_load_plan.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - tests/MegabonkLevels.Tests/editor_load_plan_tests.cs
  - docs/development.md
parent_task_id: TASK-027
priority: high
ordinal: 205000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After a Forest harness run, console level.load thps took the editor in-place path, replayed 1294 edits and rebuilt collisions but did not relocate the player to the loaded authored start. Exiting editor then killed Tony below the map at y=-68.30944. Installed UserData/Levels/thps.mblevel.json is an old schema-3 generated-baseline level; repository levels/thps.mblevel.json is schema 4 baseline none. The user approved backing up/refreshing the installed file, testing a fresh THPS launch, and fixing unsafe in-place loading separately from the completed BepInEx harness migration. Preserve unrelated installed levels and the reversible loader setup. No harness-wide rewrite or distribution packaging work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Loading a level with an authored player start through the editor/console does not leave the player at the previous level position; safe startup placement completes before play resumes.
- [x] #2 Regression tests cover legacy generated levels with authored starts, same-start reloads and existing from-scratch/generated load policies.
- [x] #3 The stale installed THPS file is backed up before refresh; a fresh launch of the current repository THPS is verified above the playable floor without a fall-through death.
- [x] #4 The originally unsafe console load scenario is verified in-game, and developer documentation explains the load policy and installed-versus-repository level distinction.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Maintainer approved refreshing/testing THPS and a scoped fix for unsafe in-place level loading.
1. Check branch/working tree. Back up installed legacy THPS byte-for-byte outside UserData/Levels, refresh only that installed file from repository THPS and verify a fresh BepInEx launch/player floor placement with sparse state/log/screenshot evidence. Leave unrelated content untouched.
2. Write failing EditorLoadPlan tests for schema-3/generated authored-start loads, same-start reloads and mismatched generated baselines with authored start. Route authored-start loads through the existing FreshRun path, which already coordinates content/portal readiness and editor reentry; preserve in-place behavior for compatible generated levels without a start and refusal for incompatible generated levels without a start. Avoid adding a second teleport/hold scheduler or refactoring the harness.
3. Build/relaunch, reproduce Forest -> legacy THPS console load using a temporary preserved legacy fixture, verify it now starts a new run and lands on the Warehouse floor. Also verify current installed schema-4 THPS console loading; remove only the temporary fixture created for this check. Never overwrite the user backup.
4. Document the explicit-load policy and installed-file resolution, run focused tests and task check, record root cause/evidence and commit conventionally. Preserve main/loader rollback and leave a safe editor for review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Original installed level preserved byte-for-byte at .tools/evidence/authored-load-20261109/thps-installed-original.mblevel.json (SHA256 b82246effd8dc22158037d598e072f4cb28f59732f9cf59ee461fae6404c8f18). Installed thps.mblevel.json refreshed from repository schema 4 baseline none, 48 edits, authored start [109,38,-116], killFloorY=-35. No other user levels modified. Fresh launch verified normal Warehouse rendering and playing state at [109,29.747574,-111.17714], no fall-through.

Regression tests written first: four expected failures for generated authored-start loads (schema 3/4), same-start reload and mismatched generated baseline. Fix is one policy condition: targets with PlayerStart use existing FreshRun path. No new teleport scheduler or harness refactor. Existing in-place generated/no-start and refusal policies retained. Removed obsolete all-loads-in-place comment. All 13 EditorLoadPlan cases pass; five additional cases total.

Real game after rebuild/relaunch: Forest -> temporary byte-identical legacy installed THPS via console while editor active returned loading rather than loaded, started new run, applied 1294 edits, completed exactly one authored placement and settled at [108.99999,29.747574,-111.17714] with editor=false/frozen=false. Console level.load thps then started current schema-4 from-scratch run, 48 edits, authored kill floor -35, one placement, same settled position. No KillFloor death lines or in-place loads in verification session. Screenshots: current-thps-fresh-playing.png, legacy-console-load-playing.png, current-thps-console-playing.png; console-load-verification.log retained beside them. Temporary legacy fixture removed only after verifying bytes still matched backup. Final game frozen in editor, invulnerable, spawns off, zero dirty edits.

task mod:build passed with 0 warnings/errors; task check passed (2786 C# tests, 1160 Python tests, installer checks and lint). Existing test-project nullable/xUnit and pytest fixture-scope warnings remain. Full check log at .tools/evidence/authored-load-20261109/task-check.log; git diff --check clean. Main and reversible BepInEx/MelonLoader files untouched.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
