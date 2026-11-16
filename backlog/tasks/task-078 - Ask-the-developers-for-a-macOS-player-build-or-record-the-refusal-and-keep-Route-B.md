---
id: TASK-078
title: >-
  Ask the developers for a macOS player build, or record the refusal and keep
  Route B
status: To Do
assignee: []
created_date: '2026-11-15 23:53'
labels: []
dependencies: []
references:
  - docs/development.md
modified_files:
  - docs/development.md
priority: low
ordinal: 251000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The cheapest thing that deletes the largest Route B blocker: the developers already ship Linux and Windows player builds, so a macOS build is a build-pipeline change and not a port. With one, the shader translation pass becomes unnecessary because the game ships its own Metal shaders, and the macOS-native artifact stops depending on a locally rebuilt probe player.

This is an external request, so the task is to make it and record the answer either way. The docs already carry it as standing blocker 2; this makes it trackable and gives the refusal a place to live so the route notes do not keep re-asking.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A concrete request reaches the developers with the measured evidence already gathered
- [ ] #2 The response is recorded in docs/development.md whether it is yes, no or silence
- [ ] #3 If the answer is yes the Route B notes say which blockers the build removes
- [ ] #4 If the answer is no the notes name what replaces this ask rather than leaving it open
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
<!-- DOD:END -->
