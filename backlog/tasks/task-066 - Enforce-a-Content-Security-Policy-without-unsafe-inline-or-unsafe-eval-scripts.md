---
id: TASK-066
title: Enforce a Content-Security-Policy without unsafe-inline or unsafe-eval scripts
status: To Do
assignee: []
created_date: '2026-11-12T19:00:00Z'
labels: []
dependencies: []
documentation:
  - docs/website.md
priority: low
type: enhancement
ordinal: 225000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The site's enforced CSP still allows 'unsafe-inline' and 'unsafe-eval' in script-src, because Astro and Starlight emit inline scripts and the standard Alpine build evaluates expressions at runtime. That clears the missing-header finding from the web-check scan but gives little protection against script injection: an injected inline script would still run. Tightening it means the page scripts must run under a policy that lists exactly which inline code is allowed, without breaking the gallery, wiki search, giscus comments or the OAuth login popup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The Content-Security-Policy served by the site has no 'unsafe-inline' or 'unsafe-eval' in script-src
- [ ] #2 Home, wiki (including search), level gallery, level view with giscus comments, upload and pack pages load with no CSP violations in the browser console
- [ ] #3 OAuth login through the popup still works against the dev API
- [ ] #4 tests/server.test.js asserts the stricter script-src
- [ ] #5 docs/website.md Security headers section describes the final policy and drops the explanation of the exceptions
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
