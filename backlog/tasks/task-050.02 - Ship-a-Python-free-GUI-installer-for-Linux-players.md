---
id: TASK-050.02
title: Polish the Python-free Linux installer desktop experience
status: To Do
assignee: []
created_date: '2026-11-07 01:57'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-049
  - TASK-050.01
documentation:
  - docs/player-installer.md
  - docs/player-guide.md
  - docs/modding-setup.md
parent_task_id: TASK-050
priority: medium
type: enhancement
ordinal: 185000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Polish the established cross-platform Go installer as a non-technical Linux desktop experience. Go already provides cross-platform installs; do not rebuild it or reintroduce a player Python dependency. The starter release phase supplies Go-based packages. This task improves graphical launch, desktop integration and fallback usability of that existing package, with accurate Steam/Flatpak and Proton guidance. Developer Python remains 3.13. Do not claim automatic game-build switching.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The public Linux player package installs through the Go binary without Python, Go, uv or a repository on the player's machine.
- [ ] #2 The documented graphical launch path opens the confirmation/progress/result UI on supported desktops; missing GUI support provides a clear usable fallback.
- [ ] #3 Executable permissions, extraction and desktop security friction are checked using a browser-downloaded package on supported Linux setups.
- [ ] #4 Fresh install, check/repair and uninstall are verified with Python unavailable, including supported Steam discovery scenarios; all player guides describe the resulting entry point.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
