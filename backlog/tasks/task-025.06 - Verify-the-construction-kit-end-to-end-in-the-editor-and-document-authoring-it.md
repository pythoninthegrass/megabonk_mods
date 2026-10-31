---
id: TASK-025.06
title: Verify the construction kit end to end in the editor and document authoring it
status: To Do
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-31T02:58:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.05
  - TASK-025.07
references:
  - scripts/mcp_server.py
  - scripts/run.py
  - levels/thps.mblevel.json
documentation:
  - docs/development.md
  - docs/thps-warehouse-pieces.md
parent_task_id: TASK-025
type: task
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.05, which delivers the assembled editable level. Everything so far has been judged piece by piece; what has not been proven is that a person can actually rebuild the arena with the kit in the running game, and that nothing about the shipped level regressed once the editor starts handling dozens of interlocking pieces instead of one mesh. This task drives the whole workflow through the megabonk MCP harness and leaves the author-facing documentation behind.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A harness-driven walkthrough selects, moves, rotates, duplicates and deletes pieces in the editable level, then saves and reloads it with the changes intact
- [ ] #2 Undo and redo restore every edit made in the walkthrough
- [ ] #3 A ramp is rebuilt from composable modules in the editor and its joined surface rides and grinds continuously
- [ ] #4 Performance and selection remain usable with the full set of pieces placed
- [ ] #5 The shipped Warehouse level is re-verified unchanged and its gameplay re-checked through the harness
- [ ] #6 Docs give an author-facing guide to the kit: the palette, module mating conventions, how to assemble and modify ramps, and the preservation guarantee for the shipped level
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
