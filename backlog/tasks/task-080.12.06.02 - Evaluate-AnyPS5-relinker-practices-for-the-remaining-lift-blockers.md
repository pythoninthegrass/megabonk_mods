---
id: TASK-080.12.06.02
title: Evaluate AnyPS5 relinker practices for the remaining lift blockers
status: Done
assignee: []
created_date: '2026-11-20T22:55:00Z'
updated_date: '2026-11-21T20:15:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - 'https://github.com/boykopovar/AnyPS5'
  - 'https://github.com/boykopovar/AnyPS5/blob/main/docs/dev/debt/relinker.md'
documentation:
  - docs/development.md
modified_files:
  - docs/development.md
  - tests/test_pcode_lift.py
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
- [x] #1 For each of the five fixed-word tail-jump bodies in the TASK-080.12.06 blocker set, a report states whether the jumped-through slot has a relocation in the pinned GameAssembly.so and what that relocation says the slot can hold.
- [x] #2 The report states whether AnyPS5's CallSiteResolver slot-recognition rules (operand forms, address-size prefix) cover those five jump shapes, with the decoded bytes of each shape.
- [x] #3 An instruction-start check on decoded jump-table entries is run against the 22 audited tables and the 0x2159b14 case, with a stated verdict on whether it explains the five unexplained Ghidra cases or the five missing entries.
- [x] #4 Each practice judged reusable is recorded with the evidence it needs and the existing lifter test that pins the corresponding hole, so a later change cannot loosen that test; practices judged unsuitable are recorded with the reason.
- [x] #5 No lifter rule is added in this task, the 108-body blocked set and the v7 baseline are left unchanged, and any follow-up lowering is filed as its own task with its evidence requirement.
- [x] #6 Findings and the AnyPS5 license (GPL-2.0) implications for borrowing code versus borrowing the idea are documented in docs/development.md.
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
1. Research (done): decoded the five fixed-word bodies in the pinned GameAssembly.so (sha256 a86fd434...), read AnyPS5 `CallSiteResolver.cpp` and `X64OpcodeConstants.hpp`, looked up each slot in a fresh `llvm-readelf -r`, found slot writers with a RIP-relative scan of `.text`/`il2cpp`/`.plt`.
2. Run the instruction-start check over the 22 audited bodies' 134 tables (scratch script, not committed) against the dump's instruction starts and an independent per-FDE linear disassembly; split 0x2159b14's five extra and five missing entries.
3. Add two characterization tests to tests/test_pcode_lift.py that pin existing behavior without changing the lifter: BRANCHIND directly on a `ram` varnode with a proven frame stays a hole; a table entry that is not a dump instruction start refuses the byte-evidence replacement.
4. Document findings, the reuse/unsuitable verdicts and the GPL-2.0 position in docs/development.md.
5. File one follow-up task for the fixed-word shape with its evidence requirement; add nothing to scripts/pcode_lift.py and leave the v7 baseline and 108-body set untouched.
6. Run `task check`, commit as a conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both suspected overlaps were checked against the pinned GameAssembly.so and both are refuted as stated. Findings are in docs/development.md ("AnyPS5 relinker practices against the remaining blockers").

- Relocations: 3 of the 5 fixed-word slots have one (malloc and free imports, and an in-image `jmp free@plt` stub). The other 2 are `.bss` with none. Each relocation gives only a load-time value for a writable, non-RELRO slot that in-image code overwrites, so it cannot be tail-call evidence.
- CallSiteResolver rules (`ff /2../6` and REX.W `8b` with RIP-relative operand, `0x67` truncation) cover all five `ff 25` shapes, but it is a slot-to-instruction index that decides nothing about control flow.
- Instruction-start check: all 134 tables and 1,191 decoded entries across the 22 blockers pass, by the dump and by an independent linear decode, so it adds nothing to the verdict. It does reject 964 of 1,216 Ghidra surplus cases as non-code. It does not explain 0x2159b14: the five extra and five missing entries are all valid instruction starts, each extra equal to its missing entry minus 0x3d0, the distance to the twin frame.
- Recommended reuse is the structural fact (fixed address, no index, proven frame), not a relocation; filed as TASK-080.12.06.03 with its evidence requirement. The instruction-start check already exists in `audited_cases`.
- Added two characterization tests that pin current behavior (fixed-word shape stays a hole; a non-instruction-start table entry is refused). No lifter rule was added; baseline and 108-body set untouched. `task check` passes.
<!-- SECTION:FINAL_SUMMARY:END -->
