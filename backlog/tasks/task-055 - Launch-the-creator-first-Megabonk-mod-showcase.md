---
id: TASK-055
title: Launch the creator-first Megabonk mod showcase
status: Done
assignee: []
created_date: '2026-11-08T20:49:00Z'
updated_date: '2026-11-08T22:33:00Z'
labels: []
dependencies: []
references:
  - docs/player-guide.md
  - docs/development.md
  - docs/starter-level.md
type: feature
ordinal: 203000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Creators need a concise public explanation of what this repository adds to Megabonk and a clear path into making levels. Build a single-page showcase at megabonkmod.party, centered on original Bramblecrown Hill content, the editor, console and MCP. Hosting remains undecided; do not imply public installer availability.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A static single-page Astro site presents the editor, console and MCP with Markdown-first content, vanilla JavaScript, Alpine.js and Basecoat UI.
- [x] #2 Real editor, gameplay and console screenshots accompany clearly labeled editor and gameplay video placeholders.
- [x] #3 Formatted copyable commands distinguish console, shell and MCP usage and document development prerequisites.
- [x] #4 Creator-focused guide links, compatibility notes and unofficial status accurately reflect repository documentation.
- [x] #5 Desktop and mobile rendering, keyboard interactions, no-JavaScript content and production build are checked; local setup and media replacement are documented.
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
1. Implement the approved Build table direction in an isolated site/ Astro project, with pale blue/graphite surfaces, annotated real captures and creator-first copy.
2. Capture current Bramblecrown-like editor, gameplay and console views without altering level data; label only verified content. Preserve the paused editor state afterward.
3. Render section prose and command examples from Markdown, compose native Astro media components, theme Basecoat controls and keep enhancement code small (vanilla copy, Alpine state).
4. Include editor/gameplay video placeholders, accurate setup and compatibility guidance, canonical metadata and host-independent static output.
5. Add tests for testable command/media behavior before implementation, run production checks and a real-browser desktop/mobile/no-JS review, then independent finish review and design documentation.
6. Document local commands and media replacement; report any unavailable evidence or deployment work explicitly.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User chose creators first, original starter showcase, hosting deferred and code-first implementation. Rejected the first visual round; selected Build table in the second round. No existing site or user modifications present. Root .gitignore currently ignores /site and must be narrowed for the new source project.

Implemented isolated site/ Astro static project, Markdown content fragments, Basecoat CSS and controls, Alpine image emphasis, vanilla clipboard enhancement, original Bramblecrown editor/gameplay/console captures and two honestly labeled video placeholders. Root gitignore now tracks site source; markdownlint ignores third-party/generated files and embedded fragments. No mod source or level files changed; game left in paused editor with no dirty edits.

Validation: Astro check 0 errors/warnings; production build successful; 3 clipboard tests (written first and observed red before implementation) plus 4 built-output tests pass; npm audit reports 0 vulnerabilities; task lint and git diff --check pass. Real browser at 1440 and 390: both images visible; primary selection updates; copy reports success; keyboard focus solid; native setup opens; expanded mobile configuration remains width390; no-JS sandbox preserves both screenshots and all six headings with enhancement controls absent. Primary button contrast 5.65:1; muted table text 5.17:1. Screenshots: .impeccable/review/desktop.png and mobile.png.

Finish review initially requested simultaneous plates and seed corroboration. Both resolved; scoped verdict pass ship. Seed checker confirmed seed:a13ed1d36f9d46f1. DESIGN.md and .impeccable/design.json document the shipped system. Source image provenance scan: 4 rasters, 0 missing.

All acceptance criteria are verified. Keep In Progress for remaining repository hygiene: full task check was not run because it rebuilds/deploys the unrelated game mod, and no commit was requested. No deployment/DNS changes made; recordings remain placeholders by design. Local dev preview http://127.0.0.1:4321; production preview http://127.0.0.1:4322.

Follow-up: all 12 current off-site links, including the Markdown harness link and newly embedded https://melon-loader.com/ link on MelonLoader in the setup checklist, use target=_blank and rel=noopener noreferrer. Local fragment navigation stays in the current tab. Inline prose links are visibly underlined. Added a regression test first (observed failure), then verified generated HTML and the live browser: 12 external links, no incorrect targets/rel values, MelonLoader label/URL correct. Astro check and all 5 built-page tests pass; no new Markdown dependency was added.

Website design context is now scoped under site/: PRODUCT.md, DESIGN.md and the entire .impeccable/ directory moved from the repository root, preserving ignored screenshots and seed history. Surface brief renamed to site/.impeccable/surfaces/src-pages-index-astro.md with primary_target src/pages/index.astro; sidecar source references rebased. docs/website.md, site/README.md and the two-sentence AGENTS.md website pointer document the new root. Shared skills remain in .agents/skills/. Verified surface-brief lookup from site/, config/JSON validity, documentation links, preserved review captures, Git ignore behavior, Markdown lint and static build.

Closure verification (mbp, pushed HEAD 40effa8): task check exit 0, covering the mod build and deploy, the Go installer, 1158 pytest items and task lint. Website checks green: astro check 0 errors/warnings, 3 clipboard tests, 10 built-output and static-server tests, production build, npm audit 0 vulnerabilities. Committed and pushed as 13bd501 (container tooling) and 40effa8 (deployment docs and site/.env.example), both conventional subject and body only with no attribution trailer.

Hosting was decided after the original plan and is now implemented: the site is live at https://megabonkmod.party/ served from the multi-stage image built from site/Dockerfile, deployed declaratively through dokploy.yml with the icarus CLI and documented under docs/website.md#deployment. Live verification: apex answers 200 text/html over HTTPS with a Let's Encrypt certificate, plain HTTP 301s to HTTPS, and the container smoke check run against the public origin passes with 18 local references (1 css, 1 js, 16 images) at exit 0.

Remaining deferred items, neither covered by an acceptance criterion: the editor and gameplay video placeholders remain placeholders by design, and www.megabonkmod.party resolves but has no router yet, so its TLS handshake fails; it needs a second host entry on the app or a redirect at the DNS provider.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built a creator-first, single-page showcase for megabonkmod.party in site/, using Astro, Markdown-first content, vanilla JavaScript, Alpine.js and Basecoat UI. Includes original Bramblecrown editor, gameplay and console captures, honestly labeled editor and gameplay video placeholders, accurately labeled console/shell/MCP commands, creator-focused guide links and compatibility notes, and canonical metadata in a host-independent static output. Website design context (PRODUCT.md, DESIGN.md, .impeccable/) is scoped under site/.

The site is published at https://megabonkmod.party/ from the container image the repository builds: a multi-stage site/Dockerfile served by the dependency-free static server, deployed declaratively through dokploy.yml with the icarus CLI and documented under docs/website.md#deployment, with the container smoke check doubling as the health check and the post-deploy verification. Container serving for local preview is documented under docs/website.md.

Verification: astro check 0 errors/warnings; 3 clipboard tests written first and observed red before implementation, plus 10 built-output and static-server tests; production build and npm audit with 0 vulnerabilities; task check exit 0 including the mod build, installer, Python suites and lint; task lint clean. Real-browser desktop and mobile review covers both screenshot emphasis states, copy feedback, keyboard focus, the expanded MCP configuration and no-JavaScript content. Live checks against the public origin: HTTPS 200 text/html with a Let's Encrypt certificate, HTTP 301 to HTTPS, and the smoke check passes 18 local references at exit 0.

Deferred by design or out of scope: the two video placeholders await real recordings, and www.megabonkmod.party still needs a router or a DNS-level redirect.
<!-- SECTION:FINAL_SUMMARY:END -->
