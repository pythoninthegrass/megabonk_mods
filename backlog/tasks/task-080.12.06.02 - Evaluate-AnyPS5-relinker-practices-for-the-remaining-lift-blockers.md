---
id: TASK-080.12.06.02
title: Evaluate AnyPS5 relinker practices for the remaining lift blockers
status: To Do
assignee: []
created_date: '2026-11-20T22:55:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - 'https://github.com/boykopovar/AnyPS5'
  - 'https://github.com/boykopovar/AnyPS5/blob/main/docs/dev/debt/relinker.md'
documentation:
  - docs/development.md
parent_task_id: TASK-080.12.06
priority: medium
type: spike
ordinal: 294000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After TASK-080.12.06's latest rescore (v7), 108 bodies still carry a BRANCHIND hole and one body (0x208b610) a trap hole, with 41 residual jump-table shapes held back for lack of an accepted index bound. The AnyPS5 relinker (GPL-2.0, a PS5 to Linux/Windows executable converter, not an ISA lifter) solves adjacent problems with no pcode: it finds relative jump tables in gaps between functions by checking that each 4-byte entry lands on a decoded instruction start, and its CallSiteResolver recognizes call and tail-call `jmp` sites that read a relocation slot through a RIP-relative operand, including the address-size-prefixed form. A first read suggests two possible overlaps: the five bodies that tail-jump through a fixed word Ghidra folded into the operand (no LOAD for the load-trace rule), where a relocation on that slot would be the positive evidence the tail-call gate requires, and an instruction-start cross-check on decoded table entries for cases such as 0x2159b14. Neither was verified. This spike confirms or refutes them against the pinned GameAssembly.so and records what is worth reusing, so the lifter does not copy heuristics that weaken its constraint that an unresolved jump is never guessed to be a tail call.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 For each of the five fixed-word tail-jump bodies in the TASK-080.12.06 blocker set, a report states whether the jumped-through slot has a relocation in the pinned GameAssembly.so and what that relocation says the slot can hold.
- [ ] #2 The report states whether AnyPS5's CallSiteResolver slot-recognition rules (operand forms, address-size prefix) cover those five jump shapes, with the decoded bytes of each shape.
- [ ] #3 An instruction-start check on decoded jump-table entries is run against the 22 audited tables and the 0x2159b14 case, with a stated verdict on whether it explains the five unexplained Ghidra cases or the five missing entries.
- [ ] #4 Each practice judged reusable is recorded with the evidence it needs and the existing lifter test that pins the corresponding hole, so a later change cannot loosen that test; practices judged unsuitable are recorded with the reason.
- [ ] #5 No lifter rule is added in this task, the 108-body blocked set and the v7 baseline are left unchanged, and any follow-up lowering is filed as its own task with its evidence requirement.
- [ ] #6 Findings and the AnyPS5 license (GPL-2.0) implications for borrowing code versus borrowing the idea are documented in docs/development.md.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
