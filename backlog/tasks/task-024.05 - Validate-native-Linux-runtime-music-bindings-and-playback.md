---
id: TASK-024.05
title: Validate runtime music playback on Linux through Windows Proton on mf
status: To Do
assignee: []
created_date: '2026-10-30T02:25:00Z'
updated_date: '2026-11-02T04:50:00Z'
labels:
  - music
  - linux
dependencies:
  - TASK-024.04
documentation:
  - docs/music.md
  - docs/development.md
  - docs/gamepadui.md
parent_task_id: TASK-024
ordinal: 124000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate the existing Win64 runtime music path on Linux using the Windows build under Proton on SSH host mf. Lance explicitly chose Windows/Proton for every Linux machine; no Linux box should run the native Linux build. This supersedes the former native-Linux ABI inspection and playback requirement. Do not install or switch to the native Linux depot, remove the native-Linux platform guard, or claim native Linux support. Use docs/gamepadui.md for remote Steam/Proton setup and verify the installed Windows depot and active Proton runtime before testing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Confirm mf is running the Windows build under Proton (Windows depot 3405342 and active prefix/runtime evidence), not the native Linux build.
- [ ] #2 A runtime mp3 is audibly confirmed on mf through the normal MusicTrack path under Proton; human listening confirmation is recorded separately from automated source-state checks.
- [ ] #3 Stage playback, boombox transitions, wrap, replay and missing/unreadable/undecodable fallback work under Proton on mf without invalid clip lifetime.
- [ ] #4 Native Linux remains unsupported and guarded; documentation and the parent task reflect Windows/Proton as the Linux-host target, with any access or verification blockers explicitly recorded.
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
Platform decision from Lance (2026-11-01): mf is the Linux host; all Linux machines must use the Windows build under Proton, never the native Linux build. Replaced obsolete native-Linux ABI/playback acceptance criteria with Proton validation. No playback verification performed or acceptance criteria completed by this update. Parent TASK-024 still contains superseded native-Linux wording and must be reconciled as part of this task.
<!-- SECTION:NOTES:END -->
