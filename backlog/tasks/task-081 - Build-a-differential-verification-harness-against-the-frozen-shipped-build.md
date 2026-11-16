---
id: TASK-081
title: Build a differential verification harness against the frozen shipped build
status: To Do
assignee: []
created_date: '2026-11-16 00:31'
labels: []
dependencies: []
references:
  - docs/development.md
modified_files:
  - scripts/
  - tests/
  - taskfiles/
  - docs/development.md
priority: high
ordinal: 254000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The reason Route C, the reimplementation, lost to Route B is that it fails quietly: a port whose behaviour drifted would still launch and play, and every harness result would become a statement about the port instead of about the game. That failure mode was accepted as unmeasurable and used as a decisive argument, which means it is currently a belief. It is also the thing standing between this project and the only arm64-native, untethered, non-expiring build.

The freeze that removed the other argument against Route C makes this measurable. The shipped build can never change underneath a reference capture, so a golden corpus is durable rather than maintained: a fixed set of scenarios, each a forced seed plus a scripted input sequence driven by the existing dev harness, scored by a machine-readable state snapshot and screenshot hashes captured from the shipped build on Linux, then replayed against any candidate build with per-field differences counted rather than eyeballed. That converts silent drift into counted drift and gives the route decision a number instead of a worry.

The ordering matters. Before the corpus can judge a port it has to prove it can agree with itself: the same scenario replayed twice on the reference has to produce identical output, otherwise the harness is measuring its own nondeterminism. Seed determinism of map generation is already established elsewhere in this project, so the remaining nondeterminism to hunt is in timestamps, float ordering, iteration order, entity ids and anything the harness itself perturbs.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
