---
id: TASK-080.12.08
title: Boot the rebuilt game headlessly in the matching arm64 Unity player
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.07
references:
  - scripts/native_bind_probe.py
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 275000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A standalone IL2CPP domain does not establish Unity integration. The next gate pairs the rebuilt shipped runtime with the official macOS arm64 Unity 2023.2.22f1 player and the game's own data. Engine calls, managed startup and native plugin requirements must be measured in the player rather than inferred from exported symbols. This task stops at headless game initialization; rendering and device behaviour are separate tasks. Keep reference saves isolated and all game-derived content local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A repeatable headless launch uses the matching official Unity player, rebuilt arm64 game runtime and shipped metadata/assets, and proves every loaded executable image is compatible with native arm64 execution.
- [ ] #2 The game's managed startup reaches a documented menu-ready or equivalent headless checkpoint, with required engine calls resolved and no silently bypassed fatal initializer.
- [ ] #3 Missing engine calls, native plugins or incompatible data versions produce actionable diagnostics; a bounded run shuts down without orphan processes or changing reference saves.
- [ ] #4 An integration smoke check and developer docs record prerequisites, provenance, checkpoint evidence and any headless-only limitations.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
