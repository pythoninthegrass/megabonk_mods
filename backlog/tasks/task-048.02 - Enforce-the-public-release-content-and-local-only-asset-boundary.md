---
id: TASK-048.02
title: Enforce the public release content and local-only asset boundary
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-14 23:04'
labels:
  - onboarding
dependencies:
  - TASK-047
documentation:
  - docs/thunderstore.md
  - docs/asset-bundles.md
  - docs/music.md
parent_task_id: TASK-048
priority: high
ordinal: 178000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Audit and complete the public-content boundary around the existing runtime-only Thunderstore package, not the retired standalone starter installers. Reuse the exact ZIP allowlist, source-byte verification and regression tests already implemented. Keep game references, extracted THPS content, soundtrack files and proprietary-derived packs out of public artifacts and caches. Local builds may read generated game references on the trusted build host; exclusion means they are never published or cached publicly, not that compilation must stop reading them. Review unresolved redistribution rights explicitly without inferring rights from an existing publication.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Document the existing six-entry runtime ZIP allowlist and required third-party notice; record unresolved project/content redistribution permissions and block newly affected content until resolved.
- [ ] #2 Retain and verify tests rejecting extra ZIP files, duplicate entries, stale approved binaries, game references and proprietary content; cover disguised replacements of approved filenames where testable.
- [ ] #3 Audit public upload and cache paths so only the validated ZIP and its checksum leave the trusted builder; generated game references and local-only source/output directories are never uploaded or publicly cached.
- [ ] #4 Audit optional THPS/OST workflows for explicit local-only opt-in and no publication; verify the current runtime and separately supplied original starter remain usable without those inputs.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-14 audit baseline: scripts/check_thunderstore_package.py enforces exact entries, duplicates and byte identity to approved sources. tests/test_thunderstore_package.py already covers missing/extra entries, stale binaries and duplicates. .github/workflows/thunderstore.yml runs the proprietary-reference build only on a trusted self-hosted host, uploading .tools/thunderstore/*.zip and *.zip.sha256; no cache step exists there. docs/thunderstore.md documents runtime-only content and NLayer MIT notice, but explicitly leaves the project license unresolved. Keep the task open for permissions and full path/local-workflow auditing rather than reimplement completed packaging controls.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
