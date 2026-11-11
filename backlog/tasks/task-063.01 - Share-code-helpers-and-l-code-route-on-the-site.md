---
id: TASK-063.01
title: Share-code helpers and /l/<code> route on the site
status: Done
assignee: []
created_date: '2026-11-11 04:48'
updated_date: '2026-11-11 05:22'
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

The helpers live in `site/src/scripts/levels.js`, the route in `site/server.mjs`, and the tests in `site/tests/levels.test.js` and `site/tests/level-route.test.js`. The route tests use a temp fixture root, so they need no built `site/dist/`.
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
- [x] #8 The helpers, tests and server change are committed as one conventional commit with no attribution
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Write failing unit tests for the pure helpers (share code validation and formatting, slugify, PocketBase filter builder, sort mapping, pack list), then implement them in site/src/scripts/levels.js.
2. Write failing route tests against a temp fixture root so they need no built dist/, then add a canonical share-code regex to site/server.mjs that rewrites GET and HEAD of /l/<code> to levels/view/index.html and leaves every other path and method unchanged.
3. Register both test files in the site `npm test` script, run deno fmt and lint, and commit.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the foundation the gallery pages build on: pure, unit-tested share-code helpers and a pretty URL for level pages.

What changed:
- site/src/scripts/levels.js: isShareCode and formatCode for the canonical XXX-XXX-XXX Crockford base32 form, normalizeCode for forgiving user input (case, spaces, O/I/L lookalikes), slugify with a 'level' fallback, buildFilter that escapes quotes and backslashes and accepts only the fixed tag set, sortParam, packList, and the TAGS list.
- site/server.mjs: GET and HEAD of /l/<canonical code>, with or without a trailing slash or query string, serve levels/view/index.html. Non-canonical codes, extra segments and encoded traversal answer 404 or 400; POST still answers 405; all other paths are unchanged. The regex is inlined because the runtime image copies server.mjs without src/.
- site/tests/levels.test.js (16 tests) and site/tests/level-route.test.js (6 tests, temp fixture root with a file outside the root to prove traversal is blocked), both in the site `npm test` script.

Verification: `task check` passes (build, installer tests, 1373 Python tests, markdownlint, ruff, site lint); `npm test` in site/ passes 34 of 34; the real site image builds from the committed tree.

Notes for follow-ups: a valid /l/<code> URL returns 404 until the view page exists (TASK-063.03). No documentation was required here because nothing user-visible ships before the pages; TASK-063.03 owns the player guide, website docs and PRODUCT.md updates.

Unrelated fixes made so `task check` could pass: the two release-gate mismatch tests now set the manifest version through JSON instead of replacing a hardcoded 0.1.0, and the generated CHANGELOG.md is excluded from markdownlint.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
