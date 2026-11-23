---
id: TASK-080.12.07.01
title: Generate typed il2cpp API exports in the linked arm64 image
status: To Do
assignee: []
created_date: '2026-11-23T05:19:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - scripts/lift_link.py
  - scripts/lift_abi.py
  - scripts/native_runtime_probe.py
  - scripts/native_bind_probe/host.c
  - TASK-080.12.04
  - TASK-080.12.07
documentation:
  - docs/development.md
parent_task_id: TASK-080.12.07
priority: high
type: enhancement
ordinal: 297000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The linked arm64 dylib exports no typed il2cpp_* functions: the link step passes an empty export list to the adapter generator, so nothing can resolve the runtime API by name. The native runtime gate for the rebuilt shipped image stops before il2cpp_init because all 20 required exports are missing, and the matching macOS Unity player will resolve the whole API the same way. The pinned image's own export table lists 240 il2cpp_* names, so the host's 20 are a fraction of what the player needs. Exports used to reproduce startup so far are scratch adapters, not a production path. Confirmed constraints: prototypes come from the matching Unity editor's il2cpp API header, cross-checked against the image's own export table, and a disagreement between the two must fail the link, not be reconciled silently. The header is a local editor file and is never committed or copied into outputs. TASK-080.12.04 is editing the same link and ABI code at the same time (platform services, startup, weak imports); only one agent should write those files at once, and findings should pass between the two tasks as Backlog comments. Startup ordering (explicit startup entry plus a load-time constructor) is decided under TASK-080.12.04 and is not part of this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every il2cpp_* function the pinned image exports has a typed export in the linked arm64 dylib, with its prototype taken from the matching Unity editor's API header and the name set cross-checked against the image's own export table; a name present in only one source fails the link and reports both lists.
- [ ] #2 The produced image reports its exported API surface in a machine-readable file (name, signature and source per export), and the runtime integration check fails when a required export is missing from it.
- [ ] #3 A prototype the header lacks, or a signature the adapter generator cannot represent, fails closed with a named error; no export is skipped, defaulted or stubbed silently.
- [ ] #4 Generated adapters have tests for pointer, integer, boolean and void signatures, and at least one lifted function reached through a generated export returns the Linux reference value natively on arm64.
- [ ] #5 The header is read from the local editor install at build time and never copied into the repository or build outputs; developer docs say how to regenerate the exports and which Unity version is required.
- [ ] #6 Existing link behavior is unchanged: the import dispositions and counts match the previous link, the dylib still loads in a fresh arm64 process, and the full suite passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
