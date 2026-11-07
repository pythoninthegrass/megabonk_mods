---
id: TASK-050.03
title: 'Make content locations, save results and missing assets understandable'
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
  - docs/music.md
  - docs/asset-bundles.md
parent_task_id: TASK-050
priority: medium
type: enhancement
ordinal: 186000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reduce the need to browse raw logs or memorize UserData paths. Provide discoverable in-game access to levels, packs and local music locations, clear save feedback and actionable messages for missing optional content. Keep optional THPS and OST inputs local and opt-in; never offer automatic proprietary downloads. Existing music fallback and level loading should continue working.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Players can discover and open the relevant levels, pack and local-music folders from user-facing UI; unavailable folders or open failures receive clear guidance.
- [ ] #2 Saving reports success with the saved name/location or an actionable failure, and does not falsely clear unsaved status after failure.
- [ ] #3 A missing pack identifies the dependency and recovery action before a confusing placeholder-only play experience; missing custom music explains stock-music fallback.
- [ ] #4 Absent optional content never triggers an unauthorized download or blocks the self-contained starter experience; runtime checks, regression tests where practical and player docs cover these cases.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
