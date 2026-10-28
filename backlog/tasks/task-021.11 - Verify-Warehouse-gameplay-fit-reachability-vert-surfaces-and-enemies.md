---
id: TASK-021.11
title: 'Verify Warehouse gameplay fit: reachability, vert surfaces and enemies'
status: To Do
assignee: []
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28 02:41'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.09
  - TASK-021.10
documentation:
  - docs/thps-warehouse-layout.md
  - docs/development.md
parent_task_id: TASK-021
priority: medium
ordinal: 99000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The original ramps go vertical but the player cannot climb a face past 45 degrees (PlayerMovement.maxSlopeAngle), and the existing reachability test (ThpsLevelTests) is tile-based so it says nothing about the imported mesh. After the mesh import and item anchoring, check that every collectible can actually be reached and that the level plays as a Megabonk run. Depends on the mesh import and item anchoring tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every collectible is reached by the player in game, or the unreachable ones are listed with the surface that blocks them
- [ ] #2 For each item reachable only over a vert surface, a ramp or JumpPad is added or the item is listed as an approved deviation
- [ ] #3 ThpsLevelTests still passes, and a per-item teleport-and-settle check through the MCP server is recorded
- [ ] #4 Enemies spawn and path inside the shell in a run with spawns on
- [ ] #5 Unverified routes, such as the corridor tape, are listed in docs/thps-warehouse-layout.md as open questions
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
