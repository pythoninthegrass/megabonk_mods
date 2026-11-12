---
id: TASK-063.04
title: Deploy the PocketBase API and wire the gallery into hosting
status: Done
assignee: []
created_date: '2026-11-11 04:49'
updated_date: '2026-11-12 00:23'
labels:
  - website
  - sharing
  - deploy
dependencies:
  - TASK-063.02
references:
  - 'https://giscus.app/'
  - 'https://pocketbase.io/docs/going-to-production/'
documentation:
  - dokploy.yml
  - docs/website.md
  - site/docker-compose.yml
  - site/.env.example
  - site/Dockerfile
parent_task_id: TASK-063
priority: medium
ordinal: 219000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship the PocketBase service (TASK-063.02) to production next to the site and make local development match. The site deploys from `dokploy.yml` at the repository root through the `ic` CLI, run from `site/`; read "Deployment" in docs/website.md before changing hosting or DNS. The site and API share the one self-hosted Dokploy control plane and VPS; identifiers and credentials stay in the untracked local notes and `site/.env`, never in tracked files, commits or this task.

Requirements:
- A second Dokploy app builds `pocketbase/Dockerfile` and serves it at `api.megabonkmod.party` on port 8090 with Let's Encrypt, deployed before the site, with a persistent volume for the PocketBase data directory so levels, uploads and accounts survive redeploys.
- OAuth client ids and secrets for GitHub, Google and Discord are Dokploy environment variables, not repository content. Each OAuth app's redirect URL is `https://api.megabonkmod.party/api/oauth2-redirect`.
- DNS: an `api` A record to the VPS, DNS-only (no CDN proxy) so the HTTP-01 challenge resolves, like the apex.
- Backups: PocketBase scheduled backups, configured from code, written to the data volume. Off-box copies are a possible follow-up, not part of this task.
- Local development: a `pocketbase` service in `site/docker-compose.yml` and `PUBLIC_PB_URL` in `site/.env.example`.
- giscus: Discussions enabled on the repository, a "Levels" category, and the giscus GitHub app installed. These are manual steps for the maintainer; document them and the resulting repo, category and ids that the site configuration needs (these are public values).
- Update the `dokploy.yml` project description, which currently calls the site a dependency-free static server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 dokploy.yml declares the PocketBase app with its domain, port, certificate, deploy order before the site, and a persistent data volume, and passes the ic validation or dry-run used for the existing app
- [x] #2 No secret, personal identifier, address or host-specific path appears in dokploy.yml, docs, compose files, commits or backlog tasks
- [x] #3 After `ic --env prod apply` and DNS propagation, https://api.megabonkmod.party/api/health answers 200 with a valid certificate
- [x] #4 Data written to PocketBase persists across a redeploy of the app
- [x] #5 Scheduled backups run and a restore of a backup into a throwaway instance has been tried and documented
- [x] #6 OAuth sign-in works in production for each enabled provider, or the provider that is not yet set up is documented as pending
- [x] #7 site/docker-compose.yml starts PocketBase for local development and site/.env.example documents PUBLIC_PB_URL and the giscus values
- [x] #8 docs/website.md Deployment section covers the PocketBase app, DNS, environment variables, OAuth app setup, backups and restore, and the giscus setup steps
- [x] #9 One production upload, download and like completes end to end once the gallery pages (TASK-063.03) are deployed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: PocketBase service tests for the backup schedule and retention; add pocketbase/pb_hooks/backups.pb.js, applied from PB_BACKUP_CRON and PB_BACKUP_KEEP on every start (default daily at 03:00, keep 7).
2. dokploy.yml: a pocketbase app (pocketbase/Dockerfile, build context /pocketbase because the root .dockerignore excludes everything but docs/ and site/), persistent /pb_data volume, api.megabonkmod.party on port 8090 with Let's Encrypt, healthcheck, deployed before the site, env_targets limited to pocketbase.
3. Move the Dokploy and OAuth settings into the root .env (template in .env.example), filtered by ENV_EXCLUDES so only PB_* keys reach the API app; run ic from the repository root.
4. Patch icarus (separate repository) so apply creates apps missing from the state file and plan lists them; make ic exec interactive on a terminal.
5. site/docker-compose.yml: pocketbase service with a named data volume; site/.env.example: gallery and giscus settings.
6. docs/website.md: deployment, DNS, environment variables, OAuth app setup, backups and restore, giscus steps.
7. Apply to production, verify health and certificate, persistence across a redeploy, a manual backup and restore, scheduled backups, GitHub sign-in, and an upload, like and download.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done and verified locally: backups.pb.js with 3 new tests (57 PocketBase tests pass, task check passes); dokploy.yml pocketbase app validates against the icarus JSON schema; compose config validates; a backup was written under the data dir and a restore into a throwaway instance served /api/health 200 (documented in docs/website.md).

Not done, by instruction (stop before apply): ic check/plan could not run because site/.env with Dokploy credentials is absent on this box, so AC 1's ic dry-run is unverified (schema validation only). ACs 3, 4, 6, 9 and the production half of 5 need ic apply, the api DNS record in the infra repo, OAuth apps and Dokploy env vars. Changes are uncommitted.

