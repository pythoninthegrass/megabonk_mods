---
id: TASK-063
title: Community level gallery on the website
status: To Do
assignee: []
created_date: '2026-11-11 04:48'
labels:
  - website
  - sharing
dependencies: []
documentation:
  - docs/website.md
  - docs/level-format.md
  - docs/player-guide.md
  - site/PRODUCT.md
  - site/DESIGN.md
  - dokploy.yml
priority: medium
ordinal: 215000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Players currently share a level by sending the `.mblevel.json`, its sidecar images and a list of required packs by hand (see "Sharing a level" in docs/player-guide.md). Add a public web gallery in the style of MakerCentral and Level Share Square: browse and search levels, open a level page with a short share code, cover, tags, required packs, likes and download count, discuss it, and upload after signing in with OAuth.

Decisions already made, which subtasks must follow:
- Jamstack: the Astro site in site/ stays `output: 'static'` and its Bun static server stays GET/HEAD only. Pages fetch data from PocketBase in the browser.
- PocketBase (new `pocketbase/` directory, a second Dokploy app at `api.megabonkmod.party` with a persistent data volume) owns accounts (GitHub, Google and Discord OAuth2, no password sign-up), level records, file storage, likes and reports.
- giscus (GitHub Discussions on this repository) provides one comment thread per level, keyed by the share code. Commenting needs a GitHub account; uploading and liking work with any OAuth provider.
- Web only for now: players download the level and install it into `UserData/Levels/` by hand. Share codes are stable so the mod can resolve them in a later task. Mod-side import is out of scope.
- Pack bundles are never hosted or offered for download (see TASK-050.03, no automatic proprietary downloads). A level page only lists the packs a level needs, with versions.
- Moderation uses the PocketBase admin dashboard; no custom moderation UI.

Level files and sidecar images follow docs/level-format.md (schema 4; `title` is required for a level to appear on Map Selection; cover limits are 8 MiB and 4096 px).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A signed-in player can upload a level with a cover and receive a share code and a public level page at /l/<code>
- [ ] #2 Anyone can browse, search, filter by tag and sort the gallery, and download a level file that is byte-identical to the upload
- [ ] #3 Each level page has a discussion thread keyed by its share code
- [ ] #4 The gallery and PocketBase API run in production at megabonkmod.party and api.megabonkmod.party with data surviving a redeploy
- [ ] #5 The player guide, website docs and PRODUCT.md describe the gallery and the manual install of a downloaded level
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
