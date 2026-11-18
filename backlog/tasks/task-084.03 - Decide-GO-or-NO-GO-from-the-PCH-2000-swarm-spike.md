---
id: TASK-084.03
title: Decide GO or NO-GO from the PCH-2000 swarm spike
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T06:02:00Z'
labels:
  - ps-vita
  - vita-spike
dependencies:
  - TASK-084.02
documentation:
  - docs/performance.md#attributing-the-per-enemy-cost
  - .agents/skills/vita-port/references/measurement.md
parent_task_id: TASK-084
type: spike
ordinal: 288000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
An empty arena, emulator run or reduced-density demo does not establish full-port viability. This decision gates every subsequent subtask, regardless of Backlog dependency status.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Before benchmarking, record a minimum meaningful swarm density and gameplay checks against the pinned reference; use 240 enemies as a desktop comparison point, not an assumed Vita pass threshold.
- [ ] #2 At 960×544 and stock clocks on a physical PCH-2000, repeat gathered/scattered runs with matched counts up through 240 or the first documented hardware limit. Record workload, duration, counts, p95/p99, hitches and peak MAIN/CDRAM.
- [ ] #3 Record GO only if the representative gathered workload meets p95 ≤33.3 ms within 256 MiB MAIN and 112 MiB CDRAM and preserves the agreed combat feel and upgrade flow; otherwise record NO-GO or leave the gate open while evidence is missing.
- [ ] #4 On NO-GO, stop port work and mark every post-gate subtask Done with all ACs unchecked and a 'Not implemented — NO-GO' summary linking to this decision. Close the parent without checking full-port delivery.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
