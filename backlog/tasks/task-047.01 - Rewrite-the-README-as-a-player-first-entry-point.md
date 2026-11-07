---
id: TASK-047.01
title: Rewrite the README as a player-first entry point
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-047.02
documentation:
  - README.md
  - docs/player-guide.md
  - docs/modding-setup.md
parent_task_id: TASK-047
priority: high
type: docs
ordinal: 174000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The root README currently describes a source repository and links to two guides. Replace that first impression with a concise explanation of playing, creating and sharing custom levels. Keep developer setup separate. Python 3.13 belongs only to contributor requirements; players use Go installers. The public release task supplies actual downloads later, so do not invent a working download link before publication.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README has description, minimum requirements, recommended setup, quickstart and development H2 sections, with creator and optional-content navigation.
- [ ] #2 Players can distinguish required Megabonk ownership, supported game build and first-launch internet needs from optional creator/developer tooling.
- [ ] #3 Quickstart describes download, extract, install, launch and select the starter level; availability and platform limitations are honest.
- [ ] #4 No unsupported hardware requirements or development commands are presented as player prerequisites.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
