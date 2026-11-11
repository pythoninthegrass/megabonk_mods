---
id: TASK-063.02
title: 'PocketBase service for level storage, accounts and likes'
status: To Do
assignee: []
created_date: '2026-11-11 04:49'
labels:
  - website
  - sharing
  - backend
dependencies: []
references:
  - 'https://pocketbase.io/docs/'
documentation:
  - docs/level-format.md
  - docs/website.md
  - levels/bramblecrown-hill.mblevel.json
  - levels/thps.mblevel.json
parent_task_id: TASK-063
priority: medium
ordinal: 217000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the backend the gallery pages talk to, as a new `pocketbase/` directory in this repository: a container image, collections defined as migrations, and server-side hooks that validate uploads. It must run locally for development and tests, and the deploy task (TASK-063.04) ships it to production. The gallery pages task (TASK-063.03) is written against the API contract below, so keep these names stable and document any change in docs/website.md.

Context and constraints:
- A level is the `.mblevel.json` file described in docs/level-format.md (schema 4; schemas 1 to 3 migrate on load in the mod, so accept 1 to 4). The server derives gallery metadata from the uploaded file so the gallery can never disagree with what the game shows. A level needs `title` to appear on Map Selection.
- Cover and biome images mirror the in-game sidecar limits: png or jpg, at most 8 MiB.
- Pack bundles are never stored or offered; `packs` is only metadata (see TASK-050.03).
- Use PocketBase 0.40.x. A local binary can be run without pinning it for the fleet: `mise exec github:pocketbase/pocketbase@0.40.6 -- pocketbase ...`. Do not add PocketBase to `.tool-versions`, since that makes every box install it.
- Secrets (OAuth client ids and secrets) come from environment variables, never the repository.

API contract the site relies on (collection `levels`): `title`, `description` (max 2000), `code` (unique, XXX-XXX-XXX Crockford base32, server-generated), `author` (relation to users), `level` (one .json file, max 1 MiB), `cover` (image), `biome` (optional image), `packs` (json object of pack id to version), `schemaVersion`, `gameBuildId`, `map`, `tags` (multi-select: Speedrun, Platforming, Survival, Puzzle, Showcase, Short), `downloads`, `likes`, `hidden`. Collections `likes` (user, level; unique pair) and `reports` (user, level, reason). Route `GET /api/l/{code}/download` increments the download count and redirects to the stored file with a `Content-Disposition` filename of `<slug-of-title>.mblevel.json`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The container image builds from a pinned PocketBase release verified by checksum, serves on port 8090, restricts CORS origins to the site's origins plus localhost for development, and keeps all data under one declared volume
- [ ] #2 Migrations create the users, levels, likes and reports collections from code, enable GitHub, Google and Discord OAuth2 with credentials read from environment variables, and disable password sign-up
- [ ] #3 Anyone can list and view levels where hidden is false; any signed-in user can create a level; only the owner can update or delete it; clients can never set code, downloads, likes or hidden
- [ ] #4 Creating a level whose file is not valid JSON, has a schemaVersion outside 1 to 4, has no title, or has a malformed grid or edits is rejected with a clear error
- [ ] #5 On create and update the title, packs, schemaVersion, gameBuildId and map fields are derived from the uploaded file, and a unique share code is generated on create
- [ ] #6 A user can like a level once and unlike it; the stored like count always equals the number of like records
- [ ] #7 The download route increments the count, redirects to the file and names the download after the level title; hidden levels are not downloadable
- [ ] #8 Signed-in users can file a report on a level; only an admin can read reports
- [ ] #9 Automated tests run against a throwaway PocketBase instance with a temporary data directory and cover every rule above, including the rejection cases, using the real files in levels/ as fixtures (bramblecrown-hill for a plain level, thps for packs)
- [ ] #10 docs/website.md documents the service, its environment variables, how to run it and its tests locally, moderation through the admin dashboard, and backups
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
