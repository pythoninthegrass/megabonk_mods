---
id: TASK-080.12.12
title: Load and exercise the level-editor mod in the native arm64 game
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
updated_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.09
  - TASK-079
references:
  - TASK-079
  - src/
  - scripts/run.py
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 279000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Native game execution and mod support are separate contracts. TASK-079 already owns proof of an arm64 detour; this task consumes it to make the actual level-editor mod run against the rebuilt shipped runtime. A successful hook in the probe player is not evidence that plugin loading, interop and the editor work in the game. Do not assume the Windows BepInEx deployment is portable unchanged or replace the game with a mod-only demonstration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The actual level-editor plugin loads in the rebuilt arm64 game with the required managed/native runtime and interop bindings, and reports a successful startup rather than only a chainloader initialization.
- [ ] #2 Required game hooks fire on native arm64 and preserve original behaviour; plugin initialization failure yields actionable logs without corrupting saves.
- [ ] #3 A native rendered smoke test creates or loads a custom level, edits it, saves, reloads and plays it, with the harness receiving actual game responses.
- [ ] #4 Tests cover testable loader/harness failure paths, and docs describe the supported native mod stack and deployment prerequisites.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
