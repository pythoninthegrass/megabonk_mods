---
id: TASK-080.12.06.01
title: Lift indirect tail calls proven by stack balance
status: To Do
assignee: []
created_date: '2026-11-16T19:23:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - scripts/pcode_lift.py
  - scripts/lift_probe.py
  - scripts/lift_holes.py
  - scripts/lift_tail_calls.py
  - tests/test_pcode_lift_differential.py
documentation:
  - docs/development.md
parent_task_id: TASK-080.12.06
priority: high
type: enhancement
ordinal: 281000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
BRANCHIND with no recovered jump table is 152 and 144 of the remaining holes in the seed-81 and seed-82 samples, against 2 and 3 for JUMPTABLE_TARGET. In the seed-80 sample, 21 of 22 hole bodies are indirect tail calls: a function pointer loaded from a fixed .bss slot, lazily resolved, frame torn down, then jmp rax. A throwaway check over the seed-80 pcode (a worklist pass that tracks the net rsp change per instruction, treats a CALL as net zero, and requires every path into a site to agree) proved rsp equals its entry value at all 33 tail-call sites and rejected the one unrecovered switch (rsp delta -24). When rsp equals its entry value at the jump, jmp rax is equivalent to call rax followed by ret, so lifting it that way is a proof, not a guess. A site without that proof must stay a hole; the parent task forbids guessing that an unresolved jump is a tail call. The seed-81/82 hole shapes are unmeasured and may include frames restored through leave or lea rsp, which the proof leaves as holes. Scope is this one hole kind only: no new instruction semantics and no change to the other hole kinds.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Before any emitter change, the proof is measured on the seed-81 and seed-82 BRANCHIND bodies and the counts proven, unproven and untracked-rsp are recorded with a reason for each unproven body; the run stops and reports if the unproven share makes the slice not worth continuing.
- [ ] #2 The emitter lifts a BRANCHIND as an indirect call followed by a return only when rsp is proven equal to its entry value on every path into the site; every other BRANCHIND remains a recorded hole, and an inconsistent-path or untrackable-rsp case never lifts.
- [ ] #3 Differential tests written first compare lifted arm64 against native arm64 for a synthetic C tail call through a function-pointer slot; a stack-unbalanced counter-example stays a BRANCHIND hole and a malformed body fails safely.
- [ ] #4 Full reruns of seeds 81 and 82 (5,000 bodies per class, same binary and options as the pshuflw reruns) write to new .tools/lift-probe-tailcall-{81,82} directories without replacing baselines; all 15,000 bodies per run decode, verify and compile for arm64 with no failure or missing body.
- [ ] #5 Comparing every address, size and hole list against the pshuflw reruns shows the only changed bodies are BRANCHIND carriers that lose the hole; every other body is unchanged, and the report lists each remaining BRANCHIND body with the reason it lacked proof.
- [ ] #6 docs/development.md reports the new hole counts per seed, the proof rule and its limits.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
