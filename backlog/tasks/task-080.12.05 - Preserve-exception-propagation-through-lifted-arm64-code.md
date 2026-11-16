---
id: TASK-080.12.05
title: Preserve exception propagation through lifted arm64 code
status: To Do
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T23:45:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.02
references:
  - scripts/pcode_lift.py
  - scripts/eh_probe.py
  - TASK-080.07
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 272000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The census found exception tables on 8,373 game-section bodies and 103,628 landing-pad entries. Current lifted code ignores their unwinding semantics, so successfully compiling a throwing method cannot count as correctness. This task establishes interoperable exception propagation for the native runtime, including interaction with native callers; it does not remeasure the already recorded census. Original binary exception metadata remains local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Lifted code matches the shipped reference for caught throws, nested propagation, cleanup/finally execution, rethrow and an uncaught exception's reported outcome.
- [ ] #2 Exceptions crossing required native/lifted boundaries unwind correctly without corrupting stack or register state.
- [ ] #3 Required exception-bearing bodies and metadata in the selected runtime image are accounted for; unsupported unwind cases are rejected rather than emitted as apparently runnable code.
- [ ] #4 Regression tests execute on native arm64, include cleanup ordering and failure cases, and docs state the verified unwind contract and coverage.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff from the calling-interface work (done on main, commit 489e95a; read its "Native and lifted calling contract" section in docs/development.md before designing anything). The contract this task must fit: lifted bodies keep `void sub_<ELF-address>(unsigned char *reg)`; scripts/lift_abi.py generates typed native exports and imports from explicit Binding(address, name, Signature) lists, each export call getting a private 8 KiB register file and 64 KiB guest stack; with `pcode_lift.lift_body(..., call_dispatch=True)` CALLIND and recognised loaded indirect tail calls go through a generated `lift_dispatch` switch that aborts on an unregistered target; raw pcode already does the CALL push and RET pop, and the adapter checks guest RSP advances by eight on return. tests/test_lift_abi.py and tests/fixtures/lift/calls.c are the pattern for synthetic x86-64 fixtures executed natively on arm64. The interop task lists exception unwinding, nonlocal exits, guest TLS and the floating-point environment as NOT supplied by these adapters, so nothing about unwinding exists yet.

Measured facts about the exception surface (docs/development.md, the eh-probe census; reproduce with task re:eh-probe, output in .tools/eh-probe/summary.json): 8,373 of 196,137 il2cpp-section bodies carry an LSDA (0 tiny, 2,642 small, 5,731 large); 2,795 have two to four distinct landing pads and 5,578 have five or more; 144,668 call-site entries of which 103,628 name a landing pad, 84,257 distinct pads, largest body 931; .gcc_except_table is 1,110,448 B at 0xfba378. Two CIEs use the `zPLR` augmentation with personality encoding 0x9b and LSDA encoding 0x1b, at 0x9b9dd8 (9,424 FDEs, 8,373 of them in the il2cpp section) and 0xa71910 (0 FDEs). All 103,628 landing pads lie strictly inside their own body. A one-pad-per-body implementation covers none of the 67% of affected bodies with five or more pads. The image imports _Unwind_* from libgcc_s (and the shim probe lists __gcc_personality_v0 as a weak import it treats as a no-op), so on Linux the unwinder is a platform import; coordinate with the platform-services task so only one of the two provides it.

Not yet researched (do not assume): (1) whether Ghidra's pcode dump contains the landing-pad blocks at all. They are reached only by the unwinder, never by a branch, and scripts/lift_probe/LiftDump.java records pcode and jump tables only, so a body can report fully decoded while its pads are missing. A cheap and decisive first measurement: for the LSDA-bearing bodies in a sample, check that every landing-pad address is an instruction start in the dumped pcode. (2) Which personality routine the two CIEs actually name; the census reports the slot, not the function, and does not resolve nonzero TType entries or whether such bodies call a shared runtime helper (that needs the image loaded). (3) Which shipped methods can serve as an oracle through the il2cpp C API for caught throws, nested propagation, cleanup order and rethrow; il2cpp_runtime_invoke reports a thrown exception through its out parameter (see invoke_candidate in scripts/native_bind_probe/host.c), but no throwing method has been identified. Look in .tools/il2cpp_dump/dump.cs, and prefer methods with deterministic, argument-driven throws. (4) How to build synthetic x86-64 fixtures that actually carry an LSDA: the existing differential fixtures are freestanding and nostdlib, so a personality and unwinder would have to be supplied or avoided. (5) Whether any native code (Unity or libc) can raise a C++ exception through lifted frames, which sets whether the native-boundary half of acceptance criterion #2 needs more than lifted-to-lifted propagation.

Design guidance, hypotheses and not decisions. The lifted code keeps guest state in a register-file struct, so a native arm64 unwinder cannot walk guest frames, and LLVM invoke/landingpad over those frames looks unlikely to map onto them; an explicit propagation scheme in the lifter (a pending-exception flag checked after each call, branching to the call site's landing pad per the LSDA table, or returning to the caller) fits the register-state ABI better. The unwind design, the unsupported-case policy and how it crosses native and lifted boundaries are a material architectural choice: present the proposed design for maintainer approval before coding, as the interop task did. Acceptance criterion #3 requires unsupported unwind shapes to be rejected, never emitted as apparently runnable code, and the emitter's existing practice of recording a hole rather than guessing is the model.

Process lessons from the previous task in this chain, worth applying here: never rewrite an existing test's expectation to make new behaviour pass (an unattended run did so and the change was caught only in review; the diff to existing tests should stay empty apart from new tests); require positive evidence for any lowering rule, since a necessary condition alone is not enough (balanced rsp is necessary but not sufficient for a tail call); confirm baselines are unchanged by comparing per-body hole lists across the seed-81 and seed-82 draws, which also guards against the lifter silently dropping bodies. The pcode caches for those draws were deleted, so a re-score needs a cold Ghidra dump (about 26 minutes per seed with GHIDRA_HEADLESS_MAXMEM=8G). The final BRANCHIND results are in .tools/lift-probe-tailcall4-{81,82}. Keep original exception metadata local-only; docs must not cite task ids or personal identifiers.
<!-- SECTION:NOTES:END -->
