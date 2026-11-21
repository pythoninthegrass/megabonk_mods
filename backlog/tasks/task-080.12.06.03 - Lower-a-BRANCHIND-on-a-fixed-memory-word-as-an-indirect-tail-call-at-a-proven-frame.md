---
id: TASK-080.12.06.03
title: >-
  Lower a BRANCHIND on a fixed memory word as an indirect tail call at a proven
  frame
status: To Do
assignee: []
created_date: '2026-11-21T20:14:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
parent_task_id: TASK-080.12.06
priority: medium
type: enhancement
ordinal: 295000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The five bodies that tail-jump through a fixed word (`0x209d5c0`, `0x209e0a0`, `0x209e0c0`, `0x209e0d0` and the site at `0x20f6e90` in `0x20f6e30`) carry a `BRANCHIND` whose input is `ram,<slot>,8` directly, so `defined_by_load` finds no defining op and the site stays a hole although the frame pass proves `rsp` at its entry value. docs/development.md, "AnyPS5 relinker practices against the remaining blockers", records the measurement: a relocation is not the evidence (two of the five slots have none, and the rest hold only a load-time value of a writable slot that code overwrites). The evidence is structural: a fixed address with no index register cannot be a jump table.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A `BRANCHIND` whose input is a `ram` varnode lowers as an indirect call and a return only when the frame pass proves `rsp` at its entry value at that site; no relocation is consulted.
- [ ] #2 `test_branchind_on_a_fixed_memory_word_stays_a_hole_even_at_a_proven_frame` is replaced by tests for the accepted shape and for an unbalanced-frame variant that stays a hole; the computed-register and unbalanced-frame hole tests are unchanged.
- [ ] #3 A rescore over the pinned image shows the five bodies become BRANCHIND-free and no other body changes verdict, with the new baseline written to a fresh directory.
- [ ] #4 The docs/development.md measurement is updated with the new blocked count.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
