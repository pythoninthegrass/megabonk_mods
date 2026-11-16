---
id: TASK-080
title: >-
  Spike whether any toolchain can lift shipped x86-64 il2cpp code to rebuildable
  arm64
status: Done
assignee: []
created_date: '2026-11-16 00:31'
updated_date: '2026-11-16T02:05:00Z'
labels: []
dependencies: []
references:
  - docs/development.md
  - taskfiles/re.yml
modified_files:
  - scripts/lift_probe.py
  - scripts/pcode_lift.py
  - scripts/lift_probe/LiftDump.java
  - tests/test_lift_probe.py
  - tests/test_pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
  - taskfiles/re.yml
  - docs/development.md
priority: high
ordinal: 253000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Route A, a full static recomp, was written off without being tried: the route notes say no maintained lifter produces rebuildable code at this scale, that McSema is archived read-only by its owner and needs an IDA Pro licence to recover control-flow graphs, and that remill lifts instructions which its own docs say is not enough without McSema. Those are citations about other people's tools, not measurements on this binary, and the same notes carried a stale churn figure for months. With Intel Macs out of scope and no upstream to hand over an arm64 build, Route A is one of only two ways to an arm64-native artifact, so the dismissal needs to rest on a scored sample rather than on a quotation.

Bounded spike, hours not weeks. Take a sample of representative bodies from the shipped .tools/megabonk-linux-native/Megabonk/GameAssembly.so, spanning size classes and deliberately including some of the 1,390 bodies over 512 B, and attempt to lift each with what is on this host: radare2 6.2.4 (darwin-arm_64) with its analysis and decompiler paths, and the LLVM toolchain at /opt/homebrew/opt/llvm/bin, which is keg-only so its binaries are absent from PATH and must be named explicitly; llvm-dis, llc, opt, llvm-mc and llvm-objdump are all there, which means the back half of an IR pipeline exists even though no x86 to IR lifter does. mcsema-disass, mcsema-lift, remill-llvm, rizin and analyzeHeadless are absent, and no Ghidra application is installed despite REA's Ghidra environment variables being configured, so a Ghidra-based attempt is an install first, not a call.

A documented no is a passing outcome and is worth as much as a yes: it would retire Route A on measured evidence instead of on a citation, and it would tell Route C, the reimplementation, that it is alone. What is not acceptable is an answer that stops at what a tool's README claims.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inputs (done): GameAssembly.so copied from the Linux player box over the private network into .tools/megabonk-linux-native/Megabonk/ (sha256 a86fd434...5ba1, 87,741,504 B). radare2 6.2.6 installed via brew (task text said 6.2.4, not present). Ghidra 12.1.4 IS installed as a brew formula (analyzeHeadless under /opt/homebrew/Cellar/ghidra/12.1.4/libexec/support), contrary to the task text, so a Ghidra leg is a call, not an install.
2. Sample: pick bodies from dump.cs RVAs across size classes (tiny, <64 B, 64-512 B, >512 B incl. several of the 1,390 large ones), fixed seed, recorded in a JSON manifest.
3. Attempt per body: (a) r2 analysis plus pdc/pdg decompile and any r2 ESIL-to-IR path, (b) Ghidra headless pcode per function, (c) hand-check whether pcode/ESIL can be emitted as LLVM IR that llc targets to arm64 and llvm-mc/clang assembles. Score each stage pass/fail per body: disassemble, CFG recovered, lifted to IR, IR verifies (opt -verify), compiles to arm64 object.
4. Driver in scripts/ (stdlib Python, tests first for the sampler and scorer), a re: task in taskfiles/re.yml, results JSON under .tools/.
5. Write the measured verdict into docs/development.md Route A paragraph, replacing the citation-based dismissal.
Risk: scale of 'rebuildable' needs a stated bar; a lifted body counts only if it verifies and compiles, behavioural equivalence is out of scope for hours.

Plan as executed (supersedes steps 2 and 3 above): the sample is drawn from .eh_frame function ranges of the il2cpp section, not dump.cs RVAs, because dump.cs comes from the Windows build and its addresses do not apply to the Linux ELF. Per body: Ghidra raw pcode plus decompiler-recovered jump tables, then a purpose-written pcode to LLVM IR emitter, scored on decoded, no-hole, verifier, and arm64 object; radare2 is scored separately on 30 bodies. Hand-checking ESIL as IR was dropped because radare2 has no IR output.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Status: implementation, measurement and docs done; `task check` passes (1919 passed, 1 skipped).

Inputs: GameAssembly.so pulled over the private network from the Linux player box (sha256 a86fd434...5ba1). radare2 6.2.6 installed via brew (the task text said 6.2.4, which was absent). Ghidra 12.1.4 was already installed as a brew formula, contrary to the task text, so no install was needed. Ghidra rejects project paths with a dot-prefixed element, so the driver keeps its project in a temp dir.

