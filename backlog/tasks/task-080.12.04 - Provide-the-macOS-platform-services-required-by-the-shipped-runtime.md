---
id: TASK-080.12.04
title: Provide the macOS platform services required by the shipped runtime
status: To Do
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.01
references:
  - scripts/elf_shim_probe.py
  - scripts/native_bind_probe/symprobe.c
  - TASK-076
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 271000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The ELF shim probe classifies imports as feasible but implements no working compatibility layer. Its 66-symbol work estimate includes Linux/macOS ABI differences; symbol lookup success alone does not prove compatible structures or semantics. The frozen image also requires per-thread state and ordered initialization. This task provides the platform behaviour consumed by the rebuilt arm64 image, not a generic Linux emulator. Gettext passthrough is not presumed safe merely because the symbols can be stubbed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every reachable platform import required by the pinned image has a tested native arm64 binding, compatibility implementation or explicitly justified unused/no-op classification; no unresolved import is silently ignored.
- [ ] #2 ABI-divergent services used by the runtime preserve observable Linux behaviour, including applicable threading, signal, file and locale cases, with shipped-reference evidence where available.
- [ ] #3 Concurrent threads get independent initialized TLS; required startup hooks execute once in the correct order and final memory protections are enforced before normal execution.
- [ ] #4 Automated failure-path tests and developer docs cover unsupported services, locale/catalog assumptions and reproduction of the import/startup evidence.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
