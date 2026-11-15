---
id: TASK-069.02
title: Add a Thunderstore client that resolves the mod and BepInEx pack downloads
status: To Do
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies: []
references:
  - thunderstore.toml
  - scripts/repair_bepinex.py
  - scripts/validate_thunderstore_manifest.py
  - docs/thunderstore.md
parent_task_id: TASK-069
priority: high
ordinal: 238000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When a player opts in, the installer installs or updates the level editor mod. That requires the latest `pythoninthegrass/Megabonk_Level_Editor` package from Thunderstore and the `BepInEx-BepInExPack_IL2CPP` version that package depends on (currently 6.0.788, see `thunderstore.toml`).

The new package goes in `go/internal/thunderstore` and uses the standard library only.

**Endpoints:**
- Metadata: `GET https://thunderstore.io/api/experimental/package/<ns>/<name>/` should return `latest.version_number`, `latest.download_url` and `latest.dependencies`, as `Namespace-Name-Version` strings.
  - **Unconfirmed:** nothing in the repo uses `download_url` yet. Check the live response shape before relying on it.
  - Requests need an ordinary browser `User-Agent`; otherwise Cloudflare answers with error 1010 (`docs/thunderstore.md`).
- The BepInEx pack zip comes from the CDN: `https://gcdn.thunderstore.io/live/repository/packages/BepInEx-BepInExPack_IL2CPP-<ver>.zip`.
  - Its files sit under `BepInExPack/`.
  - `scripts/repair_bepinex.py` pins 6.0.788's SHA-256; treat that as a known-good check for that version.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The latest mod version, its download URL and its BepInEx pack dependency version are resolved from Thunderstore
- [ ] #2 Dependency strings of the form Namespace-Name-Version are parsed, including names containing underscores and versions with three parts
- [ ] #3 A downloaded archive whose SHA-256 does not match a known pinned hash is rejected before anything is installed
- [ ] #4 Requests send a browser User-Agent
- [ ] #5 The live response shape of the experimental package endpoint has been confirmed and recorded in docs/thunderstore.md
- [ ] #6 Unit tests run against a local test HTTP server with no live network access in go test
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
