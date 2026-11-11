---
id: TASK-063.03
title: 'Gallery pages: browse, level view and upload'
status: In Progress
assignee: []
created_date: '2026-11-11 04:49'
updated_date: '2026-11-11 07:55'
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
modified_files:
  - site/src/pages/levels/index.astro
  - site/src/pages/levels/view/index.astro
  - site/src/pages/levels/upload/index.astro
  - site/src/layouts/GalleryLayout.astro
  - site/src/styles/gallery.css
  - site/src/styles/global.css
  - site/src/scripts/gallery.js
  - site/src/scripts/browse.js
  - site/src/scripts/level-view.js
  - site/src/scripts/upload.js
  - site/src/scripts/gallery-app.js
  - site/src/scripts/pb.js
  - site/tests/gallery.test.js
  - site/src/pages/index.astro
  - site/package.json
  - site/package-lock.json
  - site/.env.example
  - site/PRODUCT.md
  - site/Dockerfile
  - site/docker-compose.yml
  - docs/player-guide.md
  - docs/website.md
  - pocketbase/pb_hooks/level_lib.js
  - tests/test_pocketbase_service.py
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
- [x] #1 The browse page at /levels/ lists levels as cards with cover, title, author, relative date, likes, downloads, tags, a description excerpt and the share code, and pages through results
- [x] #2 Browse supports a search box over title and description, a tag filter limited to the fixed tag set, and sort by newest, most liked and most downloaded; search text cannot alter the filter beyond matching
- [x] #3 An empty result and an unreachable API each show a clear message instead of a blank page
- [x] #4 The level page at /l/<code> shows the cover, a metadata table (code, maker, upload date, map, schema, required packs with versions, likes, downloads), description and tags, a Download button that uses the download route, a Copy code button, and install instructions for UserData/Levels/
- [x] #5 An unknown or malformed code on the level page shows a not-found state
- [x] #6 Signed-in users can like and unlike a level and report it; signed-out users are prompted to sign in
- [x] #7 The level page embeds a giscus thread keyed by the share code, and shows a short note rather than a broken frame when giscus is not configured
- [ ] #8 The upload page offers GitHub, Google and Discord sign-in, then a form for the level file, cover, optional biome image and tags; server-side validation errors from the API are shown to the user; success redirects to the new level page
- [x] #9 Signed-in users can see their own levels and edit or delete them
- [ ] #10 The pages meet DESIGN.md and are usable at phone and desktop widths and with keyboard only; an Impeccable critique of the three pages has been run and its findings addressed
- [x] #11 A Levels link and a share call to action are added to the showcase page; docs/player-guide.md 'Sharing a level' points to the gallery and explains installing a downloaded level; site/PRODUCT.md records the JavaScript exception and the changed stack
- [x] #12 Pure logic is unit-tested in site/tests with node --test; an end-to-end check against a local PocketBase uploads levels/bramblecrown-hill.mblevel.json with its cover, finds it by search, downloads it byte-identical, and likes it, with screenshots captured
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (site/tests, node --test) for pure helpers in site/src/scripts/gallery.js: relativeDate, excerpt, coverUrl, downloadUrl, codeFromPath, page math, pbErrorMessages; plus a buildFilter test that hostile search text stays inside a quoted literal. Add the new test files to the npm test script.
2. Add the pocketbase SDK with npm (lockfile stays package-lock.json; the container builds with Bun from it, verify the image build still resolves it). Add PUBLIC_PB_URL (local default) and giscus values to site/.env.example.
3. Pages sharing the showcase head, fonts and tokens: /levels/ (browse), /levels/view/ (served at /l/<code>; reads code from location.pathname), /levels/upload/ (OAuth sign-in, upload form, own levels with edit/delete). Alpine components in src/scripts, styles in global.css per DESIGN.md. noscript message links to the player guide.
4. Showcase Levels nav link and share CTA; docs/player-guide.md 'Sharing a level'; site/PRODUCT.md JavaScript exception and stack line; docs/website.md.
5. Verify: npm test, check, build, test:site; end-to-end against local PocketBase in Docker with a seeded test user standing in for OAuth (upload bramblecrown-hill, search, byte-identical download, like, screenshots); Impeccable critique of the three pages and fixes; task check.
6. Conventional commits, no attribution; tick AC and DoD as met.

Approved by Lance: test user stands in for OAuth locally; PocketBase runs in Docker.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Status: implemented and committed locally; one commit pushed. The multipart-update hook fix (a545f43) is on main; the other commits are held until the PocketBase API is deployed, because pushing them deploys the site with a gallery that would show its unreachable message until the API answers.

Verified in a browser against a local PocketBase image in Docker (a seeded test session stood in for OAuth): empty and unreachable states, upload with server validation errors, redirect to /l/<code>, search including hostile text, pasted share-code jump, byte-identical download with the slugged filename and a counted download, like and unlike, report, signed-out prompt, edit (description and cover) and delete with confirm, not-found for unknown and malformed codes, 390px layouts without overflow, paging across 14 seeded levels, the tag filter, both sorts, URL state restore with hostile or invalid params ignored, the giscus embed rendering from localhost (0 reactions, 0 comments, GitHub sign-in box; no comment posted), and provider-aware sign-in buttons with no providers, only GitHub, and the API down.

Found and fixed during verification: PocketBase wraps the upload hook's error payload so field detail messages are objects (client falls back to the response message); the level page getter read the record before it loaded; multipart updates with no level file returned a generic 400 (hook fixed in level_lib.js with two regression tests).

Plan deviations: no page-math helper (the SDK's totalPages is used); helpers added beyond the plan are codeFromSearch, availableProviders, giscusAttrs, mapName and plural. Sign-in buttons come from the API's auth-methods list, so unconfigured providers are not offered. Production wiring: site/Dockerfile takes PUBLIC_PB_URL (default https://api.megabonkmod.party) and the four giscus ids (the repository's public values) as build arguments, and Compose passes the local API address. The api A record is live; the API app itself is not deployed yet.

Impeccable critique ran twice (27 then 28 out of 40); P1, P2 and P3 findings were fixed (share-code block, action ranking, delete focus, upload help, edit-mode cover and row marker, mobile header and filters, outline sign-in buttons). Remaining minor findings are in site/.impeccable/critique.

Open ACs: #8 real OAuth sign-in is untested locally and is covered by the production sign-in check in the deployment task; #10 skipped by decision because no critique pass was run after the last fixes. Both left unticked.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
