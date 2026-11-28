---
id: TASK-086.04.02
title: Verify the Mountain Pass map edges stop a player on all four sides
status: To Do
assignee: []
created_date: '2026-11-28 02:55'
labels:
  - level
  - kf1
dependencies: []
parent_task_id: TASK-086.04
priority: medium
ordinal: 313000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In the Killing Floor 1 Mountain Pass level, killFloorY is -72 at runtime and about 0.1 percent of the terrain (minimum -137) lies below it, so a fall can land on terrain instead of the kill floor. The stock Forest backdrop (a 960 by 960 mesh at the origin) sits underneath the map and is not part of it. One edge has been tried: a player teleported to [-340, 80, 0], 25 units past the west terrain edge, ended resting at [-317.6, 5.72, 20.5] and was not killed; x was clamped to -317.6, about 2 units beyond the terrain edge, so something solid stopped the lateral drift. Whether that was the perimeter wall (mesh.json carries a perimeter from level_geometry) or the Forest backdrop is not established, and no walking player has been tried. The terrain spans roughly plus or minus 315 units on x and z. Use the megabonk MCP harness (relaunch with the generated level, spawns off, teleport, state) and real movement input; see docs/development.md. The goal is evidence of what stops a player at each edge and a decision on whether a player can leave the intended map.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 For each of the four edges, the result of dropping a player from height beyond the edge is recorded: where it came to rest, and which collider stopped it
- [ ] #2 A player walking or hoverboarding into each edge is shown to stay inside the map, or the gap is recorded with the location
- [ ] #3 It is established whether any edge lets a player reach the kill floor or an area outside the intended map
- [ ] #4 Any gap found is fixed or filed with coordinates and a screenshot, and docs/kf1-mountain-pass.md records the edge behavior
- [ ] #5 Evidence screenshots and state readings are saved under .tools/evidence and named in the task notes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
