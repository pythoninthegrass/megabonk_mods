---
id: TASK-080.12
title: Deliver a native arm64 Megabonk build on Apple silicon
status: To Do
assignee: []
created_date: '2026-11-16T19:03:00Z'
updated_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - TASK-077
  - TASK-079
  - TASK-081
  - TASK-080.11
  - TASK-080.12.01
  - TASK-080.12.02
  - TASK-080.12.03
  - TASK-080.12.04
  - TASK-080.12.05
  - TASK-080.12.06
  - TASK-080.12.07
  - TASK-080.12.08
  - TASK-080.12.09
  - TASK-080.12.10
  - TASK-080.12.11
  - TASK-080.12.12
  - TASK-080.12.13
documentation:
  - docs/development.md
parent_task_id: TASK-080
priority: high
type: feature
ordinal: 267000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The liftability spike now compiles sampled shipped code for arm64, including both observed SSE userop gaps, but no lifted real game body has executed and no native game build boots. This delivery follow-up targets the local Apple silicon development machine and Route B-prime: preserve shipped game behaviour while pairing rebuilt arm64 game code with the matching macOS Unity player. Wine, CrossOver, Rosetta and a reimplementation are not the target. The frozen Linux game is the behavioural reference; the locally built probe player is not evidence of shipped-game execution. Existing shader-tail, arm64-hook and gameplay-oracle work remains in TASK-077, TASK-079 and TASK-081. Preserve completed spike results and published measurement baselines. Game binaries, assets and metadata stay local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An arm64-only execution path runs the shipped game's rebuilt code in the matching macOS Unity player, with per-run evidence that the process is not translated.
- [ ] #2 The game reaches its menu and completes a playable run with verified graphics, input, audio and save/reload behaviour against the shipped reference.
- [ ] #3 The native build loads the level-editor mod and passes a create/edit/save/reload/play smoke test without Wine, CrossOver or Rosetta.
- [ ] #4 A reproducible local build/package workflow and documented prerequisites produce the tested app without placing proprietary game content in tracked or public outputs.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Delivery work is recorded in 13 To Do subtasks, all unassigned. Start with TASK-080.12.01 (first real shipped-body native execution), then calling bridges (.02). Image relocation (.03), platform compatibility (.04), unwinding (.05) and full-code coverage (.06) converge on shipped IL2CPP initialization (.07), followed by headless Unity boot (.08). Rendering (.09, with existing TASK-077) and device/plugin support (.10) converge on gameplay/save parity (.11, consuming existing TASK-081). Native mod support (.12) consumes rendering and existing arm64 detour TASK-079. Packaging (.13) waits on gameplay parity and native mod support. Dependencies are recorded on each subtask; no implementation has started and no research/implementation plan is prescribed by these creation records. The completed TASK-080 spike and existing shader/hook/oracle tasks are not reopened or duplicated.
<!-- SECTION:NOTES:END -->
