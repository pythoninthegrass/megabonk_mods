---
id: TASK-004.06.01
title: 'Dev harness: controlled nonlethal player damage for low-health testing'
status: To Do
assignee: []
created_date: '2026-10-30T03:00:00Z'
labels:
  - dev-harness
  - testing
dependencies: []
references:
  - TASK-024
  - TASK-004.10
documentation:
  - docs/development.md
  - docs/music.md
parent_task_id: TASK-004.06
priority: medium
type: enhancement
ordinal: 125000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The harness exposes kill and invulnerability but cannot apply controlled, nonlethal player damage. Testing low-health reactions currently requires waiting for enemies and risks losing the run. During runtime-music testing, Lance used a stone golem and confirmed that the audio slows dramatically as expected; danger modulation is working, not an outstanding audio defect. A repeatable damage control would make this and other damage-driven behavior testable without enemy timing. Changing HP alone is insufficient when reactions depend on damage history.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 MCP and run.py expose a controlled player-damage command with an explicit requested amount.
- [ ] #2 The command is nonlethal by default, preserving at least 1 HP and never silently ending the run.
- [ ] #3 Damage exercises the game's normal damage-driven reactions rather than merely overwriting HP or forcing music pitch.
- [ ] #4 Results report requested versus actual damage and before/after HP, max HP, shield and overheal; blocked or clamped damage is explicit.
- [ ] #5 Invalid amounts and missing/dead players are rejected without unintended state changes; shield, invulnerability and damage-cooldown behavior is documented and tested.
- [ ] #6 Pure validation and command parsing tests are written first; CLI/MCP coverage and docs/development.md describe usage and safety limits.
- [ ] #7 In-game verification demonstrates controlled nonlethal damage and a low-health danger reaction on the default Wine setup; human audible confirmation is distinguished from source-state checks.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
