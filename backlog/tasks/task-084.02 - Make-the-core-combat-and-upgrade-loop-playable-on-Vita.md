---
id: TASK-084.02
title: Make the core combat and upgrade loop playable on Vita
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T06:02:00Z'
labels:
  - ps-vita
  - vita-spike
dependencies:
  - TASK-084.01
documentation:
  - .agents/skills/vita-port/SKILL.md
  - docs/development.md#openbonk-reconstruction-on-native-macos
parent_task_id: TASK-084
type: spike
ordinal: 287000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Keep the feasibility build small enough to test the feel of Megabonk without committing to the original engine, full asset pipeline or all content. Use original placeholders and a Forest-style graybox.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On the PCH-2000, one character moves and aims with the physical controls, fights a swarm with one automatic weapon, picks up XP and earns an upgrade.
- [ ] #2 Selecting an upgrade through the normal UI applies it once and resumes combat.
- [ ] #3 A repeatable benchmark scenario can vary live enemy count and place equally sized groups in gathered and scattered layouts, with no bypass in ordinary play.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
