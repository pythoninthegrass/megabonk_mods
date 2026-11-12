---
id: TASK-064
title: 'site:dev starts a seeded local API and applies the share-link rewrites'
status: Done
assignee: []
created_date: '2026-11-12 01:51'
updated_date: '2026-11-12 01:56'
labels:
  - website
  - dx
dependencies: []
documentation:
  - docs/website.md
  - taskfiles/site.yml
  - site/scripts/dev.mjs
  - site/server.mjs
priority: low
ordinal: 222000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Inspecting the gallery pages needs several manual steps today: a local PocketBase, a superuser, seeded accounts and levels, and the production server for the /l/<code> and /u/<id> rewrites that the Astro dev server lacks. Make `task site:dev` do all of it, so the gallery pages can be inspected in dev as they behave in production.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 task site:dev starts a local PocketBase on 127.0.0.1:8090 with data in a gitignored dev directory when nothing listens there, and stops it when the dev server exits
- [x] #2 A tracked, tested seed script idempotently creates a dev superuser, makers (one with no display name, one with no levels) and about 18 levels with one hidden, and prints each account id with a localStorage snippet that signs the browser in as that user
- [x] #3 The Astro dev server rewrites /l/<code> and /u/<id> to the view pages using route patterns shared with site/server.mjs rather than copies
- [x] #4 docs/website.md documents the dev workflow, replacing the note that the dev server has no rewrite
- [x] #5 task check passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: routes.mjs (viewRoute rewrites /l/<code> and /u/<id>, null otherwise) and dev-seed.mjs (seed definition shape: makers incl. empty name and no levels, ~18 levels with one hidden; sign-in snippet).
2. site/routes.mjs shared by server.mjs and an Astro dev vite plugin; Dockerfile copies it.
3. site/scripts/dev-api.mjs: find PocketBase via POCKETBASE_BIN or mise, reuse a listener on 8090 else start via pocketbase/entrypoint.sh with data in gitignored pocketbase/pb_data_dev, upsert superuser, seed over REST (idempotent, rate limits off for the dev instance), print ids and localStorage snippets; scripts/dev.mjs starts it and stops it on exit.
4. Docs in docs/website.md; task check.
Deviation from the earlier proposal: Node instead of Python for the seed, so one process lifecycle lives in dev.mjs and tests use node:test.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`npm run dev` (task site:dev) now runs scripts/dev-api.mjs first: it finds the pinned PocketBase (POCKETBASE_BIN or mise), reuses a server already on 8090 or starts one through pocketbase/entrypoint.sh with data in the gitignored pocketbase/pb_data_dev, upserts a dev superuser, and seeds three makers and 17 levels (one hidden) idempotently through the REST API (rate limits off for that instance). It prints each maker's /u/<id> and a localStorage sign-in line, and stops PocketBase when the dev server exits. Route patterns moved to site/routes.mjs (viewRoute), shared by server.mjs and a Vite plugin in astro.config.mjs, so /l/<code> and /u/<id> work in dev; the Dockerfile copies routes.mjs. Seed Node rather than Python, as noted in the plan. Verified in a pty: API healthy, /u and /l return 200, SIGINT stops PocketBase and Astro. Astro backgrounds itself when it detects an agent environment (CLAUDECODE etc.), which leaves PocketBase unowned; documented. Tests: routes.test.js and dev-seed.test.js; task check green.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