Binary: the game code is the 46.8 MB `il2cpp` section; bounds from .eh_frame. 196,137 bodies (75,845 tiny <=63 B, 100,919 small <=512 B, 19,373 large). The task's 1,390 figure is Assembly-CSharp only on the Windows build. Whole-section census: 11,773,906 instructions, 298 mnemonics, zero undecodable, no x87, no AVX, no %fs: TLS, 18,986 indirect jmp, 79,458 indirect call.

Code: scripts/pcode_lift.py (Ghidra raw pcode -> LLVM IR), scripts/lift_probe/LiftDump.java, scripts/lift_probe.py, `task re:lift-probe`. Tests: tests/test_pcode_lift.py, tests/test_lift_probe.py, tests/test_pcode_lift_differential.py, fixture tests/fixtures/lift/diff.c. Written test-first.

Final measurement, 3,000 bodies (1,000 per class, seed 80): decoded 3000/3000, verifier 3000/3000, arm64 object 3000/3000, lifted with no hole 2956/3000 (tiny 984, small 991, large 981). Holes (bodies): BRANCHIND with no recovered table 21, divps 20, minps 2, maxps 2, divpd 1, JUMPTABLE_TARGET 1. 193 bodies use the tail-call approximation (BRANCHIND whose target traces through COPYs to a LOAD); a switch the decompiler failed to recover could be misclassified as a tail call silently. Unmapped constant refs 0. arm64 object is 9.11x the x86 bytes at -O2. radare2 (30 bodies): extent matched the frame record in 8, 0 of 30 pdc outputs compile, no IR output, pdg/pdd need uninstalled plugins.

Debugging history worth keeping: (1) Ghidra rebases a shared object by 0x100000, so the first sample disassembled at the wrong addresses; everything is now reported as file VAs. (2) ram varnodes and LEA constants are data/code addresses and must be rebased to section symbols; .bss must be in the section list (4,001 unmapped refs before). (3) unique-space offsets are sparse (0x58300) and must be compacted or the lifted code writes out of bounds; this only showed up when the differential test ran the code. (4) Earlier runs reported 214 BRANCHIND holes; the cause was thunks that load a pointer into a unique temp, COPY it to a register and `jmp *reg`, which the first tail-call rule missed. One earlier note here claimed this was fixed before it was measured; it was not until the COPY-chain rule.

Differential test: 10 freestanding C functions compiled to x86-64 ELF, lifted, rebuilt for arm64, match native arm64 on 2,000 inputs each; breaking INT_ADD makes it fail (harness run bounded by a 120 s timeout). Validates the emitter only; there is no oracle for real il2cpp bodies.

Not measured, and stated as such in docs/development.md: C++ exception unwinding (1.1 MB .gcc_except_table, personality CIE); the lifted calling interface vs the native il2cpp runtime and Unity; rewriting data pointers (466,320 relative relocations) to symbols; SSE ops without semantics; x86 vs arm64 float edge cases; TLS; running any lifted real body; 9x code size.

Verdict recorded in docs/development.md ("Lifting the shipped code to arm64", plus the Route A and B-prime bullets): liftability does not block Route A or B-prime; the McSema/IDA/remill reading was irrelevant; the open risk moved to exceptions, the calling interface and data relocation, and size. Route C is not alone as an arm64-native option, but the cost of making lifted code run in the player is unmeasured.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Route A's dismissal is replaced by a measurement on the shipped binary. A Ghidra-pcode front end plus a purpose-written LLVM IR emitter lifts a 3,000-body sample (1,000 per size class, seed 80) of the il2cpp section: 3000/3000 decode, 3000/3000 pass the LLVM verifier, 3000/3000 compile to arm64, and 2956/3000 (98.5%) lift with no hole. Remaining holes: 21 computed jumps without a recovered table, 25 SSE operations without semantics, 1 jump-table case outside its body. 193 bodies rely on a tail-call approximation that could misclassify an unrecovered switch. arm64 output is 9.11x the x86 bytes. radare2 does not reach IR (extent matched in 8 of 30, 0 of 30 pdc outputs compile as C). The McSema/IDA/remill reading in the old notes did not matter.

Verification: tests/test_pcode_lift.py and tests/test_lift_probe.py cover the emitter and driver logic; tests/test_pcode_lift_differential.py lifts ten freestanding C functions, rebuilds them for arm64 and matches native arm64 on 2,000 inputs each, and fails when the emitter is deliberately broken. `task check` passes (1919 passed, 1 skipped). The sample numbers come from `task re:lift-probe`.

Risks and follow-ups, recorded in docs/development.md and not created as tasks: the differential test validates the emitter only (no oracle for real il2cpp bodies); C++ exception unwinding, the calling interface to the Unity runtime, rewriting data pointers, SSE and float edge semantics, thread-local storage and the 9x code size are unmeasured. Liftability does not block Route A or B-prime; the open questions moved to those items.
<!-- SECTION:FINAL_SUMMARY:END -->
