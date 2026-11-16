---
id: TASK-056
title: >-
  Migrate MegabonkLevels from MelonLoader to BepInEx IL2CPP for Thunderstore
  distribution
status: Done
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-14 21:50'
labels:
  - bepinex
  - thunderstore
dependencies: []
references:
  - 'https://thunderstore.io/c/megabonk/p/BepInEx/BepInExPack_IL2CPP/'
  - 'https://github.com/Zard-Studios/r2modmac'
  - 'https://wiki.thunderstore.io/mods/creating-a-package'
  - 'https://github.com/thunderstore-io/thunderstore-cli'
documentation:
  - docs/development.md
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The mod currently loads through MelonLoader, which no Thunderstore mod manager installs: r2modmac supports BepInEx but explicitly does not implement MelonLoader install/launch, and the Megabonk community's pinned, manager-installed loader is BepInExPack_IL2CPP (6.0.788). Publishing with one-click manager installs therefore requires moving the mod to BepInEx 6 IL2CPP, which touches the mod runtime, the csproj reference set, the dev harness, and packaging.

Runtime target on macOS: the Windows build under a plain-Wine prefix - Wine is preferred over CrossOver for this work.

Structure: two timeboxed spikes close with a recorded go/no-go before any sure-thing task starts. Both no-go closes the effort with findings; a single no-go re-scopes rather than commits.

Rollback strategy (binding for every subtask):
1. Branch isolation - all port work happens off main; main keeps building and shipping the MelonLoader version until the cutover merge.
2. Game-dir reversibility - the BepInEx install is additive and inventoried (doorstop files plus the BepInEx folder); MelonLoader launch options stay configured throughout; applying the recorded rollback manifest restores the MelonLoader-only launch.
3. Release reversibility - tag the last MelonLoader-only build before cutover; Thunderstore versions are immutable, so existing installs keep working; deprecate an old release only after a soak period, never delete.
4. Decision gate - if a spike no-gos, archive the sure-thing subtasks and close this parent with findings; nothing on main needs reverting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both spike subtasks are closed with a recorded go/no-go before any sure-thing subtask moves to In Progress
- [x] #2 All sure-thing subtasks are completed and their rollback constraints held throughout
- [x] #3 Main never stopped building the MelonLoader version before the cutover merge
- [x] #4 Before the first publish, the last MelonLoader-only build is tagged and the licensing decision for bundled level/pack content is recorded
- [x] #5 Docs describe the BepInEx install, the supported managers, and how a user or developer reverts to the MelonLoader setup
- [x] #6 If either spike no-gos, this parent is closed with findings and the sure-thing subtasks are archived without main-branch changes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved continuation after both GO spikes: TASK-056.03 ports the runtime on bepinex-port (off bepinex-spike), then TASK-056.04 migrates script paths/log scraping/relaunch and MCP integration, then TASK-056.05 handles Thunderstore packaging and manager install verification. Runtime smoke tests use the unchanged harness queue and direct BepInEx log reads until the script migration. Keep assignees empty; main remains MelonLoader until cutover.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-08 Spike TASK-056.01 closed GO for BepInEx as the loader. Findings the sure-thing subtasks must carry: (1) r2modmac Apply structurally omits the pack's dotnet/, .doorstop_version and changelog.txt - the Thunderstore package or install docs must supply them or BepInEx silently never starts; (2) the winhttp=n,b DllOverrides line must be added manually to the target prefix's user.reg with no wine process running (wine reg is unusable over SSH), and the override is per-prefix; (3) the port replaces MelonLoader - version.dll and the doorstop cannot be active together; (4) r2modmac Play is unusable for the Windows-under-Wine build (CrossOver runner only, and CrossOver's expired-trial dialog gates that runner) - the manager is for file management only, launch stays task game:run/scripts/launch_game.py; (5) the manager's per-mod disable is file-level sync and bidirectional (files wiped from the game dir vanish from the profile on next sync); (6) the dev harness is resident in the MelonLoader mod and is inert in BepInEx-only runs - port it with the mod (TASK-056.04); (7) community plugin quality varies (the Noelle skin pack throws NullReferenceException on hover-preview, spams lilToon shader errors and builds physics points on the main thread) - verify packages individually, disable-by-compare. Full evidence in TASK-056.01 notes; working launch method and conditions documented in docs/development.md under 'Running BepInEx under Wine'. Scope note: all positive results are Wine 11.18 against the CrossOver bottle prefix; the plain-Wine prefix was never tested end to end.

