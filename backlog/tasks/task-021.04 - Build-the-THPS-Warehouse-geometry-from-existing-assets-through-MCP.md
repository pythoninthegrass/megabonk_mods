---
id: TASK-021.04
title: Build the THPS Warehouse geometry from existing assets through MCP
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
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
- [ ] #1 The level is saved as levels/thps-warehouse.mblevel.json and loads through the harness load command
- [ ] #2 Every structure the spec assigns to an existing asset is present at its specified grid position
- [ ] #3 The reachability validator passes on the saved level
- [ ] #4 Screenshots of the built level are compared side by side with the matching reference frames, and the differences are listed
- [ ] #5 A run on the level starts and the player is not killed or stuck at spawn
- [ ] #6 The level-building workflow and any editor limits found are documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
