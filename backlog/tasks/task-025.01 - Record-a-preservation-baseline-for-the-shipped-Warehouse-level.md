---
id: TASK-025.01
title: Record a preservation baseline for the shipped Warehouse level
status: To Do
assignee: []
created_date: '2026-10-30T16:24:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - scripts/build_thps_level.py
  - levels/thps.mblevel.json
  - scripts/thps_item_overrides.json
documentation:
  - docs/development.md
  - docs/asset-bundles.md
modified_files:
  - tests/test_build_thps_level.py
  - docs/development.md
parent_task_id: TASK-025
type: chore
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The construction kit work will add pack assets, change the generator and touch the editor's handling of placed objects, all while levels/thps.mblevel.json and the assets it loads must stay exactly as they are. Without a machine-checkable baseline there is no way to prove later tasks did not disturb the shipped level, and a byte drift in a generated level file is invisible in review. This task establishes that baseline and the check that enforces it, before any decomposition work starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A committed baseline records the current levels/thps.mblevel.json contents, the generator's derived values, and the pack assets the level depends on
- [ ] #2 A check compares the level file, a fresh generator run's output and the pack asset inventory against the baseline and fails naming every difference
- [ ] #3 Regenerating with scripts/build_thps_level.py reproduces the baselined level file exactly
- [ ] #4 The check runs in the existing test suite and passes before any decomposition work lands
- [ ] #5 Docs state how to refresh the baseline deliberately and that a refresh means the shipped level changed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
