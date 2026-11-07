---
id: TASK-048.03
title: Add public CI for game-independent checks and installer builds
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-047
  - TASK-048.02
references:
  - 'https://docs.github.com/en/actions/reference/security/secure-use'
documentation:
  - docs/development.md
  - docs/player-installer.md
parent_task_id: TASK-048
priority: high
type: chore
ordinal: 179000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use GitHub Actions to provide useful public PR validation without acquiring a game install or uploading generated game references. Build on existing test and Go installer capabilities. Python development jobs use 3.13. The full mod build requires local game references and is outside hosted CI scope until a separately approved reference strategy exists. Public PR code must never run on a maintainer workstation holding proprietary assets or secrets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Public PR CI runs the designated game-independent checks and builds supported Go installer targets without proprietary inputs or a local game installation.
- [ ] #2 Python jobs use 3.13 and required checks distinguish genuine failures from intentionally unavailable generated artifacts.
- [ ] #3 Untrusted PR jobs have no publishing secrets, privileged execution path or access to asset-bearing self-hosted machines; actions use immutable pins and least-privilege permissions.
- [ ] #4 Contributor docs identify hosted checks, excluded game-dependent validation and how required results are interpreted.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
