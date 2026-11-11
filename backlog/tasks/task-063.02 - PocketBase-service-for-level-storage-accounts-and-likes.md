---
id: TASK-063.02
title: 'PocketBase service for level storage, accounts and likes'
status: Done
assignee: []
created_date: '2026-11-11 04:49'
updated_date: '2026-11-11 05:41'
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
- [x] #1 The container image builds from a pinned PocketBase release verified by checksum, serves on port 8090, restricts CORS origins to the site's origins plus localhost for development, and keeps all data under one declared volume
- [x] #2 Migrations create the users, levels, likes and reports collections from code, enable GitHub, Google and Discord OAuth2 with credentials read from environment variables, and disable password sign-up
- [x] #3 Anyone can list and view levels where hidden is false; any signed-in user can create a level; only the owner can update or delete it; clients can never set code, downloads, likes or hidden
- [x] #4 Creating a level whose file is not valid JSON, has a schemaVersion outside 1 to 4, has no title, or has a malformed grid or edits is rejected with a clear error
- [x] #5 On create and update the title, packs, schemaVersion, gameBuildId and map fields are derived from the uploaded file, and a unique share code is generated on create
- [x] #6 A user can like a level once and unlike it; the stored like count always equals the number of like records
- [x] #7 The download route increments the count, redirects to the file and names the download after the level title; hidden levels are not downloadable
- [x] #8 Signed-in users can file a report on a level; only an admin can read reports
- [x] #9 Automated tests run against a throwaway PocketBase instance with a temporary data directory and cover every rule above, including the rejection cases, using the real files in levels/ as fixtures (bramblecrown-hill for a plain level, thps for packs)
- [x] #10 docs/website.md documents the service, its environment variables, how to run it and its tests locally, moderation through the admin dashboard, and backups
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved decisions: JSVM migrations and hooks on the stock binary (no Go build); PocketBase tests skip when the binary is absent so `task test` stays green, a dedicated `pocketbase:test` task fails when absent; alpine base image on a current patched release (apk upgrade at build), checksum-verified PocketBase 0.40.6 zip.

1. Tests first (tests/test_pocketbase_*.py): session fixture starts the binary on a free port with a tmp data dir, creates users through the superuser API, uses levels/bramblecrown-hill and levels/thps as fixtures. Cover rejection cases, derivation, code format, access rules, likes count invariant, download route, reports, OAuth/password settings. Confirm they fail.
2. pocketbase/pb_hooks/level_validate.js (pure validator), levels.pb.js, likes.pb.js, download.pb.js.
3. pocketbase/pb_migrations: users (OAuth2 from env, password auth off), levels, likes, reports with access rules.
4. pocketbase/Dockerfile (pinned release, SHA-256 verified, one volume, port 8090, PB_ORIGINS CORS, healthcheck).
5. taskfiles/pocketbase.yml (run, test), wired into task test with skip semantics.
6. docs/website.md section: service, env vars, local run and tests, moderation, backups.
7. task check, then conventional commit without attribution.

As built: hooks are level_lib.js (validator, derivation, codes, slugs), levels.pb.js (upload hooks, download route, filename), likes.pb.js and oauth.pb.js; the separate level_validate.js and download.pb.js were folded into those. Added pocketbase/entrypoint.sh so tests and the image share one startup path, and the pocketbase:install, superuser and image tasks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PocketBase 0.40 JSVM gotchas found while building: handlers run in isolated scopes so shared helpers must live in a module loaded with require inside the handler; hook events expose the response writer as e.requestEvent.response, not e.response; findUploadedFiles throws on non-multipart requests, so the hook checks the content type first; onServe is not a JSVM global, use onBootstrap; a rule-failed update answers 404, not 403.

Choices beyond the contract: cover is required (the contract lists biome as the optional image); an OAuth credential sync hook re-applies env credentials on every start because migrations run once; the download redirect targets a ?download=1 file URL and onFileDownloadRequest sets the title-based Content-Disposition, since a header on the 302 itself would never reach the browser; PocketBase tests skip under task test and fail under task pocketbase:test when the binary is absent; the test file captures os.kill at import so it can stop its own service despite the conftest guard.

Image builds on alpine 3.24.4 (first 3.24 release with the OpenSSH fix) with zero openssh packages; the build fails if one appears. Alpine stable branches backport the fix without reaching OpenSSH 10.6p2, so a version-number check would reject patched stable releases.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Adds pocketbase/: a JSVM-only PocketBase 0.40.6 service (migrations for users, levels, likes, reports; hooks for level validation and metadata derivation, share codes, like recounts, the download route with title-based filename, and OAuth credential sync), an Alpine container image with a checksum-verified release, no OpenSSH and a single /pb_data volume, taskfiles/pocketbase.yml, and a Gallery API section in docs/website.md. 52 tests in tests/test_pocketbase_service.py run against a throwaway instance started through the real entrypoint, using levels/bramblecrown-hill and levels/thps. task check passes.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
- [x] #5 Container image ships no OpenSSH package (build fails if any openssh package is present) and is based on an Alpine release at or after the 2026-11-05 OpenSSH password-bypass fix (3.24.4 or later), upgraded with apk at build time
<!-- DOD:END -->
