---
id: TASK-049.01
title: Document the first edit-save-play-share creator journey
status: To Do
assignee: []
created_date: '2026-11-07 01:57'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-049.02
documentation:
  - docs/player-guide.md
  - docs/level-format.md
  - docs/music.md
parent_task_id: TASK-049
priority: high
type: docs
ordinal: 181000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a short non-technical creator quickstart using the public starter level. The release phase provides the downloadable package and starter content; the ordinary-editor-access subtask establishes the supported UI path. Do not route creators through development harness commands, environment variables, source builds or Unity. Optional packs and local MP3s are separate advanced choices, never tutorial prerequisites.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A creator guide linked from the README and player guide covers opening the editor, changing one object, undoing, saving under a new name, replaying and sharing.
- [ ] #2 Steps use the ordinary shipped UI, name the save location and shared files, and include publicly distributable screenshots where recognition matters.
- [ ] #3 The guide explains optional pack dependencies and local music without requiring either or suggesting redistribution of proprietary content.
- [ ] #4 The tutorial is exercised against the packaged starter level without contributor tools or development flags; observed steps match the guide.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
