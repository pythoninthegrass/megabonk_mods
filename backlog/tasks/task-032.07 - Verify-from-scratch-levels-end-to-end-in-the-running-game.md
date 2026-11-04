---
id: TASK-032.07
title: Verify from-scratch levels end to end in the running game
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 20:37'
labels: []
dependencies:
  - TASK-032.05
  - TASK-032.06
parent_task_id: TASK-032
priority: high
ordinal: 160000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032 acceptance gate. Prove in the running game, through the megabonk MCP server (docs/development.md, "MCP server" and its end-to-end check), that a minimal from-scratch level works, and that old levels still do.

Create the minimal level with the editor's new-level command and commit it as levels/scratch-minimal.mblevel.json. Relaunch into it and enter the editor (task mod:build first; MEGABONK_DEV=true). Capture screenshots showing no stock map content. Walk to the boss spawner, interact, defeat the boss and reach the portal. Run Validate. Die and retry. Then repeat the load of levels/thps.mblevel.json and load levels/example-forest.mblevel.json to confirm generated-baseline levels are unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 levels/scratch-minimal.mblevel.json is committed and loads from a fresh relaunch with no generated tiles, props or interactables visible in a screenshot
- [ ] #2 The player spawns at the authored spawn, reaches the boss spawner, defeats the boss and reaches the portal
- [ ] #3 Validate passes on the from-scratch level
- [ ] #4 A death-screen retry restarts without spawn reset or portal interference
- [ ] #5 levels/thps.mblevel.json and levels/example-forest.mblevel.json load and play as before
- [ ] #6 Results, screenshots and log excerpts are summarized in the task, and parent TASK-032 acceptance criteria are checked off
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
