---
id: TASK-039
title: Fix failing tests/test_thps_pack_pieces.py prefab piece tests
status: Done
assignee: []
created_date: '2026-11-04 04:02'
updated_date: '2026-11-04 04:10'
labels: []
dependencies: []
priority: medium
ordinal: 151000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`task check` fails on two tests in tests/test_thps_pack_pieces.py: `test_piece_prefab_roots_carry_the_mesh_to_world_scale` and `test_built_prefabs_contain_no_obsolete_kit_or_alias_entries`. They fail on a clean tree too (confirmed with tracked changes stashed), so they predate TASK-006.05. The second reports extra built prefab entries such as `piece-crane-hook`, `piece-south-transition-middle`, `piece-truss-west-02`, `piece-start-flat-east` and `piece-main-north-02` on the built side. Find out whether the tests, the generated prefab output or a stale gitignored build product is out of date, and fix the cause.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Root cause of both failures identified and recorded in the task notes
- [x] #2 tests/test_thps_pack_pieces.py passes
- [x] #3 task check passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rebuild the stale gitignored unity/pack-authoring/Assets/Thps output with `task thps:pack`, then rerun tests/test_thps_pack_pieces.py.
2. Tighten `needs_prefabs` so a directory holding only Warehouse.prefab (stale build) skips instead of failing. Write the failing case first (TDD).
3. Run `task check`, record root cause in notes, commit with a conventional message and no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause: unity/pack-authoring/Assets/Thps (gitignored) was built Oct 29 and holds only Warehouse.prefab. pieces.json and the manifest were regenerated Oct 30 and list the piece prefabs. needs_prefabs only checks the directory exists, so the stale directory runs the tests and they fail.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both failures came from a stale gitignored Assets/Thps build (only Warehouse.prefab, built before pieces.json listed piece prefabs). Rebuilt it with task thps:pack --force (201 prefabs). Changed needs_prefabs to require piece-*.prefab files so a stale directory skips rather than fails, with a unit test for the guard, and documented the rebuild in docs/development.md. task check passes.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
