---
id: TASK-050
title: Remove remaining non-technical onboarding friction
status: To Do
assignee: []
created_date: '2026-11-07 01:55'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-049
priority: medium
type: enhancement
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 4 of onboarding: turn common recovery, content-management and troubleshooting actions into discoverable UI flows after the baseline release and creator journey are verified. Extend the existing Go installer and editor rather than replacing them. Player installs must need no Python; development tooling uses Python 3.13. Preserve user saves, unrelated mods and user-owned content, and make support-data export explicit and privacy-reviewed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Players can install, repair and uninstall through discoverable GUI flows on advertised desktop platforms without Python.
- [ ] #2 Players can locate content and understand save outcomes and missing optional content without reading raw logs.
- [ ] #3 An opt-in support report provides useful diagnostics without exposing credentials or personal identifiers.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
