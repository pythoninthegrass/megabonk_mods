---
id: TASK-053
title: Record the generated Forest and Desert Tier 2 stage parameters and layouts
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
  - docs/development.md
priority: medium
type: spike
ordinal: 190000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
To audit how levels are generated, the Tier 2 stages of Forest and Desert need to be measured, not just the first stage. Custom levels are capped to Tier 1 and the stock menu driver only works on Linux, so a completed Tier 2 playthrough is not a practical way to get this, and the per-generation log line holds only counts and hashes. The harness can already generate a map and stage directly, so the stage's data and its generated output can be captured and compared without playing a run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 It is established and written down which stage index of Forest and of Desert is the vanilla Tier 2 stage (for example Deep Forest), with the evidence.
- [ ] #2 For Forest and for Desert at that stage, the stage's generation parameters (grid size, height strategy and its inputs, edge fill, prop and interactable counts or multipliers, and for the procedural-mesh map its terrain and noise settings) are recorded in a document with the values read from the running game.
- [ ] #3 Each of the two stages is generated at least twice with the same forced seed and at least twice without, and the generation log lines (seed, counts, layout hash, object hash) are recorded to show what repeats and what varies.
- [ ] #4 The findings are added to docs/map-generation-determinism.md or docs/runtime-map-structure.md, and any harness or script change needed to capture them is covered by tests.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
