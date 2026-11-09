---
id: TASK-057
title: Prepare the repository tree and history for public review
status: Done
assignee: []
created_date: '2026-11-09 05:19'
updated_date: '2026-11-09 05:42'
labels: []
dependencies: []
ordinal: 207000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Apply the approved pre-public cleanup without changing repository visibility. Keep anonymized backlog, generic hostnames, tooling and screenshots. Remove obsolete fixture levels, transcripts, scraped references and spike. Curate 0.1.0 release notes and developer README, pin local THPS input disc checksum. Back up all Git refs before preparing a few logical initial commits. Remote rewrite and stale branch cleanup require a final checkpoint; preserve unrelated work. This is repository hygiene, not completion of the broader public-package rights and validation work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Obsolete fixtures and copied reference content are removed, with maintained docs and generated editable-level tests updated.
- [x] #2 Names and personal home paths are anonymized in tracked project content without changing generic hostnames.
- [x] #3 THPS extraction rejects a mismatching input disc checksum before producing output, with synthetic regression tests.
- [x] #4 README and curated 0.1.0 changelog describe current BepInEx support and local-only third-party assets accurately.
- [x] #5 Git history is backed up and a small logical initial history is prepared; remote cleanup is reported explicitly and repository visibility is unchanged.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Back up all Git refs privately. Clean obsolete source-tree fixtures and copied references, preserving local inputs, screenshots, generic hostnames and unrelated work. Anonymize names/home paths while retaining full task records. Add fail-closed input-disc checksum verification and synthetic tests. Curate developer README and 0.1.0 changelog; remove pinned release-as and restrict future changelog sections. Validate the tree, prepare four logical initial commits, then replace remote main/release baseline with explicit leases and remove approved stale refs. Preserve local branches and keep visibility private.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tree cleanup verified: task check passed (2780 .NET tests, 1282 Python tests, Go installer tests, build and lint). Input disc SHA-256 checked locally; negative and CLI tests use synthetic data. Editable-level replay tests now use a small in-memory fixture; Python generator test verifies deterministic output without a tracked generated JSON. Existing untracked actionlint config and package-automation task remain excluded. All original task sections retained during privacy substitutions.

Maintainer approved removal of the remote legacy MelonLoader tag and resetting the preserved release-please branch onto fresh history. Repository visibility remains manual. Legacy checkout documentation now explains the private backup boundary. GitHub PR refs/caches may still retain old objects after a branch/tag rewrite.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Prepared the source tree for public review: removed nine obsolete/generated levels, copied transcripts/scrape and the BepInEx spike; updated maintained docs and deterministic/in-memory fixture tests. Kept generators, screenshots, generic hostnames and tooling. Anonymized personal names and home paths, preserving task-record contents. Added a pinned SHA-256 for the supported local THPS input image and pre-extraction rejection/CLI tests. Rewrote README and curated the 0.1.0 baseline, clearly separating current BepInEx packaging from legacy installers and local-only third-party assets.

Validation: task check passed (2780 .NET tests, 1282 Python tests, Go installer tests, build and lint); task thps:verify-disc accepted the locally supplied input. Final lint and diff checks passed. A targeted sensitive-token scan found only synthetic test values. This is not a legal clearance or exhaustive secrets audit.

A full all-ref Git bundle was verified outside the repository. Prepared four logical initial commits with a final tree matching the reviewed cleanup. Atomic leased push replaced remote main/release-please/v0.1.0, deleted nine stale remote branches and the legacy MelonLoader tag. Repository visibility stayed private. Local legacy branches and GitHub PR refs/caches can still retain old history; they are outside the new published branch ancestry. Existing unrelated untracked files were excluded.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
