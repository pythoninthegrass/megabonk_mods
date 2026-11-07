---
id: TASK-048.04
title: Automate approved starter packages and draft release publication
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-048.01
  - TASK-048.02
  - TASK-048.03
documentation:
  - docs/player-installer.md
  - docs/player-guide.md
  - README.md
parent_task_id: TASK-048
priority: high
type: enhancement
ordinal: 180000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Turn the existing package commands into a reliable GitHub Releases download path. Trusted local compilation provides approved distributable mod outputs because game-reference assemblies remain local; fully hosted mod compilation is not required. Release publication consumes only allowlisted outputs plus approved dependencies and starter content. Preserve a human approval gate. Existing packaging work is reusable groundwork, not a replacement project.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An authorized release flow assembles clearly named per-platform packages from trusted approved mod outputs, Go installers, pinned dependencies and the curated starter level.
- [ ] #2 A draft release includes checksums, dependency notices, version/game-build compatibility, first-launch expectations and known platform limitations.
- [ ] #3 Package integrity and safe-content checks must pass before upload; public publication requires explicit approval after a documented smoke test.
- [ ] #4 A published starter release is downloadable without contributor tools, and README/player-guide placeholders are replaced with verified release links.
- [ ] #5 Maintainer documentation explains trusted-input provenance, validation, approvals and failure recovery without exposing private inputs or credentials.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
