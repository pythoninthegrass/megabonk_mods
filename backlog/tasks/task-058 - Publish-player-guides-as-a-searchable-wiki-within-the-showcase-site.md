---
id: TASK-058
title: Publish player guides as a searchable wiki within the showcase site
status: Done
assignee: []
created_date: '2026-11-09 06:06'
updated_date: '2026-11-09 06:48'
labels: []
dependencies: []
ordinal: 208000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the sts2 wiki as reference: publish only the agreed player-facing guides inside the existing site, with searchable navigation and copyable raw Markdown. Keep repository docs authoritative and preserve the showcase. Serve via docs.megabonkmod.party; DNS was updated by the maintainer.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Only the eight approved guides and wiki index are published, with working links and preserved showcase.
- [x] #2 Production wiki search finds guide content; each page offers Copy page and View as Markdown.
- [x] #3 Build and deployment include authoritative docs, docs hostname HTTPS routing, and health checks.
- [x] #4 Sync, Markdown endpoints, server routing and built site have automated coverage; local workflow is documented.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implemented and deployed: integrate Starlight in site/ with a hand-authored /home/ landing page and eight published guides under /docs/. Keep docs/ authoritative through an allowlisted Node sync/watch step with parsed link rewriting. Provide matching raw Markdown endpoints, sts2 Copy page SVG, accessible controls, Pagefind and llms text. Preserve the showcase and add a Docs navigation item styled like Source. Use a white light-theme reading background, pale-blue navigation and unchanged dark theme. Build from a tightly filtered repository-root Docker context. Import existing Dokploy state, explicitly reconcile source/build fields omitted by Icarus apply, add the docs HTTPS domain, and deploy pushed main commits. Preserve old homepage links with server redirects to /home/ and /home.md. Validate site suites, typecheck, lint, container smoke, real browser layouts/search/copy and live endpoints. DNS was handled by the maintainer. Website-specific checks substitute for the unrelated game-mod task check per AGENTS.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented Starlight under site/ /docs/ with eight-guide allowlist, authoritative-doc sync/watch, parsed Markdown-link rewriting, raw Markdown routes, accessible copy/disclosure controls, Pagefind and llms text outputs. Showcase remains at apex; docs host root redirects to /docs/. Dockerfile-specific allowlist supports repo-root context without game artifacts or secrets; Dokploy config adds docs domain and docs/** watch path.

Validation: npm test (11 tests), npm run test:site (15 tests), npm run check (zero errors/warnings; expected execCommand deprecation hint), task lint and git diff --check passed. Docker Compose build and in-image smoke passed (42 references), plus docs-host 308 via actual HTTP Host header. Dev wrapper served guide at 200. Browser desktop/mobile verified four Bramblecrown search results, exact Markdown clipboard content, themed layouts, preserved showcase and final overflow-free dropdown. Independent finish review accepted rendering; its documentation-persistence fix was resolved and scored ship.

Fixed inherited NODE_ENV=development disabling production search UI by explicitly setting production in build command. Added built-markup regression assertion. Reconciled lockfile using npm 10 in a clean temporary directory after container npm ci exposed optional-dependency lock omissions.

Deployment blocked: ic --env prod status cannot read DOKPLOY_API_KEY on this machine. No remote changes, DNS changes, commits or pushes made. Once credentials are restored and changes reviewed/committed/pushed, run ic check/plan/apply from site/ with existing imported state, then smoke both hostnames. Full task check intentionally not run: website-only guidance uses site checks instead of rebuilding/relaunching game mod. Existing unrelated .github/actionlint.yaml left untouched.

Maintainer requested deployment and supplied root .env credentials. Authenticated configured server, imported existing project state (hydrated appName from application.one because project.all summaries omit it), explicitly reconciled Docker context and GitHub watch paths using the Icarus checkout payload builders, and applied config without creating a replacement project. Domain path defaults are explicit to avoid spurious updates. No environment targets are configured, so credentials/game settings were not pushed to the site.

Wiki implementation committed and pushed as b3a5c5f. Production deployment completed successfully; apex smoke served 42 references and docs-host smoke served 23. Verified valid HTTPS, docs-host root HTTP 308 to /docs/, raw Markdown HTTP 200 with text/markdown, and existing showcase.

User refinements: white light-theme reading background, exact sts2 SVG copy icon. Follow-up request for Docs navigation styled like Source implemented with external-link icon and a regression test; committed/pushed as cd0413f. All 16 built-site tests pass. Awaiting live verification of the auto-deployed navigation update. The unrelated .github/actionlint.yaml remains untouched.

Completed follow-up homepage routing change in f513448, committed and pushed. Production / and /docs/ both answer 308 to /home/; old /docs/index.md answers 308 to /home.md; /home/ returns HTML 200 and /home.md returns text/markdown 200. Showcase Docs link now targets /home/. Both production smoke checks pass after this deployment. Local built-site suite now has 17 passing tests including legacy redirects; 11 unit tests and typecheck/lint also pass.

Icarus plan reports infrastructure up to date, and separate source/build payload comparisons are empty after reconciliation. The generic task-check DoD is left unchecked because the explicit website-only workflow uses site checks instead of rebuilding the unrelated game mod.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Published and deployed the eight-guide Starlight wiki within the existing Astro showcase. Authoritative docs sync automatically; published links, search, copyable raw Markdown, llms text bundles and navigation are covered by tests. The wiki uses the requested copy icon and white light-theme reading background. Docs navigation matches Source; the canonical wiki homepage is /home/, with compatible redirects from the old homepage and Markdown URL. Updated Docker/Dokploy configuration and workflow docs, preserving existing showcase and project resources.

Validation: 11 unit tests, 17 built-site/server tests, Astro check, task lint, Docker build/in-image smoke, desktop/mobile browser checks including exact clipboard content and search results, and successful smoke checks on both public hostnames. Feature commits b3a5c5f, cd0413f and f513448 are pushed. No API keys, environment files, local state or unrelated actionlint file were committed.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
