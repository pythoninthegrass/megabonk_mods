---
id: TASK-066
title: Enforce a Content-Security-Policy without unsafe-inline or unsafe-eval scripts
status: Done
assignee: []
created_date: '2026-11-12T19:00:00Z'
updated_date: '2026-11-12T19:52:00Z'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Closed as won't do; none of the acceptance criteria were implemented, so they stay unchecked.

Decision: the strict CSP means switching Alpine to its CSP build (every x-data and x-on expression rewritten as a registered component) and hashing Astro and Starlight inline scripts at build time. That touches every Alpine page and needs an in-browser pass over the gallery, wiki search, giscus and the OAuth popup. The risk and effort were judged too high for two web-check findings, so the site keeps the enforced CSP with 'unsafe-inline' and 'unsafe-eval' in script-src. The rationale is recorded in docs/website.md under Security headers.

Other web-check findings left as they are, with reasons: no WAF (the Cloudflare proxy conflicts with the DNS-only setup the Let's Encrypt HTTP-01 challenge needs); no OCSP stapling (Let's Encrypt no longer issues OCSP responses); the legacy-client TLS warning (TLS 1.0 and 1.1 are already off, further changes only cut off very old devices); no COEP (require-corp breaks the giscus frame and cross-origin gallery images); security.txt unsigned (signing is optional); no HSTS preload (hard to undo).

Still open outside the repo: DNSSEC is not enabled. Turn it on in Cloudflare and add the DS record at the registrar.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Not implemented, by decision. The enforced CSP keeps 'unsafe-inline' and 'unsafe-eval' in script-src because a strict policy requires rewriting every Alpine component for the CSP build and hashing inline scripts, which was judged too invasive. Reopen as a new task if the risk assessment changes.
<!-- SECTION:FINAL_SUMMARY:END -->
