---
id: TASK-069.02
title: Add a Thunderstore client that resolves the mod and BepInEx pack downloads
status: Done
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
- [x] #1 The latest mod version, its download URL and its BepInEx pack dependency version are resolved from Thunderstore
- [x] #2 Dependency strings of the form Namespace-Name-Version are parsed, including names containing underscores and versions with three parts
- [x] #3 A downloaded archive whose SHA-256 does not match a known pinned hash is rejected before anything is installed
- [x] #4 Requests send a browser User-Agent
- [x] #5 The live response shape of the experimental package endpoint has been confirmed and recorded in docs/thunderstore.md
- [x] #6 Unit tests run against a local test HTTP server with no live network access in go test
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

- `go/internal/thunderstore` (standard library only) adds `Client.Resolve`, which reads `latest.version_number`, `latest.download_url` and `latest.dependencies` from `/api/experimental/package/<ns>/<name>/` and reports the mod version, download URL and the `BepInEx-BepInExPack_IL2CPP` version, plus `Client.DownloadBepInEx`, which fetches the CDN archive only after checking its SHA-256 against the caller's pinned digest, and before that checks the archive parses as a zip with every member under `BepInExPack/`. Bytes land through a `.part` file renamed into place, so a rejected or interrupted download leaves nothing at the target.
- Dependency parsing follows the site's `PackageReference.parse` (version, then name, from the right), matching the port in `scripts/validate_thunderstore_manifest.py`. A consequence worth recording: for `Dash-Ed-Team-Mythic-TestMod-1.1.0` the namespace is `Dash-Ed-Team-Mythic` and the name `TestMod`, not the split the hyphens might suggest. The task's own example expectation was corrected to the upstream rule.
- `DownloadBepInEx` rejects a `target` containing `.` or `..` components, a NUL, or a backslash or colon, because `filepath.Join` collapses `..` before any check could see it. Without this, a caller-supplied path such as `dir/sub/../escaped.zip` wrote the archive outside the folder the caller intended. This was found by testing the guard's absence, not by the acceptance criteria.
- `TestNoResolvableHostInSources` scans the package's own sources for a host the client could dial, following the equivalent check in `internal/site`, so the no-network guarantee is enforced rather than assumed. `go test` also passes with `HTTP_PROXY`, `HTTPS_PROXY` and `ALL_PROXY` pointed at a closed port.
- `task check` cannot complete in this checkout: its first stage, `mod:build`, needs the game's `BepInEx/interop` assemblies and fails with 1228 `CS0246` errors. This was verified as pre-existing by stashing all of this task's work and rebuilding pristine source, which fails identically. The gates that do not need the game were run and pass: `installer:test`, `mod:test` (2836), `scripts:test` (1498 passed, 60 skipped), `lint`, and `installer:verify-static` (MyGo still the only direct module dependency).
