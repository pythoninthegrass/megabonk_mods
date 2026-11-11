---
id: TASK-063.04
title: Deploy the PocketBase API and wire the gallery into hosting
status: To Do
assignee: []
created_date: '2026-11-11 04:49'
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
- [ ] #1 dokploy.yml declares the PocketBase app with its domain, port, certificate, deploy order before the site, and a persistent data volume, and passes the ic validation or dry-run used for the existing app
- [ ] #2 No secret, personal identifier, address or host-specific path appears in dokploy.yml, docs, compose files, commits or backlog tasks
- [ ] #3 After `ic --env prod apply` and DNS propagation, https://api.megabonkmod.party/api/health answers 200 with a valid certificate
- [ ] #4 Data written to PocketBase persists across a redeploy of the app
- [ ] #5 Scheduled backups run and a restore of a backup into a throwaway instance has been tried and documented
- [ ] #6 OAuth sign-in works in production for each enabled provider, or the provider that is not yet set up is documented as pending
- [ ] #7 site/docker-compose.yml starts PocketBase for local development and site/.env.example documents PUBLIC_PB_URL and the giscus values
- [ ] #8 docs/website.md Deployment section covers the PocketBase app, DNS, environment variables, OAuth app setup, backups and restore, and the giscus setup steps
- [ ] #9 One production upload, download and like completes end to end once the gallery pages (TASK-063.03) are deployed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
