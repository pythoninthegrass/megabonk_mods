---
id: TASK-068
title: >-
  Let other sites embed the showcase site's images so the Thunderstore README
  screenshots render
status: To Do
assignee: []
created_date: '2026-11-14 23:29'
labels:
  - site
  - thunderstore
dependencies: []
references:
  - 'https://thunderstore.io/c/megabonk/p/pythoninthegrass/Megabonk_Level_Editor/'
  - 'https://megabonkmod.party/social.jpg'
documentation:
  - site/server.mjs
  - site/tests/server.test.js
  - docs/website.md
  - docs/thunderstore.md
modified_files:
  - site/server.mjs
  - site/tests/server.test.js
  - docs/website.md
priority: medium
ordinal: 235000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Thunderstore package page renders pkg/README.md's two screenshots from megabonkmod.party and both fail: the browser reports net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin and advises a more permissive Cross-Origin Resource Policy. The assets themselves are fine: https://megabonkmod.party/social.jpg returns 200 image/jpeg 1200x630 and loads standalone.

Cause: site/server.mjs adds Cross-Origin-Resource-Policy: same-origin to every response, so no other origin may embed any site asset. docs/website.md tells README authors to host screenshots on the public showcase site rather than private-repository raw URLs, so the intended design and the header contradict each other. The package page is the first troubleshooting page a player reads, and it currently shows two broken images there.

Fix: allow cross-origin embedding of public static assets (at least images) while keeping documents and non-public responses restricted. Keep the gallery working: pocketbase/pb_hooks/security_headers.pb.js already sends same-site for the API because the apex loads gallery images from the api subdomain, and the gallery's own embedding behaviour must not regress.

Found while validating TASK-062.01's Thunderstore Markdown Preview check; the README text change shipped with the images still blocked, tracked here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both README screenshots render on the Megabonk Level Editor package page: each img has naturalWidth > 0 and the page's console has no ERR_BLOCKED_BY_RESPONSE entries
- [ ] #2 site/server.mjs sends Cross-Origin-Resource-Policy: cross-origin for public static image assets while HTML documents and non-public responses keep a policy that still blocks cross-origin embedding, or an equivalent split with the rationale recorded
- [ ] #3 site/tests/server.test.js covers the per-response-type CORP behaviour and the site checks described in docs/website.md pass
- [ ] #4 docs/website.md's security-headers paragraph states the CORP split and why marketing and README images must be embeddable by other origins
- [ ] #5 The deployed site, not just a local run, serves the new header, confirmed by an external check, and the api-subdomain gallery images still load on the apex pages
- [ ] #6 No tokens, personal paths or machine identifiers are introduced, and the commit is Conventional with no attribution
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
