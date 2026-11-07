---
id: TASK-048.01
title: Curate a self-contained starter level for public downloads
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-047
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
parent_task_id: TASK-048
priority: high
type: enhancement
ordinal: 177000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Give the default player package a small polished level suitable for first play and a first edit. Existing level files include development regression maps; do not indiscriminately bundle them. The starter must work using the owned game's runtime resources and approved distributable project content, without THPS packs or soundtrack files.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The default public player package includes one clearly titled, playable starter level with an appropriate publicly distributable selection image.
- [ ] #2 First play works with no optional packs or custom music installed and produces no missing-content placeholders.
- [ ] #3 The level supports a simple edit-save-replay tutorial and excludes scratch/regression maps from the default experience.
- [ ] #4 A packaged runtime smoke test and starter-content documentation establish the expected first-play result.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
