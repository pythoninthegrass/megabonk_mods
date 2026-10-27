---
id: TASK-020.01
title: >-
  Query live Unity objects and fields through the harness and MCP, filtered with
  jq
status: Done
assignee:
  - claude
created_date: '2026-10-27T20:07:00Z'
updated_date: '2026-10-27T20:44:00Z'
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
- [x] #1 A harness command and matching MCP tool list all loaded Unity objects of a named type with their name and a caller-chosen set of public fields, returned as JSON
- [x] #2 Enum-typed fields are returned as their integer value so a mismatch with the Il2Cpp enum, such as MapHell eMap=64, is visible
- [x] #3 An optional jq expression argument is applied to the JSON result before it is returned; an invalid expression is a tool error that names the jq parse failure
- [x] #4 An unknown type name or field name is a tool error that names it, not an empty result
- [x] #5 Against the running game, querying MapData with fields name and eMap returns MapDesert=2, MapDungeon=16, MapForest=1, MapGraveyard=8 and MapHell=64
- [x] #6 The query is read-only and works while a run is active or frozen
- [x] #7 jq filtering and argument validation have offline unit tests; the harness command has Unity-free unit tests for its parsing and result shape
- [x] #8 Documented in docs/development.md with an example of the MapData query and a jq filter
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Harness command `query-objects` `{type, fields[]}`: parsed in harness_command.cs into a `QueryArgs` (type non-empty, fields array of non-empty strings; name is always returned).
2. Unity-free `object_query.cs`: reflection read of named public properties/fields off any object, enums as their integer value, unknown field is an error naming it, result shape `{type, count, objects:[{name, ...fields}]}`. Unit-tested with plain POCOs.
3. dev_harness.cs: resolve the Il2Cpp interop wrapper type by name (unknown type is an error naming it), find loaded instances with Resources.FindObjectsOfTypeAll, feed them to the query. Read-only, no pause dependence.
4. Python: run.build_query_objects_command, `query_objects(type, fields, jq)` MCP tool; jq.py applied to the result before encoding; bad expression is a ToolError with the jq parse message. Add `jq` to the script deps and the scripts:test taskfile line.
5. Tests first (C# parsing/query shape, Python builder/jq/validation), then implementation. Live check: MapData fields name,eMap against the running game. Docs in docs/development.md.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the `query-objects` harness command and the `query_objects(type, fields?, jq?)` MCP tool.

- Mod: `object_query.cs` (Unity-free reflection reader: enums as integers, unknown type/field errors, result shape), `QueryArgs` parsing in `harness_command.cs`, and `QueryObjects` in `dev_harness.cs` using `Resources.FindObjectsOfTypeAll` over the Il2Cpp interop wrapper type.
- Python: `run.build_query_objects_command`; the MCP tool validates arguments, compiles the jq expression before sending anything (parse failure is a ToolError with jq's message), and returns the inner result or the jq output. `jq>=1.8` added to the script deps and `scripts:test`.
- Tests: 14 new xunit cases (parsing, query shape, type resolution) and 8 pytest cases (builder, jq filtering, invalid jq, unknown type, empty args). `task check` passes.
- Live check on a frozen editor run: MapData with `eMap` returned MapDesert=2, MapDungeon=16, MapForest=1, MapGraveyard=8, MapHell=64; unknown type and unknown field were rejected naming them. Not separately exercised with an unfrozen run; the command never touches pause state.
- Docs: "Querying live objects" in docs/development.md. The TOON-vs-JSON note there still says to re-measure on this query's uniform rows.
<!-- SECTION:FINAL_SUMMARY:END -->
