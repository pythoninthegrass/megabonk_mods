---
id: TASK-052
title: Document how the game generates its maps and what random sources it uses
status: In Progress
assignee: []
created_date: '2026-11-07T23:07:00Z'
labels:
  - research
  - generation
dependencies: []
documentation:
  - docs/map-generation-determinism.md
  - docs/runtime-map-structure.md
priority: medium
type: spike
ordinal: 189000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The mod's generation log line records only counts and hashes, and the existing notes in docs/map-generation-determinism.md leave the core questions open: which function sequences generation, how the two tile-height algorithms consume randomness, what seeds the Desert and Hell terrain, how props are placed, and which random source the boss and miniboss draws use. Without those answers a level author cannot tell which parts of a generated level are fixed and which vary per run, and the custom-level work keeps hitting the same unknowns. Playing full Tier 2 runs to find out is slow and yields only the hash line, so the answers should come from the game's code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docs/map-generation-determinism.md answers each open unknown it lists, or states why it could not be answered: what sequences generation, how the Forest and Graveyard tile heights are drawn, what seed and parameters the Desert and Hell terrain generator receives, how props and interactables are placed, and which random source the enemy, miniboss and boss draws use.
- [ ] #2 Every claim names its provenance (decompiled function with its address, dump signature, or measured in the running game), and the unknowns list is updated to match what remains unconfirmed.
- [ ] #3 The write-up says which parts of a from-scratch custom level are deterministic and which still vary per run, with the evidence for each.
- [ ] #4 Any new test or tool added to support the findings is covered by tests, and markdown lint passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
