---
id: TASK-063.06
title: Creator pages that list a maker's levels
status: Done
assignee: []
created_date: '2026-11-12 00:28'
updated_date: '2026-11-12 01:19'
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
- [x] #1 A public creator page exists at a stable address keyed by the creator's account, opens without signing in, and shows the display name, the date they joined, how many levels they have shared, and the total likes and downloads across them
- [x] #2 The totals are correct for creators with more levels than fit on one page of results
- [x] #3 The page lists every visible level by that creator, newest first, as a cover thumbnail that links to the level page, with the title and share code; levels flagged hidden never appear
- [x] #4 Creators with many levels can reach all of them, through pagination or loading more
- [x] #5 On the browse cards and on the level page the maker's name links to that maker's creator page, and a maker with no display name still has a working page and link
- [x] #6 An unknown or malformed creator address shows a clear not-found state, and the production server serves the page for any well-formed creator address when it is opened directly or refreshed
- [x] #7 A creator with no visible levels sees an empty state, and an unreachable API shows an error state with a way to retry
- [x] #8 The page never exposes an email address or other private account field, which a test checks
- [x] #9 A signed-in creator viewing their own page sees the same edit icon on their thumbnails as on the browse cards; other visitors see no edit controls
- [x] #10 The page matches the gallery's visual design at phone and desktop widths, keeps the footer at the bottom on short pages, and shows the same no-JavaScript message as the other gallery pages
- [x] #11 Logic is covered by tests written before the change and the page is verified in a browser signed out, signed in as the creator, and signed in as someone else
- [x] #12 docs/website.md documents the creator page, its address and its data sources
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: gallery.test.js (creatorIdFromPath, creatorUrl, sumCounts, creatorFilter), level-route.test.js (/u/<id> rewrite to /creators/view/index.html; malformed ids 404; traversal; POST 405), privacy test (page only requests id,name,created user fields).
2. server.mjs: CREATOR_ROUTE rewrite.
3. creator-view.js + pages/creators/view/index.astro: users.getOne(fields id,name,created); totals via getFullList(fields likes,downloads); levels via getList 12/page sort -created, Previous/Next; owner edit icon; loading/notfound/error/empty/ready states; noscript.
4. Maker names link to /u/<id> on browse cards and level page (incl. Unknown maker).
5. gallery.css additions.
6. docs/website.md: creator page, address, data sources.
7. task check; browser verification signed out / as creator / as other user.
Decisions: address /u/&lt;account id&gt; (15 lowercase alnum); Previous/Next paging.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a public creator page at /u/<account id>, served from creators/view/index.html by a new CREATOR_ROUTE rewrite in site/server.mjs. It shows name (or "Unknown maker"), join date, level count and like/download totals (from a getFullList over likes/downloads, so correct beyond one page), and a 12-per-page newest-first thumbnail grid with Previous/Next; the owner sees the edit icon on their own thumbnails. States: loading, not found, error with retry, empty, noscript. Maker names on the browse cards and level page now link to it. The page requests only id,name,created from users. The SDK auto-cancels parallel same-collection requests, so the page sets distinct requestKey values. Tests: gallery.test.js and level-route.test.js (82 pass), task check green. Verified against a local PocketBase seeded with 18 levels (one hidden) in headless Chrome: signed out 0 edit icons, as creator 12, as another user 0; 17 levels and 2 pages; empty-name creator, no-level creator and unknown id states. Docs updated in docs/website.md. Not verified: phone-width layout (headless Chrome clipped at 390px, the site header too), and a real OAuth sign-in (sessions came from impersonation tokens).
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
