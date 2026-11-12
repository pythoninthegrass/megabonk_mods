---
id: TASK-063.07
title: Let players upload small asset packs to the gallery
status: In Progress
assignee: []
created_date: '2026-11-12T18:16:00Z'
updated_date: '2026-11-12T18:46:00Z'
labels:
  - website
  - sharing
  - packs
dependencies:
  - TASK-063.03
  - TASK-063.04
references:
  - 'https://support.google.com/youtube/answer/2807622'
documentation:
  - docs/asset-bundles.md
  - docs/level-format.md
  - docs/player-guide.md
  - docs/website.md
  - site/PRODUCT.md
  - pocketbase/pb_migrations/1762800000_create_gallery.js
  - pocketbase/pb_hooks/level_lib.js
  - site/src/pages/levels/view/index.astro
  - site/src/pages/levels/upload/index.astro
  - site/src/scripts/level-view.js
parent_task_id: TASK-063
priority: medium
type: feature
ordinal: 224000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-063 and TASK-063.03 decided that pack bundles are never hosted: the gallery stores only a level's `packs` map (pack id to version) and the level page says pack files are not offered. Reverse that for small, player-made packs. Players can upload a pack of at most 30 MB, the uploader attests they have the right to share it, and anyone can report a pack or level for copyright. This is a reporting-based model, not a pre-approval or licence-check one.

TASK-050.03's rule still holds: downloads stay manual and the mod never fetches a pack on its own.

Design:
- New PocketBase `packs` collection, added by a migration. Fields: pack id, version (read from `manifest.json`), author, description, `manifest.json`, `attachments.json`, a Windows bundle and a Linux bundle (a bundle is built per platform, so at least one is required), an attestation flag, and the moderation fields the `levels` collection already has (`hidden`, `viewers`, `blocked`).
- Pack ids are claimed by the first uploader. A new version of an id can be uploaded only by that owner or an admin, so nobody can overwrite or shadow someone else's pack.
- Total upload size is capped at 30 MB across all files. Confirm the cap against PocketBase's request body limit and the Traefik/Dokploy proxy limit during implementation, and set per-field `maxSize` values that add up to it.
- A server hook validates the manifest with the same rules as `PackManifest.Parse` (docs/asset-bundles.md): valid JSON, string `id` equal to the pack id, string `version`, list `assets`. It also checks sizes and that at least one platform bundle is present, and returns per-field messages the way `level_lib.js` does.
- Download serves a zip laid out as `<id>/<bundle>`, `<id>/manifest.json`, `<id>/attachments.json` for the chosen platform, so it unpacks straight into `UserData/LevelPacks/`. Count downloads like levels do.

Attestation and copyright:
- The upload form has a required checkbox along the lines of "I made this pack or have the right to share it". A tooltip next to it says what qualifies (your own work, assets under a licence that allows redistribution) and what does not (assets ripped from games or other copyrighted material, which includes the THPS Warehouse pack built locally from `.tools/`).
- The existing `reports` collection gains a reason category, with copyright as one option, and reports can target a pack as well as a level. Choosing copyright shows what a valid report needs: who owns the work, what was copied and where, and a way to contact the reporter. Reports are read in the PocketBase admin dashboard, and an admin hides or deletes the item there. No custom moderation UI, matching TASK-063.

Level page and docs:
- Each required pack on a level page links to the hosted pack with the same id when one exists, and flags it when the hosted version differs from the one the level records. Packs that are not hosted keep today's text and the link to the "Installing an asset pack" guide.
- Update docs/player-guide.md (installing a downloaded pack and sharing one), docs/website.md, site/PRODUCT.md and the pack paragraph in TASK-063's decisions list.

