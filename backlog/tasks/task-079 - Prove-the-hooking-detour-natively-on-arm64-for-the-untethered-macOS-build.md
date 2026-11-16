---
id: TASK-079
title: Prove the hooking detour natively on arm64 for the untethered macOS build
status: To Do
assignee: []
created_date: '2026-11-15 23:53'
updated_date: '2026-11-16 00:31'
labels: []
dependencies: []
references:
  - docs/development.md
  - scripts/native_bind_probe.py
  - scripts/native_bind_probe/host.c
  - .tools/native-bind/summary.json
modified_files:
  - scripts/
  - taskfiles/re.yml
  - docs/development.md
priority: high
ordinal: 252000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Intel Macs are out of scope for this port, so every question here is an Apple silicon question. Mach-O gives a process one architecture: dyld refuses a slice it cannot run, so a translated x86_64 GameAssembly.dylib forces the player executable, UnityPlayer and every other load-time dependency onto x86_64 slices too. Route B therefore cannot pair translated game code with a native arm64 player, and its endpoint on the only hardware this port targets is the current CrossOver experience with Wine deleted and Rosetta kept, carrying the date Apple attached to that, macOS 27 as the last release running Intel-only apps. Route C, the reimplementation built arm64 by Unity, is the only route that is simultaneously untethered, native and non-expiring, and with the game unmaintained there is no upstream to hand over an arm64 build.

Correction to the first version of this task. It claimed the probe player's arm64 slice had never executed because the host was an Intel Mac. That was false: the development host is an Apple M4 (Darwin arm64, hw.optional.arm64=1) and .tools/native-bind/summary.json records host_id darwin-arm64. The arm64 leg1 passes, arm64 leg2 passes all five mscorlib candidates and fails the same five whose assemblies a probe player lacks, winners.arm64 is the same System.Math::Abs(int) as x86_64, and the two columns are distinguishable from inside the process by proc_translated, 0 native and 1 under Rosetta. So the arm64 binding path is already proven on that architecture and the criterion asking for it is removed rather than met by new work.

The real gap is leg3, and it is a gap in this repository rather than in the architecture. scripts/native_bind_probe/host.c guards the trampoline and absolute-jump patcher with an x86_64 ifdef, and the non-x86_64 branch emits leg3 needs x86_64 absolute-jump patching. So arm64 leg3 currently reports a fail that was never attempted, and hooks_passed.arm64 is null only because of that. The work is the arm64 equivalent of the detour: an mmap'd trampoline replaying the target's own prologue and an absolute branch to a counting hook, built from adrp and add to materialise the target address and br to reach it, with the read-write then read-execute page dance Apple requires where Linux can mmap read-write-execute directly.

Two scoring fixes come along with it. A leg the host cannot implement on the running architecture should be reported as the existing skipped status in LEG_STATUS_ORDER rather than as a fail, so an unimplemented code path never reads as an architectural wall; the vocabulary already exists, it is just not used for this case. And the metadata question, which needs no Apple silicon, stays: the standalone parser reads zero classes from the shipped bundle because its il2cppmd version 24.0.0 metadata is older than the version 29 it supports, while the shipped Linux runtime carries the real il2cpp implementation and is on hand locally and on the player box, so asking that runtime to read its own metadata is runnable today.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 arm64 leg3 either scores pass with the detour's own evidence, trampoline address and a hook_calls count, or names a specific failure, and never emits the string leg3 needs x86_64 absolute-jump patching
- [ ] #2 A counting hook on arm64 is proven to fire at least once while the original method still returns its own value, so the detour is shown not to disturb the callee
- [ ] #3 A leg the host cannot implement on the running architecture is reported with the existing skipped status and does not make the run's overall verdict fail, and each leg still carries proc_translated so a Rosetta run cannot be read as a native one
- [ ] #4 The shipped runtime itself enumerates classes from its own global-metadata.dat on the Linux control leg, or the failure is characterised well enough to say whether the parser's 0-classes result is an artifact
- [ ] #5 The notes state what the untethered build is on each architecture, naming the whole-process Rosetta bound and the macOS 27 date, and what would replace it with its cost
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 No Wine or CrossOver parity measurement is used to justify the native build
- [ ] #7 Arm64 evidence is labelled with host_id and per-leg proc_translated so a Rosetta run cannot be mistaken for a native one
<!-- DOD:END -->
