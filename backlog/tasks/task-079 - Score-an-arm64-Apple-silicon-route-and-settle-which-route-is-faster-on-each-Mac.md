---
id: TASK-079
title: >-
  Score an arm64 Apple silicon route and settle which route is faster on each
  Mac
status: To Do
assignee: []
created_date: '2026-11-15 23:53'
updated_date: '2026-11-16 00:10'
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
The Route B artifact is x86_64 Mach-O. On an Intel Mac that runs natively, but on Apple silicon it runs under Rosetta, and Apple names macOS 27 as the last release running Intel-only apps, so B's arm64 future is borrowed. Route C patches the shipped universal bundle instead, so it runs native arm64 with no translation and no expiry. The routes have not been compared on the axis that matters here: frame time on the actual fleet.

There is also an unexercised claim to close. The probe player is a universal x86_64 plus arm64 build but its arm64 slice has never executed: Mach-O loading picks the native slice, so on an Intel host only the Intel code runs. An arm64 leg has to be scored on Apple silicon, and it is the first real evidence that the binding path works at all on that architecture.

The shipped macOS runtime offers a second and possibly decisive measurement. The standalone metadata parser reads zero classes from the shipped bundle because its il2cppmd version 24.0.0 metadata is older than the version 29 the parser supports, but the shipped UnityPlayer carries the runtime itself with 111732 il2cpp methods. Asking that runtime to read its own metadata is a different code path, and if it enumerates classes then the 0-classes finding is an artifact of the parser rather than a blocker for Route C.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The probe builds and runs natively on Apple silicon with the arm64 slice confirmed by the host's own uname -sm and file output
- [ ] #2 The shipped macOS UnityPlayer is bound by symbol and reports its il2cpp_* export count and managed-body count
- [ ] #3 The bound runtime enumerates classes from its own metadata or the failure is characterised
- [ ] #4 Frame time of the current Wine-based path is measured on each Mac in the fleet and recorded
- [ ] #5 The notes state which route is the performance target on Apple silicon and which on Intel, with the numbers behind it
- [ ] #6 Add an n/a leg status to the shared binding driver so an architecture that cannot run a leg is reported as not applicable rather than as a failure
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
<!-- DOD:END -->
