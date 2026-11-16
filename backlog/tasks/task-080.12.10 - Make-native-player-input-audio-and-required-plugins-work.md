---
id: TASK-080.12.10
title: 'Make native player input, audio and required plugins work'
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.08
references:
  - TASK-076
  - TASK-074
  - docs/gamepadui.md
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 277000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A rendering menu is not a playable native port. The rebuilt Linux game may depend on platform-specific input, audio, controller or Steam/native-plugin behaviour that the matching macOS player alone does not supply. This task validates that boundary with the shipped game code rather than treating a successful dynamic-library load as compatibility. Target normal offline play without requiring a Steam session; any intentionally unavailable Steam-only features must be explicit. Do not overwrite progression in reference profiles.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A native dependency inventory accounts for required plugins, their arm64 compatibility and runtime bindings; unavailable optional services are explicitly reported rather than silently spoofed as working.
- [ ] #2 Keyboard/mouse input, text entry and the supported controller flow navigate menus and control gameplay correctly in the native player.
- [ ] #3 Music and effects play and respond to pause/resume and volume controls, with device initialization failures diagnosed instead of hanging startup.
- [ ] #4 Offline startup and isolated save-path selection work without a Steam session; repeatable smoke evidence, regression tests for testable logic and docs cover supported devices and feature exclusions.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
