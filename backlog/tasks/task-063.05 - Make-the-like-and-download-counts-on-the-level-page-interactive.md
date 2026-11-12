---
id: TASK-063.05
title: Make the like and download counts on the level page interactive
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
- [ ] #1 Signed in, clicking the heart beside the maker's name likes the level, or removes the like if it is already liked, and the like count updates without a reload
- [ ] #2 The heart shows filled in the accent colour when the visitor has liked the level and exposes that state to assistive technology
- [ ] #3 The heart and the Like button lower on the page always show the same liked state and the same count after either one is used, without a reload
- [ ] #4 Signed out, clicking the heart takes the visitor to the sign-in buttons in the page's like section and does not show an error
- [ ] #5 Clicking the download icon starts the counted download without leaving the page, and the download count shown there goes up by one
- [ ] #6 Both controls work from the keyboard, show a visible focus outline, and have accessible names that include the level title
- [ ] #7 While a like request is in flight the heart cannot be activated again, and a failed request shows the page's existing notice message
- [ ] #8 A visitor who is not the author sees no edit-only controls added by this change, and the byline stays correct for a level with zero likes or downloads
- [ ] #9 Behaviour is covered by tests written before the change and verified in a browser both signed out and signed in
- [ ] #10 docs/website.md describes the interactive counts on the level page
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