Credentials: ic check authenticates against the control plane with the repository .env (DOKPLOY_* only). PB_OAUTH_* reach the container through env_targets: [pocketbase] from a dedicated env file selected with DOTENV_FILE; the repository-root .env must not be the push source because ic env defaults to it and pushes every key not matched by ENV_EXCLUDES.

Blocker found in icarus: with a valid state file, apply skips setup and plan/reconcile only visit apps already in state, so the new pocketbase app is neither planned nor created, and cmd_env would fail on the missing state entry. Needs either an icarus change to create apps missing from state, or creating the app and running ic import. Awaiting decision; ic apply not run.

Consolidated deployment settings into the root .env (template in .env.example); ic runs from the repository root. ENV_EXCLUDES in .env keeps unrelated keys out of the pocketbase push; verified the push set is empty until PB_OAUTH_* are added. docs/website.md and AGENTS.md updated.

icarus patched in its own checkout (uncommitted there): cmd_add_missing_apps creates apps absent from state during apply, and plan lists them. With the patched checkout, ic plan from the repository root shows pocketbase application, domain, settings and mount creates (4 to create). The globally installed ic must be reinstalled from the checkout before apply. ic apply still not run.

Applied to production with the patched ic: pocketbase app created, GitHub OAuth credentials pushed from the root .env (2 vars), deployed before site. https://api.megabonkmod.party/api/health answers 200 with a Let's Encrypt certificate; auth-methods lists github only with password sign-in off; CORS allows the site origin; levels list is empty; site still 200. Google and Discord are pending (no credentials yet).

Still open: AC 4 (persistence across redeploy) and the production half of AC 5 need a superuser created in the container, which needs DOKPLOY_SSH_* for ic exec; AC 6 needs a browser GitHub sign-in; AC 9 needs the gallery pages deployed and a signed-in session.

Production checks over HTTPS with a throwaway test user (impersonated, then deleted along with its level, like and backup): uploaded bramblecrown-hill, redeployed with ic trigger, and the level record, its uploaded file and the download route all survived (AC 4). A like through the likes collection raised the count to 1 and the download route counted a download. A manual POST /api/backups created a zip; downloading it and starting a local instance on it served /api/health 200 with the level and like present (restore verified).

Scheduled backups are NOT running in production: /api/settings reports an empty backups.cron and cronMaxKeep 3 (the defaults), because the deployed image was built from origin/main, which does not yet contain backups.pb.js (the three commits are local and unpushed). AC 5 stays open until the commits are pushed, the app redeploys, and settings show the cron. AC 6: a users record created before the test user exists in production, probably a GitHub sign-in; awaiting confirmation. AC 9: API-level upload, download and like verified; the gallery pages path in the browser is untested.

Pushed to main; Dokploy autodeployed pocketbase and site. Production /api/settings now reports backups.cron '0 3 * * *' and cronMaxKeep 7, so scheduled backups are configured from code (AC 5; restore of a production backup was verified earlier). GitHub sign-in confirmed working by the maintainer; Google and Discord remain pending without credentials (AC 6). The new 404 page serves with status 404 in production. AC 9 browser path through the gallery pages remains for the maintainer to try.

AC 9 confirmed by the maintainer: a like and a download completed through the deployed gallery pages in production. The maintainer keeps a superuser as the local admin; its credentials stay in the untracked .env and are excluded from the env pushed to the API app (verified: the live container has no such keys).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The PocketBase API is deployed next to the site and the gallery works end to end in production.

What changed:
- dokploy.yml declares a pocketbase app (api.megabonkmod.party, port 8090, Let's Encrypt, persistent /pb_data volume, healthcheck) deployed before the site. Its build context is pocketbase/ because the root .dockerignore only allows docs/ and site/.
- pocketbase/pb_hooks/backups.pb.js applies a daily backup schedule (03:00, keep 7) from PB_BACKUP_CRON and PB_BACKUP_KEEP on every start, with service tests.
- Dokploy credentials and PB_OAUTH_* now live in the untracked root .env. env_targets pushes that file to the pocketbase app only, filtered by ENV_EXCLUDES; .env.example documents every key and the exclusion prefixes. No secret or identifier is in the repository.
- site/docker-compose.yml gained a pocketbase service for local development; docs/website.md covers deployment, DNS, environment variables, OAuth app setup, backups and restore, and the giscus steps.
- icarus (separate repository, pushed) now creates apps missing from the state file during apply and lists them in plan, and ic exec opens an interactive shell on a terminal.

Verified in production: /api/health answers 200 with a valid certificate; a level, its uploaded file and the download route survived a redeploy; a production backup restored into a throwaway instance; the scheduled backup settings show the cron and retention; GitHub sign-in works; a like and a download completed through the deployed pages. Tests: 65 PocketBase service tests, the site test suites and task check pass.

Risks and follow-ups: Google and Discord sign-in are pending until their OAuth credentials are added (providers without both id and secret are not offered). Backups stay on the data volume; an off-box copy is a possible follow-up. The ENV_EXCLUDES denylist must gain a prefix for any unrelated secret added to the root .env. The .dokploy-state/prod.json file is per machine and must be copied when ic is used from another box.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
