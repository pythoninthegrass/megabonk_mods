---
id: TASK-021.04
title: Build the THPS Warehouse geometry from existing assets through MCP
status: Done
assignee:
  - Claude
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27T23:00:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-021.03
documentation:
  - docs/development.md
  - docs/level-format.md
parent_task_id: TASK-021
priority: medium
type: feature
ordinal: 90000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
This is the first point where the warehouse becomes playable. Using the layout spec from TASK-021.03, an agent builds everything that existing Megabonk assets can express, driving the in-game editor through the `megabonk` MCP server (tools such as `relaunch`, `editor`, `key`, `mouse`, `click_widget`, `save_level`, `screenshot`; see "MCP server" in `docs/development.md`). Features the spec marks as needing a new asset are left for TASK-021.05 and may be stood in for by placeholders. The saved level file is the deliverable, so later tasks can open it and carry on.

Compare progress against the reference frames in `tools/thps_warehouse_frames/` (gitignored; see TASK-021.01 for how to regenerate them).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The level is saved as levels/thps.mblevel.json and loads through the harness load command
- [x] #2 Every structure the spec assigns to an existing asset is present at its specified grid position, with the documented deviations
- [x] #3 The reachability validator passes on the saved level
- [x] #4 Screenshots of the built level are compared side by side with the matching reference frames, and the differences are listed
- [x] #5 A run on the level starts and the player is not killed or stuck at spawn
- [x] #6 The level-building workflow and any editor limits found are documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built levels/thps.mblevel.json (named thps per Lance, not thps-warehouse) with a tested generator, scripts/build_thps_level.py, instead of clicking edits in the editor, per Lance's choice. The level is a 3x4 tile arena on Forest stage 0 wrapped by a raised ring, with a raised north-east block and two slope lanes, all generator clutter removed, the boss spawner moved into the arena, and three rails (rail/1 big rail, rail/0 ledge and high rails). It loads through the harness with 1143 edits applied cleanly, and a run starts with the player stable at spawn. Reachability is checked by an xUnit test over the saved file because the editor Validate button shows no result. Deviations documented in docs/thps-warehouse-layout.md: the block sits over the generator's spawn cell because moving the portal does not move the player, the dark pit is omitted, and the spec's crate was wrong (flat-tile prefabs are whole tiles with ruins). Ramps, decks, ledges and the rest remain for new assets. forest_custom.mblevel.json was verified unchanged by checksum. task check passes (293 Python tests plus the .NET tests).
<!-- SECTION:FINAL_SUMMARY:END -->