Open question: whether to also register a DMCA designated agent and publish a takedown and repeat-infringer policy page. Hosting user uploads without that registration can cost the site safe-harbour protection in the US. Decide before launch; the tooltip and report flow above are the agreed minimum.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A signed-in player can upload a pack (manifest, attachments, Windows and/or Linux bundle, at most 30 MB in total) after ticking the attestation; an upload with no attestation, over the limit, with an invalid manifest, with no bundle, or with a pack id owned by someone else is rejected with a clear per-field message
- [ ] #2 A pack page shows id, version, author, platforms, size, asset count and a per-platform Download whose zip unpacks into UserData/LevelPacks/<id>/ and loads in the game
- [x] #3 The attestation tooltip states what may and may not be uploaded, including ripped game assets
- [x] #4 Levels and packs can be reported with a reason category that includes copyright; choosing copyright explains what the report must contain; reports appear in the admin dashboard and an admin can hide the item
- [x] #5 A level page links each required pack to the hosted pack with the same id when one exists, flags a version mismatch, and keeps the install guide link for packs that are not hosted
- [ ] #6 Hook validation and pure helpers are unit-tested first; an end-to-end check against a local PocketBase uploads a test pack, downloads it, installs it and loads a level that uses it, with screenshots captured
- [x] #7 The player guide, website docs, site/PRODUCT.md and TASK-063's decisions describe hosted packs, the attestation and the copyright report path
- [x] #8 The copyright report form collects reporter contact, a description of the work, the reported item's link, the two agreed statements and a typed full-name signature; it requires confirmation that exceptions such as fair use were considered, warns that false reports are misuse, and states what is shared with the uploader
- [x] #9 Reporting an incomplete or invalid copyright report does not remove anything; an admin can ask the reporter for the missing information, and a valid report hides the item and notifies the uploader with the description of the work
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Server (TDD, tests/test_pocketbase_service.py against a real PocketBase): migration adds `packs` (packId, version, name, author, description, manifest, attachments, bundleWindows, bundleLinux, attested, assetCount, downloads, hidden, viewers, blocked; unique packId+version), and adds `kind`/`pack`/copyright-detail fields to `reports` with `level` made optional. `pack_lib.js` holds the pure manifest/size/platform validation (same rules as PackManifest.Parse) plus the zip layout; `packs.pb.js` hooks do validation, id ownership (first uploader owns the id, admin may add versions), server fields, visibility enrichment, and `GET /api/p/{id}/download?platform=` streaming a zip laid out `<id>/<id>`, `<id>/manifest.json`, `<id>/attachments.json`, counting downloads.
2. Reports: reason category (copyright, broken, inappropriate, other); a copyright report needs contact, work description, item link, two statements, fair-use confirmation and typed signature, else it is stored as incomplete and removes nothing; an admin-set `status` field (new, needs-info, valid, rejected) and a hook that hides the item and notifies the uploader on `valid`.
3. Cap: verify 30 MB against PocketBase body limit with a real 30 MB upload; per-field maxSize plus hook total check.
4. Site: pure helpers first (node tests): pack id/route, pack list merge with hosted lookups, report payload. Pages: `/p/<id>` pack view, `/packs/upload`, attestation checkbox with tooltip, level page pack links with version-mismatch flag, report form with reason category and copyright detail.
5. Docs: player-guide, website.md, site/PRODUCT.md, TASK-063 decisions paragraph, asset-bundles if needed.
6. E2E: local PocketBase + site dev, upload a test pack, download, install, load a level using it via the megabonk MCP, screenshots.
Decisions to confirm with Lance if they change scope: DMCA agent question stays open (not in scope).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Copyright report process, generalized from YouTube's removal-request help page (fetched 2026-11-12). Their process is a formal legal notice; keep the shape and drop the YouTube-specific parts (Studio, strikes, fax, URL formats per content type).

Report form fields, one report per alleged infringement:
1. Reporter contact: at least one of email, physical address, phone. Say which of these may be shared with the uploader and which stay private.
2. Description of the copyrighted work being protected, clear and specific. A representative list is acceptable when several works are copied.
3. Direct link to the reported item. Here that is the /l/<code> level page or the pack page; the form pre-fills it from the page the reporter came from. Whole accounts are not reportable, only individual levels and packs.
4. Two statements the reporter agrees to: a good-faith belief that the use is not authorized by the owner, its agent or the law; and that the information is accurate, and, under penalty of perjury, that the reporter is the owner or an agent authorized to act for the owner.
5. Signature: full legal name (a person, not a company name) typed as the signature.

Also carry over from the source:
- Only the copyright owner or an authorized representative should report. Ask for evidence of authorization when a representative reports.
- Before reporting, the reporter confirms they considered exceptions such as fair use or public domain; a report without that is treated as invalid.
- A prominent warning that false reports can lead to account termination or legal consequences.
- A short note on what is shared with the uploader (reporter name, email and description of the work) and what stays confidential (physical address, phone), so reporters can use an authorized representative if disclosure is a concern.
- An incomplete report is not actioned: an admin asks the reporter for the missing detail, and the item may stay up until it arrives.
- Admins review each report for the required information before removing anything. Removal sets the item's hidden flag and the uploader is notified with the report's description.

Out of scope unless the DMCA open question resolves that way: counter-notification, retraction, prevent-reupload and strike tracking. The source documents all four as separate flows.

Decision (Lance, 2026-11-12): the pack zip is built on the server by running the system `zip` from the download hook, since PocketBase's JS hooks have no zip API. The pocketbase image (Alpine Linux) gains the `zip` package.

Server side done and green (174 PocketBase service tests): migrations 1763000000 (packs) and 1763100000 (report categories, copyright fields, status), hooks pack_lib.js/packs.pb.js/report_lib.js/reports.pb.js, zip added to the pocketbase Dockerfile. A 30 MiB upload passed against the local PocketBase body limit; the production Traefik/Dokploy limit is not verified. Per-field maxSize: bundles 30 MiB each and JSON files 256 KiB; the 30 MiB total across all files is enforced by the hook, since two single-field caps cannot sum to a shared total. Pack updates are admin-only (author edits are not supported; publish a new version). Next: site pages (Alpine.js, check Context7), then docs, then end-to-end.

Verified 2026-11-12: 175 PocketBase service tests and 138 site tests pass; deno lint/fmt, ruff and markdownlint clean. End-to-end against a local PocketBase and the site dev server: uploaded a testprop pack (Windows and Linux bundles) and a level that requires it, downloaded the Windows zip, unzipped to LevelPacks/testprop/{testprop,manifest.json,attachments.json} with the bundle byte-identical, and captured screenshots of the level page, pack page, copyright report form and upload page with its tooltip. The run found a bug (a relative data directory broke the zip download); fixed with a regression test. Not done, per Lance: loading the level in the game, so AC #2 (loads in the game) and AC #6 (game-load part) stay open. Remaining: DoD #1 (full task check not run) and DoD #4 once reviewed. The DMCA designated-agent question is still open.

Decision (Lance, 2026-11-12): no DMCA designated agent registration and no takedown or repeat-infringer policy page. The site is run by one maintainer and handles copyright reports best-effort through the report flow. The earlier open question is closed; the site does not claim US safe-harbour protection. docs/website.md records this.
<!-- SECTION:NOTES:END -->
