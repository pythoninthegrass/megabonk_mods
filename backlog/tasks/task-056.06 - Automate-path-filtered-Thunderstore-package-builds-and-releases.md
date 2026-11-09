---
id: TASK-056.06
title: Automate path-filtered Thunderstore package builds and releases
status: In Progress
assignee: []
created_date: '2026-11-09 04:27'
updated_date: '2026-11-09T20:08:00Z'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Constraints found in research
- The mod build references game-generated BepInEx interop assemblies (not redistributable), so hosted runners cannot build it. Build runs on the self-hosted runner `mini-megabonk` (repo-scoped, labels self-hosted, macOS, ARM64, megabonk-mod, megabonk; launchd `actions.runner.pythoninthegrass-megabonk_mods.mini-megabonk`, dir `~/actions-runner-megabonk_mods` on the Mac mini; separate from the two org runners there). The repo is public, so the self-hosted jobs must never run on `pull_request`/fork code.
- The csproj post-build step copies into the game's plugins folder; CI builds pass `-p:ModInstanceFolder=<runner temp dir>` so the dev install is untouched.
- `release`/tag events do not support `paths`; release-please releases are created with a PAT (RELEASE_PLEASE_TOKEN) so the `release: published` event does fire workflows.

Design
1. `scripts/thunderstore_release_gate.py` (single source of truth for the package-affecting path set, as glob patterns) with: `affects_package(changed_paths)`, a `git diff --name-only <previous tag>..<tag>` helper, and publication guards (stable tag only, tag == `v<thunderstore.toml version>`, synchronized versions across thunderstore.toml / pkg/manifest.json / csproj / pyproject, version not already on Thunderstore via the existing `package_exists`, ZIP SHA-256 matches the recorded checksum).
2. `.github/workflows/thunderstore.yml`:
   - `push` to main with an explicit `paths:` list: build + validate + upload artifact + checksum on the self-hosted runner; never publishes.
   - `release: published`: no native paths, so a `gate` job (hosted runner) runs the gate script against previous-tag..tag and skips build/publish when nothing package-affecting changed; prereleases skipped; explicit outputs.
   - `workflow_dispatch` with a `tag` input: rebuild/validate from that exact tag; `publish` input default false.
   - build job checks out the exact tag, runs `task package:thunderstore` with ModInstanceFolder override, uploads ZIP + SHA-256 as a retained artifact.
   - `publish` job: needs build, only on release or approved manual dispatch, `environment: thunderstore` (required-reviewer approval), downloads the artifact, re-verifies the checksum, runs `tcli publish --file <zip>` with `TCLI_AUTH_TOKEN` from an Actions secret, never bare `tcli publish`.
   - `concurrency: thunderstore-publish` with `cancel-in-progress: false`; already-published versions are detected before upload and end the run successfully without overwriting.
3. A test asserts the workflow's `push.paths` equals the gate script's pattern list so they cannot drift; paths cover src/MegabonkLevels.Mod/**, csproj/props, thunderstore.toml, pkg/**, taskfiles/package.yml, scripts/check_thunderstore_package.py, scripts/validate_thunderstore_manifest.py, scripts/asset_download.py, the gate script, the workflow, and version files; exclude site/**, backlog/**, docs/**, .agents/.claude.
4. Docs: extend docs/thunderstore.md (triggers, path set, shared version-file behavior, release/tag limitation, secrets, approval, artifacts, retries, manual recovery, prerelease and manual-run behavior) and the release-please paragraph that says it does not publish.
5. Lint the new workflow with jactionlint (`.github/actionlint.yaml` already lists the runner labels).

TDD order: failing tests for gate logic and workflow/gate path parity first, then the script, then the workflow, then docs.

Needs the maintainer afterward (not done by me): create the `thunderstore` environment with required reviewers, add the `TCLI_AUTH_TOKEN` Actions secret, and set Actions fork-PR approval to "require approval for all outside collaborators".
<!-- SECTION:PLAN:END -->
