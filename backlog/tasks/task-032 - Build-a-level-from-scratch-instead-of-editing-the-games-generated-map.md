---
id: TASK-032
title: Build a level from scratch instead of editing the game's generated map
status: Done
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-05T20:45:00Z'
labels: []
dependencies: []
priority: high
type: feature
ordinal: 139000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today a custom level is an edit stack over the game's own generated baseline map: the game generates a full map, the mod tears it down and applies edits on top (the Warehouse needs 1241 edits), and tile ops replay over the generated grid, never an empty one (docs/level-format.md). That model caps authoring: a level can only ever be a perturbation of a stock map, load time grows with edit count, and leftover baseline content (spawn resets, baseline-map flashes — see TASK-027.01) keeps biting. Let a level declare itself from-scratch: the file authors the whole tile grid and objects, nothing is generated and torn down, and the editor can start a new blank level. This pairs naturally with cross-map palette access (a from-scratch author wants every kit available).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A from-scratch level file loads with none of the baseline map's generated tiles, props or interactables present
- [x] #2 The file authors the full tile grid (heights and slopes) plus the spawn, boss spawner and portal placement
- [x] #3 Reachability validation and the kill floor work for a from-scratch level, with no baseline-derived assumptions
- [x] #4 Existing edit-over-baseline levels keep loading unchanged (backward compatible)
- [x] #5 The editor can create and edit a new from-scratch level
- [x] #6 Verified in game end to end: a minimal from-scratch level loads, is playable and passes validation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Levels can now declare themselves from-scratch: the file authors the whole tile grid, spawn and boss spawner, the runtime builds that grid instead of the game's generated map, validation and the kill floor work without baseline assumptions, and the editor can create and save a new blank level. The THPS Warehouse is ported to a from-scratch level. TASK-032.07 verified it end to end in the running game: a minimal level loads with no stock content, the boss spawner and boss kill work, a restart returns the player to the authored spawn, and generated-baseline levels (example-forest) load as before. Limits: Validate was confirmed only as a log-only result because the editor status line's second line is clipped, and the boss portal could not be exercised because tier 1 levels open none. Follow-ups TASK-032.08 (harness verbs for the death screen's Confirm and Restart) and TASK-032.09 (required type on the MCP interact tool) remain open.
<!-- SECTION:FINAL_SUMMARY:END -->
