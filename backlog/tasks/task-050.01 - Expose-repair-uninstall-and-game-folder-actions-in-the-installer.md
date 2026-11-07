---
id: TASK-050.01
title: 'Expose repair, uninstall and game-folder actions in the installer'
status: To Do
assignee: []
created_date: '2026-11-07 01:57'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-049
documentation:
  - docs/player-installer.md
  - docs/player-guide.md
parent_task_id: TASK-050
priority: medium
type: enhancement
ordinal: 184000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the existing Go installer window so common lifecycle operations do not require discovering command-line flags. Retain existing ownership-aware installation/uninstallation behavior and user confirmation. Re-running and repair are existing capabilities; this task makes them accessible and understandable to non-technical players.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The installer visibly offers appropriate install, repair/check, uninstall and open-game-folder actions based on detected state.
- [ ] #2 Destructive actions explain scope and require confirmation; cancellation, absent install records and partial failures produce clear outcomes without deleting unrelated files.
- [ ] #3 Repair restores installer-owned drift and uninstall preserves saves, unrelated mods and user-created content according to the documented ownership contract.
- [ ] #4 Lifecycle tests and GUI verification cover fresh, installed, damaged and missing-record states; player documentation uses the GUI path.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
