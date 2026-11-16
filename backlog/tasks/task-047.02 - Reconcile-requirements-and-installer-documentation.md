---
id: TASK-047.02
title: Remove stale standalone-installer claims from current guides
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-14 23:03'
labels:
  - onboarding
dependencies: []
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-047
priority: high
ordinal: 175000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reconcile the remaining onboarding contradictions after the BepInEx/Thunderstore cutover. The current player route is the runtime-only Thunderstore package and a compatible mod manager, with manual Windows-build/Proton/Wine prerequisites. Player installation needs no Python or Go. Contributor tooling uses the pinned Python 3.13 baseline. The Go installer is retained legacy code, not the current player installer. Keep historical installer documentation explicitly historical; do not revive that distribution route.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Current player and contributor guides consistently distinguish Python-free runtime installation from Python 3.13 contributor tooling.
- [ ] #2 Current guides describe manual Windows-build selection and Proton/Wine prerequisites without implying the legacy installer performs them.
- [ ] #3 Remove current-support claims for internal package:linux/windows/macos tasks, default starter bundling and the Go installer being the only player installer; historical commands are clearly identified as legacy.
- [ ] #4 Check changed links and commands and preserve accurate tested-platform limitations without claiming unverified support.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-14 audit: BepInEx migration supersedes the original Go-installer authority/parity scope. Concrete remaining contradictions: docs/development.md player-installer section and 'only player installer' claim; docs/gamepadui.md player-package Python 3.11 claim; docs/starter-level.md default per-platform packaging paragraph; docs/level-format.md task package:linux example; docs/player-installer.md current-sounding unpublished-download instructions. These are genuine documentation work, so retain To Do rather than mark Done or archive.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
