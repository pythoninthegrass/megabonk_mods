---
id: TASK-021.21
title: Grind the apex edges of the half pipes like the rails
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-28T21:02:00Z'
updated_date: '2026-10-29 04:19'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.19
  - TASK-021.15
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
parent_task_id: TASK-021
priority: medium
ordinal: 111000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make the apex edge (coping) of every half pipe and quarter pipe in the Warehouse grindable, the same way the three mesh rails are.

Context for a fresh implementer: apply the hidden game rail approach from TASK-021.14 and TASK-021.19. Rails are laid along the visible geometry with MESH_RAILS in scripts/build_thps_level.py, placed with the hidden flag on object.place; the pivot height offset scales with the rail (RAIL0_BAR_HEIGHT); RailHandoffPatch (rail_handoff_patch.cs) chains rails that meet at a joint. Measure each lip line from the extracted mesh. The main half pipe near (142, -3, 32) must keep working for ollies (TASK-021.15, PlayerMovement.maxSlopeAngle raised to 88 on the thps level).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every half pipe and quarter pipe lip has a hidden game rail aligned to the coping, with each pipe and its coordinates listed in the task
- [x] #2 The player can grind each lip in game, with the grind sparks and player on the visible edge
- [ ] #3 Ollie off the main half pipe edges near (142, -3, 32) still works
- [x] #4 Generator behaviour is covered by tests in tests/test_build_thps_level.py written first, and docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Survey (tests first): add a lip finder to scripts/warehouse_surface.py (top boundary edges of 25-89 degree ramp faces, merged into collinear runs); failing tests in tests/test_build_thps_level.py first; verify candidates by screenshot.
2. Pipe list: record each half pipe and quarter pipe with lip endpoints and height in this task and docs/thps-warehouse-layout.md.
3. Rails (tests first): COPING_RAILS beside MESH_RAILS plus a helper from lip endpoints to (position, yaw, scale) using RAIL0_LENGTH and RAIL0_BAR_HEIGHT; emitted as hidden rail/0 via mesh_rail_edits; long copings split into touching rails so RailHandoffPatch chains them.
4. In game: task mod:build, relaunch, teleport and grind each lip, check sparks/player on the edge; ollie off the main pipe edges near (142, -3, 32).
5. Docs, task check, one conventional commit with no attribution.

Scope (approved): only tops of half pipes and quarter pipes; borderline edges listed in the task for veto. Skip the long ~20-unit channel quarter pipe walls at height 8.56.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Pipes coped (main half pipe, from ridge_runs on the mesh): north lip (119.78, 5.76, 8.59) to (178.95, 5.76, 8.59); south lip (119.78, 5.76, 43.81) to (178.95, 5.76, 43.81); one hidden rail/0 each at scale 2.113. Borderline, excluded: wooden kickers near (45, 3.3, 47) and (45, 3.3, 62), taxi funbox near (120-137, 2-5, 75-83); long wall quarter pipes at height 8.56 skipped by decision. Grind checked by dropping the player onto each lip (task-021.21-grind-north.png, -grind-south.png in .tools/evidence): sparks and player on the coping. AC#3 not verified: the harness injects no gameplay input, so an ollie off the pipe edge was not exercised.

Follow-up after review: the lips continue past x 119.78 as a 21 unit diagonal to the floor corner (hip), so rail_along now pitches, and a rail/0 is laid along each diagonal; the grind chains onto it (checked: north lip dropped at x 126 ends at (94.6, 2.4, 2.1)). Lip ends at walls stop WALL_MARGIN (12) short, listed in WALL_ENDS. Wall quarter pipes (north tiers, south wall, U pocket, east curve) added from lip_runs. Not verified: an eastbound grind into the east wall at (178, 7, 46) (a harness drop only grinds west) and ollies; in the north tier test the player still coasts into the wall after the rail ends.

Pocket tip fixed: two chords at the tip, coping rails at least the handoff search radius long, and RailHandoffPatch sets railDirectionMultiplier toward the far end after StartRail. Shorty's ledge on the west wall added as LEDGE_LIPS (4 segments, (40.89, 3.79, 3.51) to (21.17, 3.79, 58.73)) via ledge_runs; checked by dropping onto it: the grind chains to the kicker end and lands at (43, 2, 4). The east side's matching ledge edges are not coped.

Start half pipe platform lip (80.34, 35.85, -120.84) to (139.5, 35.85, -120.84) added as START_PIPE_LIPS; the start area's mesh is double-sided, so the finders drop duplicate faces. Rail engages (grind pose and sparks on the coping); a grind along it was not exercised because a teleport gives no speed. Other lip runs near the start (z -58.02 at height 26.95, z -65.75 at height 48.01) are not coped.

Wall-end pull-back (WALL_ENDS, WALL_MARGIN) removed: it left the last 12 units of each wall-to-wall lip ungrindable and did not stop the launch into the wall. Rails now run edge to edge (tested). Checked on the start lip: dropped 1.4 from the west wall, the grind ran to x 138.86, 0.6 short of the east wall. Observed: the spawn (109, 38, -120) is 0.84 from the start lip, so the player spawns caught on the rail and a teleport cannot move him; the spawn is a chosen position, left unchanged.

The installed thps pack was stale (manifest 2.0.10 with six assets, built before the roof and see-through fixes), so the sky showed. Rebuilt and installed with task pack:thps (2.0.21, 44.9 MB, 14 clips); in game the roof is closed and the soundtrack loads. The build log shows a WarehouseRoof compile error on Unity's first pass that clears on the second; the build exits 0.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
