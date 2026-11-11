---
id: TASK-063.04
title: Deploy the PocketBase API and wire the gallery into hosting
status: In Progress
assignee: []
created_date: '2026-11-11 04:49'
updated_date: '2026-11-11 21:15'
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
- [ ] #4 Data written to PocketBase persists across a redeploy of the app
- [ ] #5 Scheduled backups run and a restore of a backup into a throwaway instance has been tried and documented
- [ ] #6 OAuth sign-in works in production for each enabled provider, or the provider that is not yet set up is documented as pending
- [x] #7 site/docker-compose.yml starts PocketBase for local development and site/.env.example documents PUBLIC_PB_URL and the giscus values
- [x] #8 docs/website.md Deployment section covers the PocketBase app, DNS, environment variables, OAuth app setup, backups and restore, and the giscus setup steps
- [ ] #9 One production upload, download and like completes end to end once the gallery pages (TASK-063.03) are deployed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: add a test in tests/test_pocketbase_service.py that starts the real entrypoint and checks the backup cron and retention settings, including PB_BACKUP_CRON and PB_BACKUP_KEEP overrides; confirm it fails.
2. Add pocketbase/pb_hooks/backups.pb.js, a bootstrap hook setting backups.cron and backups.cronMaxKeep from the environment (defaults: daily, keep 7); backups land in the data volume.
3. dokploy.yml: add a pocketbase app (dockerfile pocketbase/Dockerfile, dockerContextPath /pocketbase because the root .dockerignore excludes everything but docs/ and site/), volume at /pb_data, domain api.megabonkmod.party port 8090 letsencrypt, watchPaths pocketbase/**, healthcheck; deploy_order [pocketbase] then [site]; rewrite the project description.
4. site/docker-compose.yml: pocketbase service with a named data volume on 127.0.0.1:8090. PUBLIC_PB_URL and giscus values are already in site/.env.example.
5. docs/website.md: extend Deployment and Backups for the PocketBase app, api DNS record, environment variables, OAuth app setup, scheduled backups and restore, and manual giscus steps.
6. Validate with ic check/plan only if credentials are present; do NOT run ic apply (approved scope stops before apply). ACs 3-6 and 9 need prod access and stay open.
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
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
