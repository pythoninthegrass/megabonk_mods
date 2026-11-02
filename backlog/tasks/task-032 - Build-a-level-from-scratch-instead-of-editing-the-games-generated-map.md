---
id: TASK-032
title: Build a level from scratch instead of editing the game's generated map
status: To Do
assignee: []
created_date: '2026-11-02T04:32:00Z'
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
- [ ] #1 A from-scratch level file loads with none of the baseline map's generated tiles, props or interactables present
- [ ] #2 The file authors the full tile grid (heights and slopes) plus the spawn, boss spawner and portal placement
- [ ] #3 Reachability validation and the kill floor work for a from-scratch level, with no baseline-derived assumptions
- [ ] #4 Existing edit-over-baseline levels keep loading unchanged (backward compatible)
- [ ] #5 The editor can create and edit a new from-scratch level
- [ ] #6 Verified in game end to end: a minimal from-scratch level loads, is playable and passes validation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
