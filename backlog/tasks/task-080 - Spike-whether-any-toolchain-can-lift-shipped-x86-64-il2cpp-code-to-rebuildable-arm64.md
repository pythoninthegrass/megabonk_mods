---
id: TASK-080
title: >-
  Spike whether any toolchain can lift shipped x86-64 il2cpp code to rebuildable
  arm64
status: To Do
assignee: []
created_date: '2026-11-16 00:31'
labels: []
dependencies: []
references:
  - docs/development.md
  - taskfiles/re.yml
modified_files:
  - scripts/
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
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
