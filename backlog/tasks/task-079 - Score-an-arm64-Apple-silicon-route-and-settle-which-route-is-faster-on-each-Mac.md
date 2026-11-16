---
id: TASK-079
title: Score an arm64 Apple silicon route for the untethered macOS build
status: To Do
assignee: []
created_date: '2026-11-15 23:53'
updated_date: '2026-11-16 00:20'
labels: []
dependencies: []
references:
  - docs/development.md
  - scripts/native_bind_probe.py
modified_files:
  - scripts/
  - taskfiles/re.yml
  - docs/development.md
priority: medium
ordinal: 252000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Route B artifact is x86-64 Mach-O. On an Intel Mac that runs natively; on Apple silicon the whole game process runs under Rosetta, and Apple names macOS 27 as the last release running Intel-only apps. So Route B delivers an untethered build whose arm64 future is borrowed.

Correction to the first version of this task: Route C is not a patch of a shipped macOS bundle. The developers ship no macOS build at all, which is exactly what TASK-078 asks them for. Route C is the pt-pc-style reimplementation, roughly 7,856 Assembly-CSharp bodies re-authored in C# against an upstream il2cpp runtime and built for macOS. It is therefore the only route that is both untethered and native arm64 with no expiry, and the reason it was rejected is that it costs 40 to 240 hours per content patch and fails quietly through behavioural drift. The arm64 question is accordingly not which route is faster but whether Rosetta is acceptable until macOS 27 or a reimplementation is the only durable answer.

There is an unexercised claim to close either way. The probe player is a universal x86_64 plus arm64 build but its arm64 slice has never executed: Mach-O loading picks the native slice, so on an Intel host only the Intel code runs. An arm64 leg has to be scored on Apple silicon, and it is the first real evidence that the binding path works at all on that architecture.

The metadata question does not need Apple silicon and was misframed here as needing a shipped macOS runtime that does not exist. The standalone parser reads zero classes from the shipped bundle because its il2cppmd version 24.0.0 metadata is older than the version 29 it supports. The shipped Linux runtime carries the real il2cpp implementation and is already on hand locally and on the player box, so asking that runtime to read its own metadata is runnable today. If it enumerates classes, the 0-classes finding is an artifact of the parser rather than a blocker for anything.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The probe builds and runs natively on Apple silicon with the arm64 slice confirmed by the host's own uname -sm and file output
- [ ] #2 The binding driver reports a leg that cannot run on the current architecture as not applicable rather than as a failure
- [ ] #3 The shipped runtime itself enumerates classes from its own global-metadata.dat on the Linux control leg, or the failure is characterised well enough to say whether the parser's 0-classes result is an artifact
- [ ] #4 The notes state what the untethered build is on each architecture, naming the Rosetta bound on Apple silicon and what would replace it with its cost
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
- [ ] #7 No Wine or CrossOver parity measurement is used to justify the native build
<!-- DOD:END -->
