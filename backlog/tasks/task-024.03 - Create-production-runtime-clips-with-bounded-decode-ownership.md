---
id: TASK-024.03
title: Create production runtime clips with bounded decode ownership
status: To Do
assignee: []
created_date: '2026-10-30T02:24:00Z'
labels:
  - music
dependencies:
  - TASK-024.02
documentation:
  - docs/music.md
parent_task_id: TASK-024
ordinal: 122000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The successful native mp3 probe is diagnostic and retains whole-track PCM. Production playback needs reusable clip creation and bounded lifetime without replacing the game's music processing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The native probe and production playback share the verified native AudioClip creation path with platform guards.
- [ ] #2 Current track and one prefetched successor have bounded decode and clip ownership, including limits for oversized or malformed input.
- [ ] #3 Track replacement and cancellation release obsolete buffers and Unity objects safely, including rapid switches and leaving a run.
- [ ] #4 Testable decode and ownership policies have tests written first; diagnostic commands retain their behavior and documentation is updated.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
