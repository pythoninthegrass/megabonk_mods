---
id: TASK-080.12.07
title: Initialize the rebuilt shipped IL2CPP runtime natively on macOS
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.02
  - TASK-080.12.03
  - TASK-080.12.04
  - TASK-080.12.05
  - TASK-080.12.06
references:
  - scripts/native_bind_probe.py
  - scripts/native_bind_probe/host.c
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 274000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The existing native-bind probe proves the official probe-player runtime on macOS and the shipped runtime on Linux separately, not the rebuilt shipped runtime on macOS. This integration gate consumes the calling interface, relocated image, platform services and complete lift from sibling tasks. It must load the shipped metadata rather than substitute the probe project's assemblies. No Unity window, graphics or mod-loader detour is required at this gate.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A bounded native arm64 host loads the rebuilt shipped runtime and matching metadata, initializes a non-null domain, attaches a thread and enumerates the expected game assemblies/classes.
- [ ] #2 The required public il2cpp API surface is callable and identified in the produced image; missing exports fail the integration check.
- [ ] #3 The managed-method ladder returns the shipped reference values, including a game-authored Assembly-CSharp method, with binary/metadata hashes and non-translated process evidence recorded.
- [ ] #4 Missing/mismatched metadata and startup failure are diagnosed without leaving orphan processes; regression tests and docs reproduce a clean startup and shutdown.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