Harness/script migration completed on bepinex-port in 6d78839. Paths, relaunch/log scraping, Wine doorstop override, failure evidence and MCP tools verified against the running BepInEx game. task check passed (2781 C#, 1160 Python tests plus installer checks/lint); main untouched and legacy proxy parked. Existing MCP connections require restart to reload changed Python modules. Packaging/manager install verification remains the next subtask; no cutover or publish performed.

Packaging and clean-profile manager verification implemented in 91e25a2, building on maintainer manifest-validator commit d7cb135. Public product is Megabonk Level Editor; package assets under pkg/, repository name unchanged. Final ZIP installed through r2modmac into an isolated clean game copy and verified under Wine: plugin/dependency hashes, level gameplay, editor edit/undo/save-copy and rendered console all pass. Full task check passed (2786 C#, 1267 Python tests plus build/installer/lint). Local annotated melonloader-final preserves main at d35acdc, without push/merge. Subtask 056.05 remains In Progress solely for release/publication gates: explicit approval, team token, public documentation access, remote tag availability and release-terms confirmation. Main and the reversible loader setup remain intact; nothing published or deprecated.

Maintainer-approved pre-merge cleanup is complete: legacy package:linux/windows/macos tasks are internal (hidden and directly non-invokable), setup/player/legacy-reference docs and site entry-point copy now describe the BepInEx/runtime-only route, and the approved melonloader-final tag is pushed with remote target d35acdc verified. Full task check passes (2786 C#, 1271 Python tests); website build/check plus 13 site tests and desktop/mobile rendered-copy review pass. No main merge, feature-branch push, website deployment or Thunderstore publication performed during cleanup. Merge blockers identified in the readiness check are resolved; publication gates remain separately tracked on 056.05.

Closure verification 2026-11-14 (parent reconciliation, no code changes): all seven subtasks (056.01-056.07) are Done. Fresh `mise exec -- task check` on main is green: 0 C# errors, 1552 Python tests passed (6 skipped), ruff/markdownlint/deno fmt+lint clean.

Cutover confirmed in-tree: `src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj` references BepInEx.Core and BepInEx.Unity.IL2CPP, so main now builds the BepInEx plugin. The rollback tag `melonloader-final` is present and peels to d35acdc. Product versions are synchronized at 0.2.0 across thunderstore.toml, pkg/manifest.json and the mod csproj.

Live package state (Thunderstore experimental package API): pythoninthegrass-Megabonk_Level_Editor latest is 0.2.0, `is_active: true`, `is_deprecated: false`, dependency `BepInEx-BepInExPack_IL2CPP-6.0.788`, categories Mods/Tools. The 0.2.0 submission went through the automated gate/build/approval/publish flow of TASK-056.06, not a manual upload.

AC #5 scope note: the install and rollback docs are authoritative for the tested route - Thunderstore manager install plus BepInExPack IL2CPP (docs/player-guide.md, docs/modding-setup.md, docs/thunderstore.md#rollback, which covers parking winhttp.dll/doorstop_config.ini and restoring the preserved MelonLoader version.dll from the legacy tag). r2modmac 1.1.0 is the manager whose menus and profile behaviour were actually observed; other managers are described generically as 'a compatible mod manager'. Manager-specific log-capture wording remains open under TASK-062 and is deliberately not claimed as done here.

AC #6 is vacuously satisfied: both spikes closed GO, so the no-go archival path never applied and main needed no reverts.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Migrated Megabonk Levels from MelonLoader to BepInEx 6 IL2CPP and shipped it as the public Thunderstore product.

What shipped:
- Runtime ported to a BepInEx IL2CPP BasePlugin with the dev harness migrated onto BepInEx log paths and doorstop handling (TASK-056.03, TASK-056.04); the harness queue contract stayed unchanged so scripts and MCP tooling kept working.
- Runtime-only Thunderstore package `Megabonk_Level_Editor` under the team namespace: mod DLL, NLayer plus its MIT notice, manifest, README and icon, declaring BepInEx-BepInExPack_IL2CPP 6.0.788. No levels, packs, music, installers, PDBs or generated game/Unity interop.
- Path-filtered automated builds and approved publication (TASK-056.06) and a safe Wine-side BepInEx runtime repair for r2modmac's incomplete Apply (TASK-056.07).
- 0.2.0 is live on Thunderstore, submitted by the automated workflow.

Why: no Thunderstore mod manager installs MelonLoader, so manager-based installs required BepInEx; the community's pinned loader is BepInExPack_IL2CPP.

Rollback and reversibility held as planned: main kept building MelonLoader until cutover, the final MelonLoader-only build is preserved as the annotated `melonloader-final` tag (d35acdc), Thunderstore versions were never deleted or deprecated, and docs/thunderstore.md#rollback documents returning to the MelonLoader setup.

Verification: two GO spikes recorded findings that then governed the sure-thing work (r2modmac omits `dotnet/`, `.doorstop_version` and `changelog.txt`; the per-prefix `winhttp=n,b` override; the two loaders must never both be active; r2modmac Play is unusable for the Wine-hosted Windows build). Clean-profile manager install and in-game editor/console/level smoke tests passed on the final archive, and the published CDN ZIP was byte-compared to the tested local build. Closure reran `task check` green (0 C# errors, 1552 Python tests, lint).

Follow-ups outside this task: TASK-062 (mod-manager log capture guidance), Google/Discord sign-in credentials for the gallery, and the still-open onboarding phases 047/048/049/050.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
