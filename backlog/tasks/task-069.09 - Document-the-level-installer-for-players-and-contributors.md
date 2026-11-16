---
id: TASK-069.09
title: Document the level installer for players and contributors
status: To Do
assignee: []
created_date: '2026-11-15 06:00'
labels:
  - installer
  - docs
dependencies:
  - TASK-069.05
  - TASK-069.07
  - TASK-069.08
references:
  - docs/player-installer.md
  - docs/player-guide.md
  - pkg/README.md
  - CONTRIBUTING.md
  - docs/development.md
parent_task_id: TASK-069
priority: medium
ordinal: 245000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Several docs describe the installer as legacy, MelonLoader-only. Replace that, and give players a one-step install path, once the installer works (TASK-069.05, TASK-069.07) and is downloadable (TASK-069.08).

Edit the authoritative files under `docs/`, not the generated `site/src/content/docs/*.md`. Follow the repo's docs rules: document the content rather than task IDs, and include no PII.

Coordinate with TASK-047.02, which removes stale standalone-installer claims.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docs/player-installer.md describes the current inputs, flags, exit codes, platform behaviour and install record, and no longer calls the installer legacy
- [ ] #2 docs/player-guide.md and pkg/README.md offer the installer as the first way to install a level and the mod, with the manual steps kept as a fallback
- [ ] #3 CONTRIBUTING.md and docs/development.md reflect the current build and test commands
- [ ] #4 markdownlint passes on the changed files
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
