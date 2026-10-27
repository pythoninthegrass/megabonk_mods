---
id: TASK-020.02
title: >-
  Override map, stage, tier and seed when loading a level through the harness
  and MCP
status: To Do
assignee: []
created_date: '2026-10-27T20:07:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
parent_task_id: TASK-020
priority: low
type: enhancement
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Testing a different map meant copying a level file, patching its map with jq, running it, then deleting it; this happened three times in one session. Optional overrides on the load and relaunch calls would make a one-off probe a single call with no file left behind.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `run.py load`, `run.py relaunch` and the MCP `load` and `relaunch` tools accept optional map, stage, tier and seed overrides that replace those fields of the level file for that load only
- [ ] #2 The level file on disk is not modified, and no temporary level file is left behind
- [ ] #3 Without overrides the behaviour is unchanged
- [ ] #4 An override value that is not an integer, or a stage outside the map's stage range, is rejected with the reason
- [ ] #5 Argument parsing and override merging have offline unit tests
- [ ] #6 Documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
