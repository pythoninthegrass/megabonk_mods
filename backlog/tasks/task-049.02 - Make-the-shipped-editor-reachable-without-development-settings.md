---
id: TASK-049.02
title: Make the shipped editor reachable without development settings
status: To Do
assignee: []
created_date: '2026-11-07 01:57'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-048
documentation:
  - docs/player-guide.md
  - docs/development.md
parent_task_id: TASK-049
priority: high
type: enhancement
ordinal: 182000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ensure a player who installed the public package can discover and enter the editor, return to play and resume their creation through normal game UI. Existing editor and from-scratch-level work is completed groundwork. This task addresses discoverability and any remaining development-only gates, not an editor rewrite. The creator guide task relies on the resulting user-visible access path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A fresh player-package install provides a discoverable documented path to the editor with no repository, harness, developer environment variables or source build.
- [ ] #2 The ordinary workflow permits opening the starter level, saving a named variation and returning to gameplay without losing the saved result.
- [ ] #3 Leaving or switching away from unsaved work does not silently discard edits; user-facing behavior is documented and verified.
- [ ] #4 Regression coverage where practical and a packaged runtime check establish the no-development-settings workflow.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
