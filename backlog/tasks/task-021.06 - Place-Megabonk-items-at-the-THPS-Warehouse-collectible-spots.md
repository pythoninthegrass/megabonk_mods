---
id: TASK-021.06
title: Place Megabonk items at the THPS Warehouse collectible spots
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-021.03
  - TASK-021.04
documentation:
  - docs/level-format.md
parent_task_id: TASK-021
priority: medium
type: feature
ordinal: 92000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
THPS collectibles (five box piles, the letters S, K, A, T and E, the secret tape and three 100-point pickups) are not recreated as THPS pickups. Each is represented by a normal in-game Megabonk item, such as a chest or shrine, placed where the matching THPS item sits, so the level keeps the original's exploration incentives while staying a Megabonk level.

The collectible-to-item mapping and target positions come from the layout spec in TASK-021.03, which Lance has signed off. Items are placed in the level from TASK-021.04 through the `megabonk` MCP server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every collectible in the spec has its mapped in-game item at the specified position in levels/thps-warehouse.mblevel.json
- [ ] #2 The placed items are ordinary Megabonk objects that spawn and can be interacted with in a run
- [ ] #3 Each item is verified in game through the MCP server, with a screenshot of its position
- [ ] #4 Items that are meant to be reachable only by a trick, such as the secret room tape, are reachable by the player in game, or the unreachable ones are listed
- [ ] #5 The reachability validator still passes after the placement
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
