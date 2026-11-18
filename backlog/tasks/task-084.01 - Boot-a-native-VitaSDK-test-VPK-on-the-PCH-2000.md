---
id: TASK-084.01
title: Boot a native VitaSDK test VPK on the PCH-2000
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
labels:
  - ps-vita
  - vita-spike
dependencies: []
documentation:
  - .agents/skills/vita-port/references/toolchain.md
  - .agents/skills/vita-port/references/runtime.md
parent_task_id: TASK-084
type: task
ordinal: 286000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish a repeatable hardware bring-up and measurement baseline independent of Unity and the macOS lift.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reproducibly built, validated VPK installs and boots on a physical PCH-2000 at stock clocks with no required plugins.
- [ ] #2 Both physical sticks are observed in-app; frame timing and peak MAIN/CDRAM use are recorded.
- [ ] #3 Build, deploy and validation steps name hardware, firmware, clocks and toolchain.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
