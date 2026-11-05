---
id: TASK-042
title: Investigate enemies falling through the Warehouse roof or floor collision
status: To Do
assignee: []
created_date: '2026-11-05 19:44'
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
- [ ] #1 The cause of the 13:34:07 group fall is identified, or ruled out as not reproducible, with the evidence recorded in the task
- [ ] #2 If a collision gap exists, its extent is recorded and a fix or an explicit decision to leave it is made
- [ ] #3 A shipped Warehouse run with enemies on the roof and floor shows no enemies reaching the kill floor through the arena footprint, verified in the running game
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
