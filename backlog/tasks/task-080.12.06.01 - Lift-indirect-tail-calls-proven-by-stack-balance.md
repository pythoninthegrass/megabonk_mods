---
id: TASK-080.12.06.01
title: Lift indirect tail calls proven by stack balance
status: Done
assignee: []
created_date: '2026-11-16T19:23:00Z'
updated_date: '2026-11-16T23:26:00Z'
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
- [x] #1 Before any emitter change, the proof is measured on the seed-81 and seed-82 BRANCHIND bodies and the counts proven, unproven and untracked-rsp are recorded with a reason for each unproven body; the run stops and reports if the unproven share makes the slice not worth continuing.
- [x] #2 The emitter lifts a BRANCHIND as an indirect call followed by a return when rsp is proven equal to its entry value on every path into the site and the target is read from memory, or when the original load-traced rule applies; every other BRANCHIND remains a recorded hole, and an inconsistent-path or untrackable-rsp case never lifts on the proof.
- [x] #3 Differential tests written first compare lifted arm64 against native arm64 for a synthetic C tail call through a function-pointer slot; a stack-unbalanced counter-example stays a BRANCHIND hole and a malformed body fails safely.
- [x] #4 Full reruns of seeds 81 and 82 (5,000 bodies per class, same binary and options as the pshuflw reruns) write to new .tools/lift-probe-tailcall-{81,82} directories without replacing baselines; all 15,000 bodies per run decode, verify and compile for arm64 with no failure or missing body.
- [x] #5 Comparing every address, size and hole list against the pshuflw reruns shows the only changed bodies are BRANCHIND carriers that lose the hole; every other body is unchanged, and the report lists each remaining BRANCHIND body with the reason it lacked proof.
- [x] #6 docs/development.md reports the new hole counts per seed, the proof rule and its limits.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Deviation from the original criterion #2, recorded at close: it said to lift only when rsp is proven balanced. The unattended run found that rule regressed criterion #5 (the old straight-line load rule already lifted some sites the proof does not cover) and kept the load rule as a floor, so the proof only adds lifted sites. Review then found balance alone is unsound: a frameless function with an unrecovered switch also has rsp at its entry value, and the run had rewritten four existing tests to fit. The fix requires the target to be read from memory (a LOAD or a COPY from a fixed slot) in addition to the proof, restores those four tests verbatim and corrects a fixture that modelled the slot read as its address. Criterion #2 above is reworded to the rule as shipped.

Run history: the unattended run (3 launches) quit twice mid-turn on tool-less narration and shipped a regression on its first full seed run (BRANCHIND hole bodies 152 to 298 and 144 to 391) before correction; its own summary reported criterion #5 clean. Every number in the final summary was re-derived independently from the saved bodies.jsonl files.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Lowers a BRANCHIND with no recovered jump table as an indirect call followed by a return when rsp is proven at its entry value on every path into the site and the target is read from memory (a LOAD or a COPY from a fixed slot), keeping the original load-traced rule as a floor. A computed or undefined target, an inconsistent path or an untrackable rsp stays a recorded hole.

Measured on the seed-81 and seed-82 draws (15,000 bodies each, same binary): 922 and 860 sites proven; BRANCHIND hole bodies fall 152 to 11 and 144 to 26; hole-free bodies rise 14,846 to 14,987 and 14,853 to 14,971. Against the pshuflw baselines the only changed bodies are 141 and 118 BRANCHIND carriers losing the hole; no other hole list, address or size changed, and all bodies decode, verify and compile for arm64. Every newly lifted site reads its target from a fixed slot; none is switch-shaped. Requiring a memory-read target changes no body on these draws. Final evidence is in .tools/lift-probe-tailcall4-{81,82} (earlier iterations in tailcall-, tailcall2- and tailcall3-); scripts/branchind_report.py writes the per-site census.

Tests: existing tests unchanged (the diff to them is empty); new tests cover the balanced slot-load tail call, the unbalanced and computed counter-examples and a branch out of the dump. task check passes on main. Commits 2e08d77, 4c7fd88 and 8e49cc8, merged to main by fast-forward.

Limits: frames restored through leave or lea rsp stay untrackable holes (11 and 26 bodies keep a BRANCHIND hole); the seed-81 and seed-82 shapes were only measured on these draws.
<!-- SECTION:FINAL_SUMMARY:END -->
