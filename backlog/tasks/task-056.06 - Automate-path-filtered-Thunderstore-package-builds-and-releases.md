---
id: TASK-056.06
title: Automate path-filtered Thunderstore package builds and releases
status: Done
assignee: []
created_date: '2026-11-09 04:27'
updated_date: '2026-11-09T21:13:00Z'
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
- [x] #1 Package-affecting changes trigger a validated Thunderstore build; website-only, unrelated documentation, backlog and other non-package changes are skipped by explicit paths filtering.
- [x] #2 Filtering covers runtime sources, dependency/build inputs, package assets/configuration, validation tools and relevant workflows; shared version changes and release/tag trigger limitations have documented, tested behavior.
- [x] #3 An eligible stable GitHub release builds from its exact tagged revision, verifies synchronized versions and validates the runtime-only ZIP before making it available as a retained artifact with a checksum.
- [x] #4 Publication submits the exact validated ZIP to pythoninthegrass-Megabonk_Level_Editor using an Actions secret for the team service account; PR/build-only runs and failed validations cannot publish.
- [x] #5 Already-published versions, retries and concurrent runs are handled safely without overwriting/deleting releases or creating duplicate submissions; prerelease and manual-run behavior is explicit.
- [x] #6 Automated checks exercise filtering inclusion/exclusion and publication guards without real uploads; documentation covers triggers, secrets, approval policy, artifacts, retries and manual recovery.
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Live verification 2026-11-09: pushed to main. The push run (paths filter matched) and a manual workflow_dispatch of v0.1.0 with publish=false both passed gate and build on the self-hosted runner; publish was skipped. Artifacts thunderstore-package uploaded with 14-day (push) and 90-day (tagged dispatch) retention. First dispatch design flaw found and fixed: the tag predates the gate script, so tooling now comes from the workflow commit (ci-tools checkout, --root). Not yet exercised live: a release-published event through the gate, the publish job, the thunderstore environment approval, and a non-matching push being skipped.

Evidence 2026-11-09: path filter skip proven by commit 7a38ff2 (docs-only) starting Release Please but no Thunderstore run; matching pushes 12a3773, 03691f0, cab6f43 and a v0.1.0 dispatch all built and passed. task check: 1365 passed, 1 skipped. Reproducible build: CI DLL a64b1fa85ea13f14 equals local builds with PathMap, ContinuousIntegrationBuild and source-control queries disabled. Open at the time of writing: the thunderstore environment does not exist (first reference would auto-create it without reviewers, so no approval gate); release-published gate path and publish job never executed live.

First real release 2026-11-09: release PR 10 merged, v0.2.0 release event ran gate (package=true, since the csproj and pkg/README.md changed beyond version lines), build on the self-hosted runner (artifact thunderstore-package with checksum), then publish paused at the thunderstore environment (required reviewer created via the API beforehand) and, once approved, published pythoninthegrass-Megabonk_Level_Editor 0.2.0 (site shows it, created 21:06 UTC). Criterion 5 (already-published skip, retries, concurrency, prerelease) remains unit-tested only; no live retry of an already-published version has been run.

Retry check 2026-11-09: workflow_dispatch of v0.2.0 with publish=true (run 42700013105) waited at the thunderstore environment, was approved, re-verified the artifact checksum and manifest, then the guard found 0.2.0 already published: the tcli publish step was skipped, the already-published summary step ran, the run succeeded and nothing was uploaded. Prerelease, wrong-tag and unknown-state guards plus concurrency-group behavior are covered by unit tests and the workflow definition, not by live runs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added automated, path-filtered Thunderstore builds and approved publication for Megabonk Level Editor.

What changed:
- scripts/thunderstore_release_gate.py holds the decisions: the package-affecting path set, release eligibility that ignores shared-version-only diffs, publication guards, SHA-256 record and check, a version-sync check, and --root for building old tags.
- .github/workflows/thunderstore.yml runs on push to main with an explicit paths filter (build and validate only), on release published (a gate job compares against the previous stable tag because release events have no paths filter; prereleases are skipped), and on workflow_dispatch for a given tag.
- The build runs on a repo-scoped self-hosted runner on the Mac mini because it needs the game's generated interop assemblies. The publish job runs on a hosted runner in the thunderstore environment (required reviewer), re-verifies the checksum and manifest, and submits the exact validated ZIP with tcli publish --file using the TCLI_AUTH_TOKEN Actions secret. An already-published version skips the upload and succeeds.
- Also added: runner labels megabonk-mod and megabonk, an actionlint config, a pyyaml dev dependency, and a reproducible mod build (ContinuousIntegrationBuild, PathMap, source-control queries disabled) so the DLL depends only on the source.
- docs/thunderstore.md documents triggers, path set, secrets, approval, artifacts, retries and recovery.

Verification:
- Unit tests written first (56 gate tests); task check 1365 passed, 1 skipped.
- Live: matching pushes built, and a docs-only push triggered no Thunderstore run.
- Live: a manual v0.1.0 build passed.
- Live: the first real release (v0.2.0) went through gate, build and approval and published to Thunderstore (the site shows 0.2.0).
- Live: a manual v0.2.0 publish dispatch was approved and correctly skipped the upload as already published.
- CI and local builds of the same source produce an identical DLL hash.

Risks and follow-ups:
- Prerelease, wrong-tag and unknown-publication-state guards and the concurrency group are unit-tested only, with no live run.
- The self-hosted runner executes repo workflows on a personal Mac, so fork-PR approval for outside collaborators must stay on.
- The environment's required reviewer is the repository owner with self-review allowed.
- The published v0.1.0 DLL predates the reproducible-build settings and will not hash-match a rebuild.
<!-- SECTION:FINAL_SUMMARY:END -->
