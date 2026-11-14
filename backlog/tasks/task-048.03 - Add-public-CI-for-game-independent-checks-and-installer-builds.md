---
id: TASK-048.03
title: Add game-independent pull-request CI on hosted runners
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-14 23:04'
labels:
  - onboarding
dependencies:
  - TASK-047
  - TASK-048.02
references:
  - 'https://docs.github.com/en/actions/reference/security/secure-use'
documentation:
  - docs/development.md
  - docs/website.md
parent_task_id: TASK-048
priority: high
ordinal: 179000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add public PR validation without a game install or generated game references. The existing Thunderstore workflow is release/build automation, not PR CI, and root task check does not run the site's unit/build/built-page checks. Use GitHub-hosted runners for untrusted PRs with Python 3.13 and the pinned site toolchain. The full mod compilation and game runtime remain trusted/local validation. Do not produce or publish retired standalone installer packages; existing Go tests may run as regression coverage without making installers public deliverables.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Public pull-request CI runs the documented game-independent Python tests and lint plus site unit tests, type checks, build and built-page tests on hosted runners; no game installation or generated game references are acquired.
- [ ] #2 Python jobs use 3.13; unavailable generated-artifact tests are explicitly accounted for rather than silently treated as runtime verification, and genuine failures fail the job.
- [ ] #3 Untrusted PR jobs never execute on asset-bearing self-hosted machines, receive publishing secrets or use a privileged workflow path; actions use immutable pins and least-privilege permissions.
- [ ] #4 Contributor docs identify hosted required checks, excluded mod/game validation and result interpretation; Go regression checks, if retained, do not publish legacy installers.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-14 rescope: .github/workflows/thunderstore.yml has main push, release and manual triggers, not pull_request, and its mod build uses a self-hosted host. Root task check runs build, installer:test, test and lint; task site:test separately runs site unit tests, build and built-page tests, so both coverage paths must be explicitly represented in CI. Remove installer-target builds from deliverables because that player route is retired. No workflow implementation is claimed by this triage update.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
