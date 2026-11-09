---
id: TASK-047.02
title: Reconcile requirements and installer documentation
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
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
type: docs
ordinal: 175000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove contradictory onboarding claims across player and development guides. The confirmed decision is Python 3.13 for development tooling and Go-based cross-platform player installation with no Python requirement. Existing docs disagree about Python versions, whether Proton switching is automatic, installer authority and parity, and platform verification. Describe actual behavior and explicit user steps; do not revive the Python installer as the player route.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Contributor Python requirements consistently specify 3.13; player installation documentation does not require a Python interpreter.
- [ ] #2 Windows-build selection, Proton/Wine prerequisites and installer responsibilities are consistent and distinguish automatic actions from manual steps.
- [ ] #3 Installer implementation authority, parity expectations and tested platform claims no longer contradict one another.
- [ ] #4 Links and commands in changed guides are checked; remaining capability gaps are explicit rather than presented as supported behavior.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
