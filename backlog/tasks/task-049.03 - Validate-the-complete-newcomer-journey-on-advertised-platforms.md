---
id: TASK-049.03
title: Validate the complete newcomer journey on advertised platforms
status: To Do
assignee: []
created_date: '2026-11-07 01:57'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-049.01
  - TASK-049.02
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
parent_task_id: TASK-049
priority: high
type: task
ordinal: 183000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate the actual public release rather than a development install. Use clean game/mod state and the documented player and creator steps on each advertised OS/architecture. Existing Windows VM, Linux/Proton and macOS/Wine findings are prior evidence, not a substitute for checking the current download. Involve a person unfamiliar with the repository for the usability pass and record privacy-safe findings. Never destroy existing saves or unrelated mods to obtain clean state.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A support matrix records actual package/version, OS/architecture, game build and runtime for each tested advertised platform, distinguishing physical hardware, VM and unverified claims.
- [ ] #2 The documented browser download, extraction, install, first launch, starter play, editor entry, save, replay, sharing and uninstall lifecycle is verified without contributor tools or Python.
- [ ] #3 Checks include delayed first launch, missing optional assets, repair and preservation of saves/unrelated content; failures are recorded rather than counted as successful support.
- [ ] #4 A newcomer usability pass records where assistance was needed; blocking findings are resolved or prevent the affected support claim, and guides reflect the observed flow.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
