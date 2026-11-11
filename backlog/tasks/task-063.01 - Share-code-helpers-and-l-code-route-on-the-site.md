---
id: TASK-063.01
title: Share-code helpers and /l/<code> route on the site
status: In Progress
assignee: []
created_date: '2026-11-11 04:48'
updated_date: '2026-11-11 04:48'
labels:
  - website
  - sharing
dependencies: []
documentation:
  - site/server.mjs
  - site/tests/server.test.js
modified_files:
  - site/src/scripts/levels.js
  - site/tests/levels.test.js
  - site/tests/level-route.test.js
  - site/server.mjs
  - site/package.json
parent_task_id: TASK-063
priority: medium
ordinal: 216000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Foundation for the gallery pages: pure, unit-tested helpers and a pretty URL for level pages. A level is addressed by a nine-character share code written XXX-XXX-XXX in the Crockford base32 alphabet (no I, L, O or U).

Status of the work: the code and tests already exist in the working tree, written test-first, and are uncommitted. They are `site/src/scripts/levels.js`, `site/tests/levels.test.js`, `site/tests/level-route.test.js`, the route in `site/server.mjs` and the two new files added to the `test` script in `site/package.json`. `npm test` in site/ passed 34 of 34 and `deno fmt --check` and `deno lint` were clean on the new files. What remains is review and a commit of exactly those files.

Known unrelated failures: two tests in `site/tests/server.test.js` fail with or without this change because the local `site/dist/` predates the current docs sync (`/docs/player-guide/` returns 404); a fresh `npm run build` should clear them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 isShareCode accepts only the canonical dashed uppercase Crockford form and rejects lowercase, undashed, I/L/O/U characters and non-strings
- [x] #2 normalizeCode turns user input with mixed case, spaces and the lookalikes O, I and L into a canonical code, and returns null for anything that cannot be one
- [x] #3 slugify gives a lowercase filename-safe slug and falls back to 'level' when nothing usable remains
- [x] #4 buildFilter escapes quotes and backslashes so a search term cannot break out of the PocketBase filter string, and ignores tags outside the fixed set (Speedrun, Platforming, Survival, Puzzle, Showcase, Short)
- [x] #5 sortParam maps newest, liked and downloads to PocketBase sort strings and defaults to newest; packList turns a packs object into sorted id/version rows and tolerates malformed input
- [x] #6 GET and HEAD of /l/<canonical code> (with or without a trailing slash or query string) serve levels/view/index.html; non-canonical codes, extra path segments and encoded traversal answer 404 or 400; POST answers 405; every other path behaves as before
- [x] #7 The new tests run without a built dist/ and are part of the site `npm test` script
- [ ] #8 The helpers, tests and server change are committed as one conventional commit with no attribution
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
