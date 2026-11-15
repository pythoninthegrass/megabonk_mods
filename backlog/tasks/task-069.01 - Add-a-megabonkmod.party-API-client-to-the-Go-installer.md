---
id: TASK-069.01
title: Add a megabonkmod.party API client to the Go installer
status: Done
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies: []
references:
  - pocketbase/pb_hooks/levels.pb.js
  - pocketbase/pb_hooks/packs.pb.js
  - pocketbase/pb_hooks/level_lib.js
  - pocketbase/pb_hooks/pack_lib.js
  - docs/level-format.md
parent_task_id: TASK-069
priority: high
ordinal: 237000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The installer must turn what a player gives it into downloadable files. It accepts a share code (e.g. `RZN-36A-M6V`), a `megabonkmod.party/l/<code>` link or a `/levels/view/?code=` link. From that it needs the level file, the cover and biome images, and the level's required packs.

The new package goes in `go/internal/site`. It uses only the standard library (`net/http`); MyGo must stay the only direct module dependency, which `task installer:verify-static` checks.

**Base URL:** `MEGABONK_API_URL`, defaulting to `https://api.megabonkmod.party`.

**Endpoints (verified in `pocketbase/pb_hooks/`):**
- Metadata: `GET /api/collections/levels/records?filter=(code='<CODE>')`.
  - Fields: `id`, `title`, `level` (filename), `cover`, `biome` (optional), and `packs`, an object mapping pack id to version string.
  - Files are served at `/api/files/levels/<id>/<file>`.
  - Codes are upper-cased server-side.
- Level file: `GET /api/l/<code>/download`. It answers 302 and bumps the download count, so use it rather than the raw file URL. A hidden or unknown code gets 404.
- Pack: `GET /api/p/<id>/download?platform=windows&version=<v>`.
  - The zip contains `<id>/<id>`, `<id>/manifest.json` and `<id>/attachments.json`.
  - 404 means the pack is not hosted.
- `/api/l/` is rate-limited to 30 requests per 60 s; a 429 needs a clear message.

The level filename on disk is the slug of the title (see `slugify` in `pocketbase/pb_hooks/level_lib.js`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Share codes, megabonkmod.party level URLs and view-page URLs all resolve to the same normalised code; anything else is rejected with a clear error
- [x] #2 Looking up a code returns the level title, slug filename, cover and biome image URLs and the required packs map
- [x] #3 An unknown or hidden code reports 'level not found' rather than a generic HTTP error
- [x] #4 A pack that is not hosted is reported distinctly from a network failure
- [x] #5 A rate-limited response tells the player to wait and retry
- [x] #6 The API base URL can be overridden by environment for testing
- [x] #7 Unit tests cover each case against a local test HTTP server, with no live network access in go test
- [x] #8 No new direct module dependency is added
<!-- AC:END -->

## Implementation Notes

`go/internal/site` is standard-library only; `go.mod` and `go.sum` are untouched and `task installer:verify-static` still reports MyGo as the single direct dependency. Tests run against `httptest` servers plus a `127.0.0.1:1` client for the unreachable case, and 89% of statements are covered.

Decisions worth recording beyond the description:

- A hidden level and an unknown one both answer "level not found", and an empty `items` page is treated the same as a 404, since PocketBase's `listRule` hides a level by returning no records rather than by refusing the request.
- `Slug` reproduces the site's `slugify`, including its behaviour of collapsing every run of non-`[a-z0-9]` characters to one hyphen and falling back to `level` when nothing usable remains (so a non-Latin title slugs to `level`). `Filename()` prefers the record's stored `level` file, because a title can be renamed after upload and the stored name does not follow it.
- Hermeticity is enforced rather than assumed: a test scans the package's own sources for any `megabonkmod.party` hostname other than the two constants, decoding string literals first so an escaped spelling cannot hide a host, and looking up hosts greedily so `megabonkmod.party.evil.example` is seen as one host rather than as the allowed host plus a suffix.
- The 429 message reads `Retry-After` when the server sends it; a non-numeric form falls back to "wait a moment and retry".
- `Redirect` policy: the level download answers 302, and the client follows it only within the API host, so a redirect off-host is refused instead of leaking the request.

Two things this package deliberately does not do, because they belong to the caller: it returns response bytes rather than writing files, and it validates no digests. Downloading a pack with an empty version asks the site for the newest hosted one, which the level's own `packs` map never needs.

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
