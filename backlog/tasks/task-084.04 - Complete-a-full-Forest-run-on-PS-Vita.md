---
id: TASK-084.04
title: Complete a full Forest run on PS Vita
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-19T03:16:00Z'
labels:
  - ps-vita
  - vita-delivery
dependencies:
  - TASK-084.03
documentation:
  - .agents/skills/vita-port/SKILL.md
parent_task_id: TASK-084
type: feature
ordinal: 289000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start only after the PCH-2000 swarm gate explicitly records GO (recorded in TASK-084.03; see docs/vita-combat.md "Gate verdict"). Turn the graybox loop into the first end-to-end stage. Use the pinned build as the behavioral reference and OpenBonk's reconstructed C# as the readable spec for gameplay systems, transliterated into the host-tested C core under vita/combat/. Credit OpenBonk as the source of the reused logic. Scope this task to a vertical slice: one character through Forest, with every other character, stage and content category left to TASK-084.05. Keep all game-derived artifacts local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On a physical PCH-2000, one character goes from character selection through Forest map generation, traversal, combat and upgrades to a boss and normal run resolution.
- [ ] #2 Death and restart work, and earned offline progression survives a clean relaunch without touching desktop saves.
- [ ] #3 A representative full run records frame pacing, peak memory and any regressions against the GO benchmark.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Pick the Forest systems the slice needs (map generation, one character, its weapon, the enemy and boss set used in Forest, XP and upgrade offers, run resolution) and port them one at a time into vita/combat/ with host tests written first, using OpenBonk's C# as the behavioral spec and the pinned build to settle disagreements. Credit OpenBonk in the docs.
2. Convert Forest assets offline into a local-only Vita format; keep the converted data out of the repository and the VPK.
3. Run the slice on the PCH-2000 and record frame pacing and peak memory against the GO benchmark.
<!-- SECTION:PLAN:END -->
