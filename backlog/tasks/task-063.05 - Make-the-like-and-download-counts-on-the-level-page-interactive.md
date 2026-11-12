---
id: TASK-063.05
title: Make the like and download counts on the level page interactive
status: Done
assignee: []
created_date: '2026-11-12 00:28'
updated_date: '2026-11-12 00:51'
labels:
  - website
  - sharing
dependencies:
  - TASK-063.03
documentation:
  - docs/website.md
  - site/src/pages/levels/view/index.astro
  - site/src/pages/levels/index.astro
parent_task_id: TASK-063
priority: low
ordinal: 220000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On the Levels browse page the heart and download counts under each card are controls: the heart likes or unlikes the level and the download icon starts the counted download. The level page shows the same two icons with their counts beside the maker's name (the `counts-inline` group under the title) as plain text, so the same-looking element does nothing there. Players who open a level expect the heart to behave as it does on the browse page and as the Like button further down the same page.

Make the heart and the download icon in that group work the way they do on the browse cards, with the heart mirroring the existing Like button on the level page (same signed-in behaviour, same sign-in requirement, same state). The level page keeps its Like, Report and Download level buttons; this only makes the icons beside the maker's name act on the same state.

Context for a fresh session: the level page is a static page that fetches the level from the PocketBase API in the browser; a signed-in visitor can have at most one like per level; signed-out visitors cannot like and are shown sign-in buttons in the page's "Like or report" section; the download route counts a download and answers with the file as an attachment; the browse page behaviour was added in the commit "like and download from the level cards".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Signed in, clicking the heart beside the maker's name likes the level, or removes the like if it is already liked, and the like count updates without a reload
- [x] #2 The heart shows filled in the accent colour when the visitor has liked the level and exposes that state to assistive technology
- [x] #3 The heart and the Like button lower on the page always show the same liked state and the same count after either one is used, without a reload
- [x] #4 Signed out, clicking the heart takes the visitor to the sign-in buttons in the page's like section and does not show an error
- [x] #5 Clicking the download icon starts the counted download without leaving the page, and the download count shown there goes up by one
- [x] #6 Both controls work from the keyboard, show a visible focus outline, and have accessible names that include the level title
- [x] #7 While a like request is in flight the heart cannot be activated again, and a failed request shows the page's existing notice message
- [x] #8 A visitor who is not the author sees no edit-only controls added by this change, and the byline stays correct for a level with zero likes or downloads
- [x] #9 Behaviour is covered by tests written before the change and verified in a browser both signed out and signed in
- [x] #10 docs/website.md describes the interactive counts on the level page
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Write failing markup tests in site/tests/site.test.js: byline heart is a count-action button wired to likeFromCounts() with aria-pressed, disabled on busy, sr-only name with the level title; byline download is a count-action link to the counted download route with title in its name.
2. level/view/index.astro: turn the counts-inline spans into those controls.
3. level-view.js: guard toggleLike against busy; add likeFromCounts (signed out goes to #social without navigating or erroring, otherwise toggleLike); expose likeTitle.
4. gallery.css: confirm count-action styles and focus-visible outline apply in counts-inline.
5. docs/website.md: describe the interactive counts.
6. task check, then verify in a browser signed out and signed in.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The heart and download icon beside the maker's name on the level page are now controls. The heart is a button wired to `likeFromCounts()`: signed in it calls the existing `toggleLike()`, so it shares `liked` and `level.likes` with the lower Like button; signed out it scrolls to the `#social` sign-in section with no navigation or error. `toggleLike()` now returns early while `busy`. The download count is a link to the counted download route that increments `level.downloads` on click. Both carry accessible names that include the level title, and the heart exposes `aria-pressed`. Added a markup test in `site/tests/site.test.js` (written first, failed, now passes), removed the dead `.counts-inline > span` rule and adjusted `.counts-inline` spacing, and documented the behaviour in `docs/website.md`. Verified in Chrome against a local PocketBase: signed out (no error, state unchanged) and signed in (like and unlike mirror the lower button both ways, the heart is disabled in flight, download count goes 0 to 1, focus outline visible). `task check` passes.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
