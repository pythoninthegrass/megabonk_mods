---
id: TASK-024.05
title: Validate native Linux runtime music bindings and playback
status: To Do
assignee: []
created_date: '2026-10-30T02:25:00Z'
labels:
  - music
  - linux
dependencies:
  - TASK-024.04
documentation:
  - docs/music.md
  - docs/development.md
parent_task_id: TASK-024
ordinal: 124000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The native clip ABI is proven only for Win64 under Wine. Native Linux support cannot be claimed by removing the guard or relying on Windows signatures; inspect that player's ABI and verify playback when the Linux machine is available.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Linux native AudioClip binding ABI is inspected and documented before enabling its production path.
- [ ] #2 A runtime mp3 is audibly confirmed on native Linux through the normal MusicTrack path.
- [ ] #3 Stage playback, boombox transitions, wrap, replay and fallback work on native Linux without invalid clip lifetime.
- [ ] #4 Platform guards and documentation match measured support; unavailable-machine blockers remain explicit rather than counting as verification.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
