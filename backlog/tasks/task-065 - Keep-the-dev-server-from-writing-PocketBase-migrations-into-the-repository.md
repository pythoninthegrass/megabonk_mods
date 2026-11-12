---
id: TASK-065
title: Keep the dev server from writing PocketBase migrations into the repository
status: To Do
assignee: []
created_date: '2026-11-12 05:13'
updated_date: '2026-11-12 05:13'
labels:
  - site
  - pocketbase
  - dev-experience
dependencies: []
references:
  - site/scripts/dev-api.mjs
  - pocketbase/Dockerfile
  - pocketbase/entrypoint.sh
priority: low
ordinal: 223000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Starting the site dev server (`task site:dev`, `site/scripts/dev-api.mjs`) leaves untracked files in `pocketbase/pb_migrations/` on every run (`<timestamp>_updated__superusers.js` and `<timestamp>_updated_users.js`). They record the dev-only change that turns off new-login alert emails for the `users` and `_superusers` collections, which the dev API applies at startup because the seeded dev addresses are not deliverable.

These files must never be committed: `pocketbase/Dockerfile` copies `pb_migrations/` into the production image, so committing them would turn auth alerts off in production. Today they only get caught if someone notices them in `git status` before committing, and they were nearly committed alongside unrelated work.

Outcome: running the dev server leaves the working tree clean, so a developer can run `git add -A` after a dev session without risking a production behaviour change. The dev instance must still have auth alerts off, and production migrations must stay exactly as they are.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After starting and stopping `task site:dev` on a clean checkout, `git status` shows no new or modified files under `pocketbase/`
- [ ] #2 The dev PocketBase instance still has new-login alerts disabled for both the `users` and `_superusers` collections
- [ ] #3 A fresh production data directory built from the committed `pocketbase/pb_migrations/` still has auth alerts at the PocketBase default
- [ ] #4 The dev server still seeds the demo makers and levels and the sign-in paths documented in `docs/website.md` still work
- [ ] #5 The behaviour and the reason it is dev-only are documented in `docs/website.md` or `docs/development.md`
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
