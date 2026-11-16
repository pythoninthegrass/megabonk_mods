---
id: TASK-080.12.06
title: Produce a complete runnable lift of the required game and runtime code
status: In Progress
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T23:30:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.01
references:
  - scripts/lift_probe.py
  - scripts/lift_holes.py
  - scripts/lift_tail_calls.py
  - scripts/pcode_lift.py
  - TASK-080.01
  - TASK-080.02
  - TASK-080.06
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 273000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The seed-81/82 samples now contain only named control-flow holes, but cover only part of the image and say nothing conclusive about runtime code outside the il2cpp section. A full native build must account for executable code reached by initialization and gameplay, including unrecovered computed jumps and body-boundary cases. This task closes build coverage, not only verifier acceptance. Do not add speculative instruction semantics for unseen operations or guess an unresolved jump is a tail call.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reproducible complete-image report accounts for the pinned game's required executable regions, including runtime code outside il2cpp, and identifies every decoded, lifted, rejected or intentionally excluded body.
- [ ] #2 Every body included in the runnable image has no unresolved semantic/control-flow hole, verifies and compiles for arm64; unhandled bodies block a runnable-build success verdict.
- [ ] #3 Recovered indirect control flow and cross-boundary targets have execution tests against the shipped reference, with unresolved and intentionally malformed cases failing safely.
- [ ] #4 The build is resumable with validated input/cache identities, preserves published baselines, and docs report actual full-build counts, output size and limitations rather than sample extrapolations.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Progress: TASK-080.12.06.01 is done. On the seed-81 and seed-82 draws (15,000 bodies each) BRANCHIND hole bodies fell 152 to 11 and 144 to 26, so the remaining holes in those samples are 11 and 26 BRANCHIND bodies plus 2 and 3 JUMPTABLE_TARGET bodies. The recorded reasons a BRANCHIND site stayed unproven are rsp not at its entry value, rsp untrackable on a path into the site, and no path in the dump reaching the site; the per-site census is in .tools/lift-probe-tailcall4-{81,82}/branchind.json. No acceptance criterion of this task is closed by it: the samples still cover a fraction of the image, and nothing yet accounts for runtime code outside the il2cpp section.

Constraint carried from the subtask: rsp at its entry value does not by itself make a jmp a tail call, since a frameless function with an unrecovered switch has the same rsp. Any later rule that lowers an unresolved jump must also require positive evidence of the target (a load from memory), and must keep the existing tests that pin computed and undefined targets as holes unchanged.
<!-- SECTION:NOTES:END -->
