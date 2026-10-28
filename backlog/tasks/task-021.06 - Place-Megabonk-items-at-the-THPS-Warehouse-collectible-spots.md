---
id: TASK-021.06
title: Place Megabonk items at the THPS Warehouse collectible spots
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-28 01:17'
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
ordinal: 92000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
THPS collectibles (five box piles, the letters S, K, A, T and E, the secret tape and three 100-point pickups) are not recreated as THPS pickups. Each is represented by a normal in-game Megabonk item, such as a chest or shrine, placed where the matching THPS item sits, so the level keeps the original's exploration incentives while staying a Megabonk level.

The collectible-to-item mapping and target positions come from the layout spec in TASK-021.03, which Lance has signed off. Items are placed in the level from TASK-021.04 through the `megabonk` MCP server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every collectible in the spec has its mapped in-game item at the specified position in levels/thps.mblevel.json
- [x] #2 The placed items are ordinary Megabonk objects that spawn and can be interacted with in a run
- [x] #3 Each item is verified in game through the MCP server, with a screenshot of its position
- [x] #4 Items that are meant to be reachable only by a trick, such as the secret room tape, are reachable by the player in game, or the unreachable ones are listed
- [x] #5 The reachability validator still passes after the placement
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/test_build_thps_level.py: all 14 spec collectibles placed once with the mapped catalog ID; none inside a structure footprint unless standing on top (Y = surface + ~4); all inside the arena and 10+ units from the player spawn. Confirm they fail.
2. Add a COLLECTIBLES table and collectible_edits() to scripts/build_thps_level.py, appended in build_level(). Approved deviations: R5 goes on the lane just south of the raised block at ground level; letter T moves to about (27, 59) on the flat between M4b and M6. Record deviations in docs/thps-warehouse-layout.md.
3. Extend ThpsLevelTests (.NET) so the reachability validator still passes; regenerate levels/thps.mblevel.json.
4. In game via MCP: relaunch, query_objects and screenshot each item, interact with one chest and one shrine, check reach of the corridor tape and elevated items by teleport and jump; list unreachable ones.
5. Update docs, task check, conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a COLLECTIBLES table and collectible_edits() to scripts/build_thps_level.py and regenerated levels/thps.mblevel.json (the task text said thps-warehouse; the file is thps). All 14 spec items are placed: 5 chests, 5 shrine catalog entries, 4 free chests, written test-first (7 new Python tests; task check passes, 1030 .NET tests including the reachability replay). Approved deviations, recorded in docs/thps-warehouse-layout.md: R5 on the west lane's low end, letter T at (27, 60.5) in the gap between M4b and M6, R4 and E moved onto the deck (E's spec position was off its edge), and every item stands on its surface instead of floating about 4 units above it. Verified in game via the MCP server: all 14 spawn at the logged positions, screenshots in .tools/evidence/task-021-06-*.png (gitignored), and the lane slope height matches the player's settled height. Caveats: forest/shrines/3 is the ShadyGuy merchant NPC, not a shrine; opening a chest needs the Interact key and gold, which the harness cannot send, so interaction is only shown by the chest price label appearing when the player stands at R5; the corridor tape at y 13 exceeds the 7.8 jump apex and its route (M6 lip, running jump across a 5 unit gap) is unverified because the harness can teleport but not move the player. Listed as unverified in the doc.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
