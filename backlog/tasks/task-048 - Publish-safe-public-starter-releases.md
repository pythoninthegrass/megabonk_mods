---
id: TASK-048
title: Publish safe public starter releases
status: To Do
assignee: []
created_date: '2026-11-07 01:55'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-047
priority: high
type: enhancement
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 2 of onboarding: give non-technical players a real downloadable editor/mod package and a complete starter experience without THPS or soundtrack inputs. Existing packaging and platform installers are completed groundwork, not new scope. Mod compilation currently needs locally generated Megabonk references; keep these and proprietary assets local. Public CI may check safe code and assemble approved distributable outputs from a trusted local build. Fully hosted mod compilation is not a prerequisite. Release rights for bundled dependencies must be reviewed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A public release provides verified player packages and a curated starter level requiring no external packs or music.
- [ ] #2 Release automation rejects content outside an explicit distributable allowlist and keeps proprietary inputs and generated game references out of public artifacts and caches.
- [ ] #3 Publication requires documented package validation and approval, with checksums, notices and truthful compatibility information.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
