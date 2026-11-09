---
id: TASK-056.06
title: Automate path-filtered Thunderstore package builds and releases
status: In Progress
assignee: []
created_date: '2026-11-09 04:27'
updated_date: '2026-11-09T19:52:00Z'
labels:
  - ci
  - release
  - thunderstore
dependencies:
  - TASK-056.05
references:
  - .github/workflows/release-please.yml
  - release-please-config.json
  - thunderstore.toml
  - taskfiles/package.yml
  - scripts/check_thunderstore_package.py
  - tests/test_thunderstore_package.py
  - 'https://thunderstore.io/c/megabonk/p/pythoninthegrass/Megabonk_Level_Editor/'
documentation:
  - docs/thunderstore.md
parent_task_id: TASK-056
priority: medium
ordinal: 206000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Automate building, validating and submitting Megabonk Level Editor releases to Thunderstore through GitHub Actions, extending the existing root Release Please flow. Version 0.1.0 was published manually as pythoninthegrass-Megabonk_Level_Editor; future submissions should use the synchronized release version and publish the exact validated archive rather than rebuilding at upload time.

Use paths filtering so unrelated website-only, documentation-only, backlog and other non-package changes do not cause unnecessary Thunderstore builds or submissions. Include package-affecting runtime sources, build/dependency inputs, packaging assets/configuration, validation tooling and the relevant workflows in the filter. Account explicitly for shared version-file changes and for release/tag events that do not support native paths filters; release eligibility must not silently bypass the intended filtering or miss a valid package release.

Existing entry points are task package:thunderstore, task package:thunderstore:check and task package:thunderstore:manifest. The release workflow currently creates GitHub releases only. Preserve the runtime-only package contents and BepInEx dependency, use a team service-account token from Actions secrets, and never expose credentials. Build-only checks must not submit publicly. Do not implement, push, configure secrets or publish as part of filing this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Package-affecting changes trigger a validated Thunderstore build; website-only, unrelated documentation, backlog and other non-package changes are skipped by explicit paths filtering.
- [ ] #2 Filtering covers runtime sources, dependency/build inputs, package assets/configuration, validation tools and relevant workflows; shared version changes and release/tag trigger limitations have documented, tested behavior.
- [ ] #3 An eligible stable GitHub release builds from its exact tagged revision, verifies synchronized versions and validates the runtime-only ZIP before making it available as a retained artifact with a checksum.
- [ ] #4 Publication submits the exact validated ZIP to pythoninthegrass-Megabonk_Level_Editor using an Actions secret for the team service account; PR/build-only runs and failed validations cannot publish.
- [ ] #5 Already-published versions, retries and concurrent runs are handled safely without overwriting/deleting releases or creating duplicate submissions; prerelease and manual-run behavior is explicit.
- [ ] #6 Automated checks exercise filtering inclusion/exclusion and publication guards without real uploads; documentation covers triggers, secrets, approval policy, artifacts, retries and manual recovery.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
