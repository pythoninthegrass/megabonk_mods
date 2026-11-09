---
id: TASK-056.07
title: Automate BepInEx runtime repair after r2modmac Apply
status: Done
assignee: []
created_date: '2026-11-09 16:27'
updated_date: '2026-11-09T19:47:00Z'
labels:
  - bepinex
  - wine
dependencies: []
modified_files:
  - scripts/repair_bepinex.py
  - tests/test_repair_bepinex.py
  - taskfiles/wine.yml
  - docs/development.md
  - docs/player-guide.md
parent_task_id: TASK-056
priority: medium
ordinal: 209000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide a safe local Wine repair task after r2modmac applies BepInEx but omits dotnet and pack metadata. Reuse configured game paths, preserve manager-owned plugins/configuration and user content, and do not modify remote hosts automatically.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A wine:bepinex:repair task restores the omitted runtime and metadata from a pinned verified pack.
- [x] #2 Dry-run makes no game or prefix changes; repeat repairs are safe and existing backups are never overwritten.
- [x] #3 Repair refuses to mutate a running game and safely parks the MelonLoader proxy.
- [x] #4 Report the winhttp override requirement without changing plugins, configuration or UserData.
- [x] #5 Focused automated tests and usage documentation cover repair and refusal paths.
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
Approved approach: add scripts/repair_bepinex.py and task wine:bepinex:repair using existing game_paths and asset_download helpers. Write focused tests first. Pin the official pack archive checksum and support an explicit local archive or opt-in download into .tools. Validate all inputs before writes; dry-run plans only. Refuse running Megabonk processes, unsafe paths, conflicting runtime files and backup collisions. Copy only missing pack dotnet and metadata, then park version.dll without replacing backups. Report launcher-supplied winhttp override rather than editing Wine registry. Document local invocation and test without touching remote game installs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation and validation complete, pending commit and full task-check hygiene. Tests were added first and initially failed collection because the helper did not exist. All 1,298 Python tests now pass, including 16 focused repair tests. Targeted Ruff checks (including requested import ordering), Markdownlint, git diff --check, site sync/type check and Task dry-run pass. Official pinned archive verified to contain 189 repair files (69,054,852 bytes). Existing pytest-asyncio loop-scope warning and Astro clipboard deprecation hint remain. Did not run task check because it builds/deploys the mod into the local game; no game or remote install was modified. No commit/push requested for this implementation yet.

Maintainer approved committing/pushing the helper and pulling it on the authoring Mac, but will run the repair manually. Remote checkout is clean on main. No remote repair or game launch is authorized for this step.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `scripts/repair_bepinex.py` and the `wine:bepinex:repair` task. It restores the dotnet runtime and pack metadata r2modmac omits from a pinned, checksum-verified pack, parks the MelonLoader `version.dll` proxy, and reports the winhttp override requirement without editing plugins, configuration or UserData. Dry-run makes no changes, repeat runs are safe, existing backups are never overwritten, and it refuses to touch a running game. 16 focused tests and usage docs in `docs/development.md` and `docs/player-guide.md`. `task check` passes (1308 passed, 1 skipped). No remote host was modified; the repair is run manually by the maintainer.
<!-- SECTION:FINAL_SUMMARY:END -->
