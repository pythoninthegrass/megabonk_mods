---
id: TASK-055.01
title: Containerize the website for repeatable local serving
status: To Do
assignee: []
created_date: '2026-11-08T21:51:00Z'
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
- [ ] #1 The site includes a Dockerfile and docker-compose.yml that build and serve the current static website from a clean checkout without host Node/npm or game dependencies.
- [ ] #2 Docker Compose exposes the website on a documented, configurable host port and supports documented start, stop and rebuild workflows.
- [ ] #3 The build context and served image exclude secrets, local environment files, node_modules, design-review state and unrelated game/mod assets.
- [ ] #4 A container smoke test verifies the home page and its referenced local CSS, JavaScript and images are served successfully; existing website checks remain passing.
- [ ] #5 docs/website.md and site/README.md document prerequisites, file locations, commands and container serving behavior, without implying that public hosting or DNS has been configured.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
