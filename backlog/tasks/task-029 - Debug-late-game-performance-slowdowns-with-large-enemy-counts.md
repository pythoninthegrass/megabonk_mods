---
id: TASK-029
title: Debug late-game performance slowdowns with large enemy counts
status: To Do
assignee: []
created_date: '2026-11-02T04:32:00Z'
labels: []
dependencies: []
priority: medium
type: spike
ordinal: 136000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Late in a run, once stage scaling has spawned a large number of enemies, the game slows down noticeably. Where the frame time goes at high enemy counts is unknown. Stock systems that scale with enemy count include per-enemy Rigidbody movement, minimap icon updates, animations and effects; the mod adds its own per-frame work on the same population (the kill-floor watcher scanning EnemyManager.enemies, the dev readout's enemy scans, Harmony prefixes on hot paths). Diagnose and attribute the cost so any fix targets the real bottleneck instead of a guess — the same pattern as TASK-027's diagnosis-first split.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A repeatable profiling method for a late-game run with a large enemy count exists (harness-driven, spawns on, invulnerable player, forced stage/tier) and is documented in docs/development.md
- [ ] #2 Frame-time attribution identifies the top cost centers with measurements, separating stock game systems from mod-added per-frame work
- [ ] #3 Every mod-side cost that scales with enemy count is measured; small ones are fixed in this task and larger ones are filed as follow-up tasks with the measurement attached
- [ ] #4 Findings are written up in docs: what scales with enemy count and what does not, so future performance work starts from evidence
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
