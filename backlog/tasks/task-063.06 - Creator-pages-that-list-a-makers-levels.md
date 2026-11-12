---
id: TASK-063.06
title: Creator pages that list a maker's levels
status: To Do
assignee: []
created_date: '2026-11-12 00:28'
labels:
  - website
  - sharing
dependencies:
  - TASK-063.03
documentation:
  - docs/website.md
  - site/src/pages/levels/index.astro
  - site/src/pages/levels/view/index.astro
  - site/server.mjs
parent_task_id: TASK-063
priority: medium
ordinal: 221000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A level's maker is shown only as plain text on the browse cards and the level page, so a creator has no single place that shows everything they have shared and a visitor who likes one level cannot find the maker's others. Add a public creator page that gives each creator a central listing: basic metadata about the creator and a thumbnail link to every one of their submissions.

Context for a fresh session: the gallery is a static site whose pages fetch from a separate PocketBase API in the browser. Accounts are created only through GitHub, Google or Discord sign-in. The account list and view endpoints are public so a level can show its maker, and email addresses are hidden; the public fields are the account id, display name and created date. A display name may be empty (pages then show "Unknown maker") and is not guaranteed to be unique, so a creator must be identified by something stable such as the account id, never by name. Levels have a cover picture, share code, title, tags, like and download counts, and a hidden flag that removes a level from public listings. The static server rewrites level share links to one page that reads the code from the address; a creator page needs the same kind of support so its address works when opened directly. Level pages are at `/l/<code>` and the browse page at `/levels/`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A public creator page exists at a stable address keyed by the creator's account, opens without signing in, and shows the display name, the date they joined, how many levels they have shared, and the total likes and downloads across them
- [ ] #2 The totals are correct for creators with more levels than fit on one page of results
- [ ] #3 The page lists every visible level by that creator, newest first, as a cover thumbnail that links to the level page, with the title and share code; levels flagged hidden never appear
- [ ] #4 Creators with many levels can reach all of them, through pagination or loading more
- [ ] #5 On the browse cards and on the level page the maker's name links to that maker's creator page, and a maker with no display name still has a working page and link
- [ ] #6 An unknown or malformed creator address shows a clear not-found state, and the production server serves the page for any well-formed creator address when it is opened directly or refreshed
- [ ] #7 A creator with no visible levels sees an empty state, and an unreachable API shows an error state with a way to retry
- [ ] #8 The page never exposes an email address or other private account field, which a test checks
- [ ] #9 A signed-in creator viewing their own page sees the same edit icon on their thumbnails as on the browse cards; other visitors see no edit controls
- [ ] #10 The page matches the gallery's visual design at phone and desktop widths, keeps the footer at the bottom on short pages, and shows the same no-JavaScript message as the other gallery pages
- [ ] #11 Logic is covered by tests written before the change and the page is verified in a browser signed out, signed in as the creator, and signed in as someone else
- [ ] #12 docs/website.md documents the creator page, its address and its data sources
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
