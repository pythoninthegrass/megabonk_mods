---
id: TASK-046
title: Cap custom levels at tier 1
status: To Do
assignee: []
created_date: '2026-11-05T20:20:00Z'
labels:
  - custom-levels
dependencies: []
references:
  - backlog/tasks/task-043 - Log-boss-spawn-and-defeat-events-in-the-mod.md
priority: medium
type: bug
ordinal: 166000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Taking the tier 2 portal from a custom level dropped the player through the level, because no custom level is built for tier 2. Custom levels should not offer progression past tier 1: find where the game decides the next tier or portal destination after a custom level's boss fight and cap it at tier 1, so a custom level never advances to a tier 2 stage. Related: tier 1 behaviour was observed in TASK-043 (A_BossDefeated True, waves continue after the kill).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A custom level cannot lead to a tier 2 stage: the tier 2 portal is absent, inert, or redirected, decided and recorded in the task
- [ ] #2 The behaviour is verified in the running game by completing the boss fight on the Warehouse
- [ ] #3 Vanilla runs are unaffected and still advance to tier 2
- [ ] #4 The rule is documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
