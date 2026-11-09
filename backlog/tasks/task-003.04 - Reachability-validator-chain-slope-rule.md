---
id: TASK-003.04
title: Reachability validator (chain/slope rule)
status: Done
assignee: []
created_date: '2026-10-06 21:41'
updated_date: '2026-10-07 21:11'
labels:
  - level-editor
dependencies:
  - TASK-003.03
parent_task_id: TASK-003
priority: high
type: feature
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-003 first for full context, especially the AlexK maze-chain reference describing the reachability rule.

Implement a validator over `LevelState`'s tile grid (from TASK-003.03) that performs a BFS/graph search where a move from tile A to adjacent tile B is legal if: B's height equals A's height, OR B's height is exactly one more than A's height AND B has a slope facing the direction of that climb (or A has a slope facing away, depending on which tile "owns" the slope per the final TASK-002.03 runtime finding — if TASK-002.03 isn't done yet, implement against the most sensible interpretation and leave a clear TODO/comment to confirm against real game data once available).

The validator reports:

- The full set of tiles reachable from a given start tile (e.g. the spawn tile).
- Any tiles NOT reachable from the start (a level-design error the editor should flag — see TASK-005's validate overlay).
- Whether a specific target tile (e.g. a boss portal tile) is reachable from the start.

Test on hand-built grids (constructed directly as `LevelState` fixtures, no game or Unity needed):

- A flat grid: everything reachable.
- A single slope-assisted single-step climb: both tiles reachable from each other.
- A cliff (height difference > 1, no slope) between two regions: each region's tiles are mutually reachable, but the two regions are NOT reachable from each other — this is the deliberate "unreachable tiles" case the validator must catch.
- A case with a slope that fixes what would otherwise be an unreachable cliff.

TDD: write these grid fixtures and their expected reachability results as failing tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The validator computes the full set of tiles reachable from a given start tile via BFS/graph search over LevelState's tile grid
- [x] #2 A move between adjacent tiles is legal when height is equal, or differs by exactly 1 with a slope present in the climbing direction, per the chain/slope rule
- [x] #3 A flat-grid test case reports full reachability
- [x] #4 A cliff-without-slope test case correctly reports the two sides as mutually unreachable
- [x] #5 A cliff-with-slope test case correctly reports full reachability
- [x] #6 The validator reports whether a specific target tile (e.g. a boss portal) is reachable from a start tile
- [x] #7 A code comment or doc note flags the slope-ownership-direction assumption as pending confirmation against real runtime data if TASK-002.03 findings weren't yet available when this was implemented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
BFS over LevelState.Tiles in reachability_validator.cs. Chain/slope rule implemented as: equal-height neighbors always connected; 1-height-step neighbors connected only if the higher tile's SlopeDirection points downhill toward the lower one (an assumption, flagged with a TODO comment on ReachabilityValidator since TASK-002.03 didn't confirm slope ownership/direction semantics, only grid shape/spacing). ReachabilityResult exposes Reachable, Unreachable, and IsReachable(target).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added ReachabilityValidator.Validate(LevelState, start) — BFS over the tile grid per the chain/slope rule (equal height always connects; a 1-step height difference connects only via a slope on the higher tile pointing downhill toward the lower one). Returns a ReachabilityResult with the full Reachable set, Unreachable tiles, and IsReachable(target) for spawn-to-boss-portal-style checks.

Slope ownership/direction is flagged as an unconfirmed assumption via a TODO comment on the class, per the task's AC#7 — TASK-002.03 confirmed grid shape/spacing but not slope semantics.

TDD: tests/MegabonkLevels.Tests/reachability_validator_tests.cs written first (confirmed red against a stub file), covering a flat grid, a slope-assisted climb, a cliff with no slope (mutually unreachable regions), a cliff fixed by chained slopes, boss-portal-reachable and -unreachable cases, and the start-tile-absent error path. Full suite: 65/65 passing. docs/level-format.md updated with a new section.
<!-- SECTION:FINAL_SUMMARY:END -->
