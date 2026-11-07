---
id: TASK-050.04
title: Provide an opt-in privacy-safe support report
status: To Do
assignee: []
created_date: '2026-11-07 01:57'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-049
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
parent_task_id: TASK-050
priority: medium
type: enhancement
ordinal: 187000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let players export useful installation/runtime diagnostics without manually finding logs or disclosing personal machine details. Collection and export must be explicit and local by default, with review before sharing. Follow repository redaction requirements: no names, usernames, emails, account identifiers, LAN/Tailscale addresses, host-specific home paths, credentials, environment-file contents or proprietary assets. Do not automatically send reports to a service.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A discoverable user action exports a local report containing useful version, platform, compatibility, install-integrity and bounded diagnostic information.
- [ ] #2 Export is opt-in, offers review before sharing and never automatically uploads or includes proprietary inputs, environment files, credentials or unrelated files.
- [ ] #3 Sensitive identifiers and personal paths are redacted across structured fields and included log excerpts; adversarial fixtures verify redaction and collection boundaries.
- [ ] #4 Users receive clear export location/error feedback and documentation explains contents, limitations and how to share only after review.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
