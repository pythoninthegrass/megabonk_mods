---
id: TASK-055.01
title: Containerize the website for repeatable local serving
status: Done
assignee: []
created_date: '2026-11-08T21:51:00Z'
updated_date: '2026-11-08T22:09:00Z'
labels: []
dependencies: []
references:
  - site/package.json
  - site/astro.config.mjs
documentation:
  - docs/website.md
  - site/README.md
  - site/PRODUCT.md
parent_task_id: TASK-055
priority: medium
type: chore
ordinal: 204000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The megabonkmod.party showcase needs a reproducible way to build and serve the site without requiring the host to maintain its Node/npm environment. Scope is the standalone static Astro project in site/, not the game mod or development harness. Hosting remains undecided: this task provides container tooling, not deployment, DNS or TLS provisioning.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The site includes a Dockerfile and docker-compose.yml that build and serve the current static website from a clean checkout without host Node/npm or game dependencies.
- [x] #2 Docker Compose exposes the website on a documented, configurable host port and supports documented start, stop and rebuild workflows.
- [x] #3 The build context and served image exclude secrets, local environment files, node_modules, design-review state and unrelated game/mod assets.
- [x] #4 A container smoke test verifies the home page and its referenced local CSS, JavaScript and images are served successfully; existing website checks remain passing.
- [x] #5 docs/website.md and site/README.md document prerequisites, file locations, commands and container serving behavior, without implying that public hosting or DNS has been configured.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (DoD): add site/tests/server.test.js that boots the not-yet-written static server against dist/ on an ephemeral port and runs the shared smoke checks; observe red before implementing.
2. site/server.mjs: dependency-free Node static server for dist/ (GET/HEAD only, index.html for /, traversal-safe path resolution, MIME map for html/css/js/webp/png/jpg/svg/woff/woff2/txt, Cache-Control per path, graceful SIGTERM). Exports createApp({root}); runs as main with PORT (8080) and HOST (0.0.0.0 inside the container).
3. site/smoke.mjs: dependency-free container smoke test. runSmoke(baseUrl) fetches / (200, text/html), extracts every local href/src plus srcset entry from the home page, asserts >=1 CSS, JS and image each, then fetches every reference asserting 200, expected Content-Type prefix and non-empty body. As main it hits http://127.0.0.1:8080 by default, so the running container self-verifies (also used as the compose healthcheck and via docker compose exec, no host Node needed).
4. site/Dockerfile (multi-stage, context site/): stage 1 node:22-alpine npm ci + npm run build; stage 2 node:22-alpine with only dist/, server.mjs, smoke.mjs; USER node, EXPOSE 8080.
5. site/.dockerignore: exclude node_modules, .astro, dist, .impeccable (design-review state), .env*, logs, .DS_Store so the build context never carries host builds, local env or review state; game/mod assets live outside the site context by construction.
6. site/docker-compose.yml: single site service, ports "127.0.0.1:${SITE_PORT:-8080}:8080" (documented, configurable), healthcheck node smoke.mjs, image name megabonkmod-party-site; document up --build / down / ps / logs / exec smoke.
7. package.json: test:site gains tests/server.test.js so existing validation sequence (build before test:site) stays intact.
8. Docs: docs/website.md container-serving section + site/README.md Docker section covering prerequisites (Docker only for container workflow), file locations, start/stop/rebuild commands, port config, smoke test, and an explicit note that container serving is local only with no public hosting or DNS configured.
9. Validate: host checks (check/test/build/test:site/audit), docker compose build, up -d, host curl of published port, in-container smoke via exec, clean-checkout proof by building from a temp copy without node_modules/dist/.astro/.impeccable, task lint; attempt task check and report any environment-limited steps honestly.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Container tooling added in site/: Dockerfile (multi-stage node:22-alpine; npm ci + astro build, serve stage carries only dist/, server.mjs, smoke.mjs, non-root), docker-compose.yml (site service, 127.0.0.1:${SITE_PORT:-8080}:8080, healthcheck node smoke.mjs), .dockerignore (node_modules, .astro, dist, .impeccable, .env*, logs, .DS_Store), dependency-free server.mjs and smoke.mjs, tests/server.test.js folded into npm run test:site.
Decisions: build context scoped to site/ so game/mod assets and .env can never enter; static scripts copied into the serve stage directly from the context (COPY --from=build of context-origin files reproducibly tripped a BuildKit content-hash bug on this host: failed to calculate checksum of ref ... not found, surviving no-cache, builder prune -a and a docker VM restart; dist/ copied from the build stage is unaffected); server binds 0.0.0.0 in-container while compose publishes loopback only; SITE_PORT works per command or via gitignored site/.env.
Lockfile: package-lock.json re-synced with npm install --package-lock-only inside node:22-alpine; the committed lock lacked the @emnapi/core/runtime entries that sharp/tailwind-oxide wasm32 chains need on linux-musl, so npm ci failed EUSAGE in the container. Diff is additive (42 lines) plus 8 dropped "peer": true flags; host npm ci, astro check, 3 clipboard + 10 built-output tests and audit pass; package.json untouched.
Validation: container healthy; host curl 200 text/html; exec smoke ok 18 refs (1 css, 1 js, 16 images) exit 0; negative test deleted index CSS -> smoke answered 404 exit 1; clean-checkout proof: rsync copy without node_modules/.astro/dist/.impeccable/.env (5MB) built, served on SITE_PORT=8234 and smoke passed; SITE_PORT=8123 honored, 8080 closed; task check exit 0 (mod build, installer, 1158 pytest, lint); task lint exit 0 after docs edits.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added container tooling for the megabonkmod.party showcase in site/: a multi-stage Dockerfile (node:22-alpine npm ci + astro build; serve stage contains only dist/, server.mjs and smoke.mjs and runs as the non-root node user), docker-compose.yml publishing 127.0.0.1:${SITE_PORT:-8080} with node smoke.mjs as healthcheck, a site-scoped .dockerignore, the dependency-free static server server.mjs, the smoke check smoke.mjs, and tests/server.test.js wired into npm run test:site. docs/website.md gained a Container serving section plus source-map and validation updates, and site/README.md a Serving with Docker section; both state the workflow is local-only with hosting and DNS still undecided.

Verification: smoke test was written first and observed failing before implementation; container reaches healthy; host curl of the published port answers 200 text/html; in-container smoke passes with 18 local references (1 css, 1 js, 16 images); a negative test removing the built CSS makes the smoke answer 404 and exit 1; a clean-checkout copy (no node_modules/.astro/dist/.impeccable/.env, 5MB) builds, serves on SITE_PORT=8234 and passes the smoke; SITE_PORT override verified against the default; host checks pass (npm ci, astro check 0/0/0, 3 clipboard + 10 built-output tests, 0 audit vulnerabilities); task check and task lint exit 0.

Notes: package-lock.json was additively re-synced inside node:22-alpine because the committed lock lacked @emnapi/core/runtime needed by sharp and tailwind-oxide wasm32 chains on linux-musl (npm ci failed EUSAGE otherwise); package.json is untouched. Serving-stage COPYs of the static scripts read from the build context because copying context-origin files with --from=build reproducibly tripped a BuildKit content-hash bug on this host's OrbStack builder.
<!-- SECTION:FINAL_SUMMARY:END -->
