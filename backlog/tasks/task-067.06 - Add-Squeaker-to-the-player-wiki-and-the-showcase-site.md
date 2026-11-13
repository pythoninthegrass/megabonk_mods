---
id: TASK-067.06
title: Add Squeaker to the player wiki and the showcase site
status: To Do
assignee: []
created_date: '2026-11-12T22:18:00Z'
labels:
  - character
  - website
dependencies:
  - TASK-067.04
references:
  - site/scripts/sync-docs.mjs
  - site/src/pages/index.astro
documentation:
  - docs/website.md
  - docs/characters.md
parent_task_id: TASK-067
type: docs
ordinal: 232000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Players finding Squeaker on the site need to learn what he is, how his stale cookie and Tiny target trait work, and how to install him. The site has no character page or section today, and the wiki is generated from an explicit docs allowlist in site/scripts/sync-docs.mjs, so the player-facing doc has to be added there rather than to the generated content directory.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A player-facing docs/squeaker.md describes Squeaker, the stale cookie, Tiny target and how to install the package
- [ ] #2 docs/squeaker.md is added to the guides allowlist in site/scripts/sync-docs.mjs and appears in the generated wiki
- [ ] #3 The showcase page has a Squeaker section or card with an in-game screenshot
- [ ] #4 The site checks pass and the new content renders, confirmed in a browser
- [ ] #5 The site's docs notes in docs/website.md reflect the added allowlist entry
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
