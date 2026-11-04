---
id: TASK-039
title: Fix failing tests/test_thps_pack_pieces.py prefab piece tests
status: To Do
assignee: []
created_date: '2026-11-04 04:02'
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
- [ ] #1 Root cause of both failures identified and recorded in the task notes
- [ ] #2 tests/test_thps_pack_pieces.py passes
- [ ] #3 task check passes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
