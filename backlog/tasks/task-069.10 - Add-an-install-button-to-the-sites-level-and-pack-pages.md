---
id: TASK-069.10
title: Add an install button to the site's level and pack pages
status: To Do
assignee: []
created_date: '2026-11-15 06:00'
labels:
  - installer
  - site
dependencies:
  - TASK-069.08
references:
  - site/src/pages/levels/view/index.astro
  - site/src/scripts/level-view.js
  - docs/website.md
parent_task_id: TASK-069
priority: low
ordinal: 246000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A player who lands on a megabonkmod.party level page currently gets manual copy-into-folder steps. Offer the installer from that page instead, linking each platform's release binary (TASK-069.08) and showing the share code to paste into it. Keep the manual steps as a fallback.

Website work lives in `site/`; follow `docs/website.md`. Pushing to main deploys the site.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The level page links the installer download for the visitor's platform and lists the other platforms
- [ ] #2 The page shows the share code with a copy button and tells the player to paste it into the installer
- [ ] #3 The manual install steps remain available
- [ ] #4 Site checks pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
