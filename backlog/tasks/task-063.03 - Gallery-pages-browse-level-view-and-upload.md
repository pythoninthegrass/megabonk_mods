---
id: TASK-063.03
title: 'Gallery pages: browse, level view and upload'
status: To Do
assignee: []
created_date: '2026-11-11 04:49'
labels:
  - website
  - sharing
  - frontend
dependencies:
  - TASK-063.01
  - TASK-063.02
references:
  - 'https://makercentral.io/levels/search/_'
  - 'https://levelsharesquare.com/SMC/levels'
  - 'https://giscus.app/'
documentation:
  - site/DESIGN.md
  - site/PRODUCT.md
  - site/src/scripts/levels.js
  - site/server.mjs
  - docs/player-guide.md
  - docs/website.md
  - docs/level-format.md
parent_task_id: TASK-063
priority: medium
ordinal: 218000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the three gallery pages to the Astro site in site/, as static pages that fetch from the PocketBase API (TASK-063.02 defines the collections and the download route) with the `pocketbase` JS SDK as the one new dependency. Use the helpers from TASK-063.01 (`site/src/scripts/levels.js`: isShareCode, normalizeCode, slugify, buildFilter, sortParam, packList). The API base URL comes from `PUBLIC_PB_URL`, with a local default and an entry in `site/.env.example`.

Design and product constraints:
- Follow site/DESIGN.md: pale blue table surface, graphite lettering, paper-backed plates for cover images, vermilion for actions, flat surfaces, Archivo display and Public Sans body. The gallery should feel like part of the existing showcase, not a separate product. Use the existing Alpine and basecoat stack.
- site/PRODUCT.md says content should be readable without JavaScript and that the site is a showcase, not an editor. The gallery needs JavaScript; record that as a deliberate exception and update the stack line, and give the no-JavaScript case a `<noscript>` message that links to the manual sharing steps in the player guide.
- Reference designs: MakerCentral (card grid with cover, title, author, relative date, likes and plays, tag chips, excerpt and the code in the corner; a level page with a metadata table) and Level Share Square (a discussion thread on each level page).
- Pack bundles are never offered (TASK-050.03). The level page lists required packs and versions and links to the wiki guidance on installing packs.
- `site/server.mjs` already rewrites `GET /l/<code>` to `levels/view/index.html`, so the view page must read the code from `location.pathname` and must work when served at that URL.
- Comments use giscus with `data-mapping="specific"` and `data-term` set to the share code. The repository's Discussions category and giscus app are enabled in TASK-063.04; until then render the embed from configuration values and degrade to a short note when they are unset.
- OAuth sign-in uses PocketBase `authWithOAuth2` for GitHub, Google and Discord.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The browse page at /levels/ lists levels as cards with cover, title, author, relative date, likes, downloads, tags, a description excerpt and the share code, and pages through results
- [ ] #2 Browse supports a search box over title and description, a tag filter limited to the fixed tag set, and sort by newest, most liked and most downloaded; search text cannot alter the filter beyond matching
- [ ] #3 An empty result and an unreachable API each show a clear message instead of a blank page
- [ ] #4 The level page at /l/<code> shows the cover, a metadata table (code, maker, upload date, map, schema, required packs with versions, likes, downloads), description and tags, a Download button that uses the download route, a Copy code button, and install instructions for UserData/Levels/
- [ ] #5 An unknown or malformed code on the level page shows a not-found state
- [ ] #6 Signed-in users can like and unlike a level and report it; signed-out users are prompted to sign in
- [ ] #7 The level page embeds a giscus thread keyed by the share code, and shows a short note rather than a broken frame when giscus is not configured
- [ ] #8 The upload page offers GitHub, Google and Discord sign-in, then a form for the level file, cover, optional biome image and tags; server-side validation errors from the API are shown to the user; success redirects to the new level page
- [ ] #9 Signed-in users can see their own levels and edit or delete them
- [ ] #10 The pages meet DESIGN.md and are usable at phone and desktop widths and with keyboard only; an Impeccable critique of the three pages has been run and its findings addressed
- [ ] #11 A Levels link and a share call to action are added to the showcase page; docs/player-guide.md 'Sharing a level' points to the gallery and explains installing a downloaded level; site/PRODUCT.md records the JavaScript exception and the changed stack
- [ ] #12 Pure logic is unit-tested in site/tests with node --test; an end-to-end check against a local PocketBase uploads levels/bramblecrown-hill.mblevel.json with its cover, finds it by search, downloads it byte-identical, and likes it, with screenshots captured
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
