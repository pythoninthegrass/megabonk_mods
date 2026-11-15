---
id: TASK-069.08
title: Publish signed installer binaries on GitHub releases
status: To Do
assignee: []
created_date: '2026-11-15 06:00'
labels:
  - installer
  - release
dependencies:
  - TASK-069.05
  - TASK-069.07
references:
  - taskfiles/installer.yml
  - scripts/notarize_macos.py
  - .github/workflows/release-please.yml
  - release-please-config.json
parent_task_id: TASK-069
priority: medium
ordinal: 244000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Players need a download link for the installer. Today the GitHub releases created by release-please carry no assets, and the only distribution channel is Thunderstore.

`task installer:build` already cross-compiles `darwin/arm64`, `linux/amd64` and `windows/amd64` without cgo, and `task installer:verify-static` checks the binaries.

Two constraints:
- An unsigned macOS binary is blocked by Gatekeeper. `scripts/notarize_macos.py` and the codesign step in the old `package:macos` task are the existing signing path, so carry them over before TASK-069.06 removes that task.
- The self-hosted runner and secrets are described in `docs/thunderstore.md` (CI section) and `.github/workflows/`.

Coordinate with TASK-048 (public starter releases) on what goes into a public release.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each release-please GitHub release carries the Windows, Linux and macOS installer binaries with SHA-256 checksums
- [ ] #2 The macOS binary is signed and notarized so it opens without a Gatekeeper override
- [ ] #3 A stable latest-download URL exists for each platform so docs and the site can link to it
- [ ] #4 The release workflow and any required secrets are documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
