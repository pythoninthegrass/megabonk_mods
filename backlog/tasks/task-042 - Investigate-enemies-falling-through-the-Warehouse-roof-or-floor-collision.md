---
id: TASK-042
title: Investigate enemies falling through the Warehouse roof or floor collision
status: To Do
assignee: []
created_date: '2026-11-05 19:44'
updated_date: '2026-11-06 01:07'
labels:
  - thps
  - collision
dependencies: []
references:
  - >-
    backlog/tasks/task-032.06 -
    Port-the-THPS-Warehouse-to-a-from-scratch-level.md
  - docs/thps-warehouse-layout.md
priority: medium
ordinal: 162000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Seen on a shipped Warehouse run (levels/thps.mblevel.json at 08a1847) after TASK-032.06: six Enemy1 reached the kill floor within 0.25 s at 13:34:07, about 42 s after a boss summon, at xz (136 to 166, -25 to 38), y -32 to -41 (KillFloor log lines, 'fell to ... killing'). That area is inside the arena footprint (x 21-180, z -122 to 122), so they dropped through something rather than off an edge. The player saw enemies standing on the Warehouse roof, and no hole in the floor.

Likely pre-existing rather than a port regression: the port removed only generated tiles, props and the boss move, and the object.place edits are identical to the pre-port set. There is no pre-port log of the same event to compare against.

Find out whether the mesh's roof or floor collision (WarehouseCollision) has gaps around x 135-165, z -25 to 38, for example by dropping test points through the mesh with warehouse_surface.drop and by reading collider bounds in the running game with query_objects. Then decide whether to fix the collision, add a catch, or leave it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The cause of the 13:34:07 group fall is identified, or ruled out as not reproducible, with the evidence recorded in the task
- [x] #2 If a collision gap exists, its extent is recorded and a fix or an explicit decision to leave it is made
- [ ] #3 A shipped Warehouse run with enemies on the roof and floor shows no enemies reaching the kill floor through the arena footprint, verified in the running game
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Static analysis: drop a grid of test points over x 130-170, z -30 to 45 through warehouse.obj with scripts/warehouse_surface.py (collision mesh after window-face removal, and render mesh); report columns with no upward-facing face or a surface far below expected. Write the gap finder test-first in tests/test_warehouse_surface.py if it is testable logic.
2. Runtime check locally under Wine via the megabonk MCP: relaunch, load levels/thps.mblevel.json, editor on; query_objects for WarehouseCollision bounds; teleport drops onto suspect spots; reproduce the group fall by summoning the boss with spawns on and watching KillFloor log lines. Check roof drop-through first (ground checks ignore back faces, roof is down-facing quads).
3. Decide: fix collision (ThpsPack.cs or roof builder), add a catch, or leave it. Record gap extent and evidence in the task; confirm the choice with Lance before changing anything.
4. Verify AC #3 in a shipped Warehouse run with enemies on roof and floor: no KillFloor 'killing' lines inside the arena footprint.
5. Close out: update docs, task check, one conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Static scan (2026-11-05): warehouse_triangles() from .tools/thps1/warehouse/warehouse.obj via build_thps_level placement, 0.5 unit grid over x 130-170, z -30 to 45 (6,000+ columns): every column has an upward-facing face; no gap in the source floor mesh. Sample columns: (150,0) floor y 0.5; (160,28) stacked boss-box faces with a pipe floor at -4.93. The scan uses the pre-pack mesh, so it excludes the pack's window-face removal (only inside y 15-26 / y 27-38, so not the floor) and the generated roof. Runtime check next.

Runtime (2026-11-05, local CrossOver bottle, levels/thps.mblevel.json, MEGABONK_DEV): live collider 'Warehouse(Clone)' bounds centre (100, 8.08, 0), extents (79.16, 56.71, 124.13), i.e. the whole mesh, MeshCollider non-convex, enabled; the roof in this level is separate 'added-roof-panel-*' and 'piece-*roof*' colliders, not one generated roof. KillFloor armed at y=-35 (catch floor -60).

Repro attempts: boss summoned from (165,18,26) with spawns on and invulnerable on. Run 1: boss (redirected to (126,15,75)) killed the player with invulnerable on, no KillFloor lines. Run 2: boss killed with kill_enemies bosses 3 s after summon, then about 4:00 game time and 173 kills with the player in the glass box and then on the main half pipe: no 'KillFloor ... fell/killing' lines. Not reproduced so far. Limits: level-ups freeze the run every 30-60 s (needs dismiss_offers + resume), so the game time covered is short, and the boss was killed early, unlike the original run (enemies fell ~42 s after a boss that was alive). Player stood in the box for most of run 2, so enemy traffic over the pipe and roof was not exercised.

Option 2 (2026-11-05): added warehouse_surface.unity_mesh_triangles and ground_gaps (tests first in tests/test_warehouse_surface.py; the degenerate-triangle case failed first, then passed). Ran them on unity/pack-authoring/Assets/Thps/WarehouseCollision.asset (world = vertex * 79.2 + (100, 0.5, 0)), arena footprint x 21-179, z -124 to 124, 1 unit step: 4,171 uncovered points in two regions, x 22-39 / z -123 to 2 and x 22-79 / z 106-123. Zero uncovered points over x 130-170, z -30 to 45. All asset gaps are also gaps in the unpacked OBJ mesh; the pack covers 563 more points than the OBJ. So the mesh has no hole under the half pipe or boss box, and the 13:34:07 fall is not explained by collision.

Decision: with the runtime repro also negative (about 4:00 game time, 173 kills), the group fall is ruled out as not reproducible (AC #1). No collision gap in the reported area, so no fix; the two uncovered regions are recorded in docs/asset-bundles.md and left alone (AC #2). Not established: whether enemies can reach those regions (the kill floor handles it if they do). AC #3 left unchecked: the run did not put enemies on the roof and the boss was killed early, so it does not meet the criterion as written. DoD #4 (commit) pending.

Longer soak (2026-11-06, local CrossOver bottle, levels/thps.mblevel.json, spawns on, invulnerable on): a boss left alive killed the player within 23 s despite invulnerable (it spawned at (153, 20, -31) beside the pipe), so the boss was killed about 40 s after the summon, matching the original timing. The run then continued to a full stage, HUD 10:25 elapsed, player level 20, 1,212 kills, final swarm active, with the player moved between (150, 6, 0), (140, 6, 20), (150, 6, -20), (155, 6, 30) and wherever the crowd pushed it (up to y 39 on the start slope and x 178 on the east wall). Latest.log has no 'KillFloor ... fell/killing' line for the whole run, only the armed line. Enemies were seen up to y 46 along the walls; none were confirmed standing on the roof, so the roof half of AC #3 is not shown, and a boss left alive was not tested because it kills the player.

Code and docs committed as 7df7418 (feat(warehouse): find ground gaps in the collision mesh).
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
