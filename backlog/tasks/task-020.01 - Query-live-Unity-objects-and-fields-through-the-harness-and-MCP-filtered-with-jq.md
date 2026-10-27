---
id: TASK-020.01
title: >-
  Query live Unity objects and fields through the harness and MCP, filtered with
  jq
status: To Do
assignee: []
created_date: '2026-10-27T20:07:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
references:
  - 'https://github.com/mwilliamson/jq.py'
parent_task_id: TASK-020
priority: medium
type: enhancement
ordinal: 81000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Answering "which MapData assets exist and what is their eMap?" needed new mod code, a rebuild and a relaunch, and the Il2Cpp dump could not answer it because it disagreed with the live asset (Hell is 4 in the enum, 64 in the MapHell asset). A generic read-only query of the running game would answer such questions in one call. Results can be large, so the MCP side filters them with an optional jq expression using the jq.py bindings (https://github.com/mwilliamson/jq.py) so only the rows the caller wants are returned.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A harness command and matching MCP tool list all loaded Unity objects of a named type with their name and a caller-chosen set of public fields, returned as JSON
- [ ] #2 Enum-typed fields are returned as their integer value so a mismatch with the Il2Cpp enum, such as MapHell eMap=64, is visible
- [ ] #3 An optional jq expression argument is applied to the JSON result before it is returned; an invalid expression is a tool error that names the jq parse failure
- [ ] #4 An unknown type name or field name is a tool error that names it, not an empty result
- [ ] #5 Against the running game, querying MapData with fields name and eMap returns MapDesert=2, MapDungeon=16, MapForest=1, MapGraveyard=8 and MapHell=64
- [ ] #6 The query is read-only and works while a run is active or frozen
- [ ] #7 jq filtering and argument validation have offline unit tests; the harness command has Unity-free unit tests for its parsing and result shape
- [ ] #8 Documented in docs/development.md with an example of the MapData query and a jq filter
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
