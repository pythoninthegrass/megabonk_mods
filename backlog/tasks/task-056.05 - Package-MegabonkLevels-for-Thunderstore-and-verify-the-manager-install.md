---
id: TASK-056.05
title: Package MegabonkLevels for Thunderstore and verify the manager install
status: Done
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-09 04:18'
labels:
  - bepinex
  - thunderstore
dependencies:
  - TASK-056.04
  - TASK-056.01
modified_files:
  - .env.example
  - .github/workflows/release-please.yml
  - .github/renovate.json5
  - .release-please-manifest.json
  - release-please-config.json
  - thunderstore.toml
  - pkg/README.md
  - pkg/manifest.json
  - pkg/icon.png
  - pkg/NLayer.LICENSE.txt
  - scripts/check_thunderstore_package.py
  - tests/test_thunderstore_package.py
  - tests/test_build_player_package.py
  - tests/test_release_versions.py
  - taskfiles/package.yml
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
  - src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj
  - site/package.json
  - site/package-lock.json
  - README.md
  - docs/thunderstore.md
  - docs/development.md
  - docs/player-guide.md
  - docs/modding-setup.md
  - docs/player-installer.md
  - docs/starter-level.md
  - docs/website.md
  - site/src/content/start.md
  - site/src/content/level.md
  - site/src/content/compatibility.md
  - site/tests/site.test.js
parent_task_id: TASK-056
priority: medium
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The migration exists so users can install from Thunderstore with a mod manager. The package must carry the manifest, readme and icon, declare the BepInExPack dependency, publish via tcli, and install cleanly through r2modmac into the Wine-hosted game. Licensing for any bundled level or pack content must be decided before the first publish.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Package source (thunderstore.toml, manifest.json, README.md, 256x256 icon.png) lives in the repo and tcli build produces a valid package
- [x] #2 The manifest declares the dependency BepInEx-BepInExPack_IL2CPP-6.0.788
- [x] #3 The package installs through r2modmac into the Wine-hosted game and the mod loads and runs in-game from that install
- [x] #4 The last MelonLoader-only build is tagged before the first publish, and the licensing decision for bundled level/pack content is recorded
- [x] #5 Publishing uses the Thunderstore team account with no personal credentials in the repo, and any superseded release is deprecated, not deleted
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved implementation plan (including maintainer naming/layout corrections):
1. Continue on bepinex-port; preserve main, legacy loader rollback and existing game/profile data.
2. Product name: Megabonk Level Editor. Thunderstore package identifier: Megabonk_Level_Editor. Team namespace confirmed by maintainer and configured in thunderstore.toml. Repository remains megabonk_mods; keep internal assembly and GUID stable. Put package README, manifest, icon and dependency notice under pkg/, with root thunderstore.toml as build/publish configuration.
3. Add tests first for metadata, package allowlist, stale binaries and malformed ZIP/assets; build with local pinned tcli and validate. Ship plugin, NLayer and its MIT notice only, with BepInExPack_IL2CPP 6.0.788 as dependency. Exclude bundled levels/packs/music; do not invent a project-wide license.
4. Document install, Wine/r2modmac limitations, rollback and release gates. Review package README in Thunderstore Markdown Preview and validate manifest (official validator requires logged-in team access). Keep GitHub links; maintainer plans to make repository public later, with visibility unchanged by this task.
5. Verify final ZIP in a new clean r2modmac profile. Maintainer will drive manager UI. Use a separately cloned clean base-game folder under .tools/thunderstore-smoke-game to keep Apply away from the development install; preserve manager settings/profile backups and baseline file inventory. Import ZIP, Apply, verify installed hashes, then launch under Wine and test in game. Account for manager's missing runtime/override without rebundling loader.
6. Run task check, package checks and docs/lint; commit conventionally after verification. Confirm final MelonLoader-only tag name/target before creating it.
7. Publishing is a separate explicit approval checkpoint. Use only a team service-account token through an untracked environment, publish the exact tested ZIP with tcli --file, and never delete superseded releases. No automatic deprecation or cutover merge.

Maintainer approved pre-merge cutover cleanup and pushing the existing melonloader-final tag. Add test-first guards that disable legacy package:windows/linux/macos outputs on the BepInEx branch, refresh stale setup/player/site entry-point instructions without deploying the website, verify applicable checks, commit the cleanup and push only the approved rollback tag. Do not merge main, publish to Thunderstore or change repository visibility. Preserve the already tested package ZIP; packaged asset changes would require rebuilding and repeating the ZIP test.

Maintainer clarified the legacy packaging change: mark only package:linux, package:windows and package:macos internal rather than deleting their implementation. Context7 /websites/taskfile_dev confirms internal tasks are hidden from both listings and reject direct CLI invocation. Preserve their contract tests through a temporary test-only wrapper; do not expose any production wrapper.

Requested release-please configuration change — proposed, awaiting implementation-plan approval. Use Context7 /googleapis/release-please docs. Keep one root Python release and configure typed extra-files for the C# project/plugin, Thunderstore TOML/reference manifest, and site's Node metadata/lockfile. Initialize actual product-version fields to 0.1.0, with regression tests for synchronized current/future versions; leave dependency, schema, game and toolchain versions unchanged. Go installer has no embedded product version and should follow the shared Git release rather than changing its go.mod toolchain or inventing an unrelated version API. Existing untracked release-please config/manifest are maintainer work and must be preserved/extended. Important bootstrap distinction: the manifest's current 0.1.0 is treated as last released; explicitly configure release-as 0.1.0 for the first release if it must be exactly 0.1.0, and document removal after that release. Updating runtime/package versions invalidates the previously tested 0.0.1 ZIP and requires a fresh build/install check before publishing.

Maintainer approved the proposed version synchronization and release-please changes, and requested a RELEASE_PLEASE_TOKEN placeholder in .env.example. Review the newly added .github/workflows/release-please.yml as maintainer work and preserve it; verify its secret/config wiring without exposing or reading secret values. Proceed with tests first, product versions synchronized at 0.1.0, a temporary release-as pin and release automation documentation. Do not trigger releases, publish, or push without further approval.

Maintainer additionally requested .github/renovate.json5 cover every runtime language. Review existing user config, confirm actual tracked manifests and current Renovate manager support through Context7, then add explicit grouping for applicable Python/C#/Go/Node managers while preserving the Saturday America/Chicago schedule and avoiding dependency/version changes. Validate the config with Renovate's own validator. No dependency upgrades or remote bot/release actions authorized.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Prerequisites 056.01 and 056.04 are Done. Initial working tree was clean except task bookkeeping, on bepinex-port. No package config, root LICENSE or icon existed. Maintainer approved implementation and supplied team namespace, then corrected public name to Megabonk Level Editor and package asset directory to pkg/.

Implemented root thunderstore.toml plus pkg/README.md, reference manifest, 256x256 PNG rasterized from the existing site favicon and upstream NLayer MIT notice. Root README remains repository-oriented. Added build/check tasks using local tcli 0.2.4 and a strict ZIP allowlist/content validator, with tests written before implementation (initial missing-module failure; later explicit failures for tcli identity fields and malformed manifest types). BepInPlugin display name changed; GUID/assembly unchanged.

Initial task check passed: build, installer checks, C# tests, 1178 Python tests and lint. Package-specific tests subsequently expanded from 18 to 24; rerun pending. Direct dotnet build without Task initially missed environment-supplied reference paths; Task correctly loads .env, and both Debug and Release builds pass with zero warnings/errors.

README preview initially caught broken GitHub raw screenshot URLs because the repository is private. Replaced screenshots with the existing public showcase social image and editor asset; both loaded in Thunderstore's preview. Maintainer will make the repository public later; keep docs/issues links and treat public access as a release checkpoint. Official manifest validator now requires logged-in team selection; not yet validated there. Megabonk category API currently lists mods/tools but no AI Generated category.

Maintainer will drive r2modmac UI for the import/Apply test. Existing manager profiles/settings backed up to .tools/thunderstore-manager-backup. Prepared .tools/thunderstore-smoke-game from only base game files using APFS clones (70 inventoried base files), excluding loaders, plugins, configs, UserData and harness. Baseline hashes saved in the same gitignored backup directory. Original game data untouched except normal development build deployment. Final ZIP path/instructions to be supplied after rebuild. No publish, tag, cutover or release deprecation performed.

Read maintainer commit d7cb135 (local upstream-compatible manifest validator and 83 tests), plus shared uncommitted taskfiles/package.yml and docs/thunderstore.md wiring. Preserved those edits. Independently verified task package:thunderstore:manifest ONLINE=true and task package:thunderstore:check; both local checkers pass on the ZIP, and online manifest checks report no errors. Maintainer reports 1267 Python tests and lint passing after that contribution. Earlier full task check before that commit passed with 1184 Python tests. Official logged-in site confirmation remains a release checkpoint, not a blocker to local validation.

Final local package after public screenshot fix: .tools/thunderstore/pythoninthegrass-Megabonk_Level_Editor-0.0.1.zip; SHA-256 9eaea05259abbe8878f15aa8c7643ee781311cfce9e267a04849b01e1062f464. The reference/generated manifests and package file hashes validate. Thunderstore preview says All systems go; both public screenshot images loaded, evidence .tools/evidence/thunderstore-readme-preview.png. Awaiting maintainer-driven clean profile import/Apply into .tools/thunderstore-smoke-game, not the development game. No further packaged file changes planned before this test.

Clean-profile manager installation VERIFIED after maintainer Apply: new profile mega_test contains exactly the BepInEx dependency and Local-Megabonk_Level_Editor-0.0.1. Manager wrote BepInEx/plugins/Local-Megabonk_Level_Editor-0.0.1/MegabonkLevels/{MegabonkLevels.Mod.dll,NLayer.dll,NLayer.LICENSE.txt}; all three bytes/hashes match the unchanged tested ZIP. No dotnet/ was supplied by Apply, confirming the known manager issue. Staged 189 dependency-only files (dotnet/ plus .doorstop_version/changelog.txt) from BepInEx-BepInExPack_IL2CPP-6.0.788.zip, SHA-256 ce25d925f9eaba817214f5d6b2083b8e135ed0592b5a61b9f75ea5d4c02f5300.

For this host-side test copy outside the prefix, manager-written doorstop_config.ini had drive-less host paths. Backed it up under .tools/thunderstore-manager-backup and normalized target_assembly and dll_search_path_override to relative BepInEx/core paths. Launched the test executable explicitly under plain Wine using the existing launch helper and winhttp override; did not use task game:run because its current executable argument is hardcoded to the default Steam path despite a game-directory override. This limitation is documented, not changed in this task. Main and the development game files were not redirected.

Runtime evidence: BepInEx logs Loading [Megabonk Level Editor 0.0.1], MegabonkLevels mod initialized and Chainloader startup complete. Harness state/screenshot work. Separately supplied pack-free Bramblecrown Hill, saw it in level.list, loaded it and entered protected editor. Raise changed edit count 98 -> 99; Undo restored 98; save-level wrote thunderstore-manager-smoke.mblevel.json with 98 edits. Returned to gameplay and opened the rendered console with help editor. Screenshots: .tools/evidence/thunderstore-manager-{editor,gameplay,console}.png. Log copies are alongside them; full test inventory/hash report is .tools/thunderstore-manager-backup/verification.json. No base-game file hashes changed. The only logged error is the expected offline Steamworks.NET initialization warning; no plugin exceptions. Test game was quit through the harness; unrelated Wine processes were left alone.

Maintainer explicitly approved local annotated tag melonloader-final at d35acdc (current main, confirmed MelonLoader-only); created it without pushing or merging. Licensing/content decision: runtime-only ZIP excludes all levels, third-party packs and music; NLayer MIT notice included. No project-wide code license invented.

Final full task check passed: 2786 C# tests, 1267 Python tests, mod build, installer checks and lint. Existing warnings remain unchanged. Both ZIP/source and local manifest validation pass on the exact tested ZIP, whose SHA-256 remains 9eaea05259abbe8878f15aa8c7643ee781311cfce9e267a04849b01e1062f464. Docs now include the verified manager nesting and explicit-executable/relative-Doorstop caveats. Implementation commit pending; task remains In Progress because publication has not been approved/performed. Before publish: explicit approval, team service-account token, public documentation access, remote legacy tag availability and final release-terms confirmation. Do not rebuild the tested ZIP or deprecate anything automatically.

Implementation committed as 91e25a2 (feat(thunderstore): package Megabonk Level Editor for mod managers), preserving the maintainer's shared taskfile/docs wiring for d7cb135. Final task lint and git diff --check passed after the last documentation edits. Local annotated melonloader-final resolves to d35acdc; no branch or tag was pushed. AC1-4 and all DoD items are satisfied. AC5 remains open: no publication approved/performed. Keep status In Progress and final summary unset until publication/release gates are satisfied. Manager settings still point at the isolated test copy selected by the maintainer; original metadata backups are preserved if the maintainer wants to restore the development target.

Pre-merge cleanup implemented and verified. Added internal:true to the three legacy platform package tasks. Four new CLI/listing tests failed before the flags and now pass. Existing legacy-helper command tests now use a temporary test-only wrapper, retaining coverage without exposing the tasks publicly. No legacy package was built.

Refreshed modding setup and player guide around BepInEx/current Thunderstore packaging; corrected log helper/name references; marked the standalone installer contract as legacy and clarified Bramblecrown Hill is supplied separately. Website setup, compatibility and level prose now match BepInEx and runtime-only packaging. Preserved existing styling, interactions and unpublished-release messaging. A built-copy assertion failed against the existing live page and passes against the new build.

Pushed only the explicitly approved annotated melonloader-final tag; remote peeled target verified as d35acdc. No main merge or feature-branch push performed during cleanup.

Checks: full task check passes with 2786 C# tests and 1271 Python tests, plus installer checks/build/lint; focused packaging tests 70 passed. Site npm ci used the lockfile (0 vulnerabilities), npm run build, npm run check (0 diagnostics), npm test (3) and npm run test:site (10) pass. Mechanical UI detector returned no findings. Viewed the rendered setup copy at 1440x1000 and 390x844 with no horizontal overflow; screenshots .tools/evidence/cutover-site-{desktop,mobile}.png. Local preview stopped afterward. No site deployment performed. Existing design sidecar drift was noted but intentionally not repaired.

The previously tested Thunderstore ZIP is unchanged and both package checkers still pass. Publication remains gated; this cleanup addresses merge-readiness issues without publishing or changing repository visibility.

Release automation/version synchronization implemented after explicit maintainer approval. Preserved the maintainer's new root release-please config/manifest and workflow, extended one root Python release with typed extra-file updaters for C# project/plugin, uv.lock project entry, Thunderstore config/reference manifest and Node metadata/lockfile. Product versions are synchronized at 0.1.0; Python/uv were already at that version. Go has no embedded product version and follows the root Git release; toolchains, dependencies, schemas and boot-spike versions are unchanged. Config temporarily pins release-as 0.1.0 and omits component names in tags; docs require removing the pin after the first release.

Added the RELEASE_PLEASE_TOKEN placeholder to .env.example and explicit config-file/manifest-file inputs to the existing workflow. The workflow continues to use secrets.RELEASE_PLEASE_TOKEN. No secret values or .env contents were read. No workflow, release, publication, dependency update or push was triggered.

Renovate now explicitly groups npm, NuGet, Go modules and Python pep621/pep723 dependencies; the unused Cargo/Rust rule was removed at the maintainer's request. PEP723 scripts are explicitly enabled only under scripts/. Kept Saturday 10-11 AM America/Chicago as the allowed update window and gave lockfile maintenance that same schedule. Other default managers remain enabled.

Tests written first produced six initial failures. Installed release-please 17.11.2 only under gitignored .tools for an offline integration test, which applies its actual primary/generic/TOML/XML/JSON updaters and mergeUpdates composite handling to temporary copies at 0.2.3. This caught an upstream TOML tagged-value quirk: uv.lock filters must accept name.value as well as plain name. Corrected the selector; every product field advances while third-party dependency data and the Go toolchain stay unchanged. Upstream config and manifest JSON schemas validate; Renovate 44.222.5 strict config validation passes (optional native RE2 unavailable, validator uses standard RegExp for this simple pattern).

Final task check passes: 2786 C# tests, 1277 Python tests, build, installer checks and lint. Site npm ci/build/check (0 diagnostics), 3 clipboard tests and 10 static/server tests pass. Focused config/package/manifest suite: 117 tests. Documentation explains bootstrap behavior, token separation, future bumps, manager coverage and that Release Please does not itself publish to Thunderstore or deploy the site.

Built and validated new .tools/thunderstore/pythoninthegrass-Megabonk_Level_Editor-0.1.0.zip; SHA-256 c58a14f923fada36613fd531a204006965cfe93f07dd5198a1e0c443abf8a329. Online validation of the manifest in this ZIP reports no errors. Existing 0.0.1 artifact/evidence preserved, but AC3 is reopened because the new final 0.1.0 ZIP has not yet been re-imported into the manager or smoke-tested in game. DoD commit item reopened: these changes remain uncommitted alongside the maintainer's new .github/config files. No commit/push/publication performed in this phase.

Maintainer's latest r2modmac screenshots/profile metadata show Local-thunderstore-1.0.0 with fallback name/description. Diagnosis: imported .tools/thunderstore itself, which contains the built ZIP but no root manifest.json, rather than an extracted package root. The actual 0.1.0 ZIP has correct manifest, README, icon and plugin layout and still passes source/hash validation. Prepared .tools/thunderstore-import/Megabonk_Level_Editor-0.1.0 by extracting all six archive entries, checking every extracted byte against the validated ZIP and refusing overwrites of different files. Maintainer should remove only the mistaken thunderstore custom entry in the GUI, keep BepInEx, and import that specific extracted folder (not its parent); it has manifest.json and BepInEx directly inside. No profile/game files modified by this diagnosis; correct 0.1.0 import/runtime test still pending.

Maintainer confirmed the corrected 0.1.0 directory import worked, then reported successful launch/smoke testing after being asked to verify gameplay, console and editor change/undo/save. AC3 satisfied by maintainer-reported testing of the final archive. Maintainer subsequently published pythoninthegrass-Megabonk_Level_Editor 0.1.0 with tcli using the configured team account; output confirms successful publication and screenshots show the package icon, README images and Mods/Tools categories. No token values were read or recorded; no superseded public release requires deprecation. AC5 satisfied.

Independently downloaded the published CDN ZIP to .tools/evidence/thunderstore-published-0.1.0.zip and verified it matches the tested local archive byte-for-byte: SHA-256 c58a14f923fada36613fd531a204006965cfe93f07dd5198a1e0c443abf8a329. Public listing: https://thunderstore.io/c/megabonk/p/pythoninthegrass/Megabonk_Level_Editor/ . Experimental version API returned 404, but the successful CDN download/hash comparison confirms publication. Installation directly from the published manager listing has not been separately tested.

All acceptance criteria are now checked; task remains In Progress because the release-version/automation changes remain uncommitted (DoD4 open). main matches origin/main for committed history. Repository visibility is still PRIVATE, so public package README GitHub documentation/issues links remain inaccessible to ordinary users. No visibility change, commit/push, GitHub release or website deployment performed. Keep release-as 0.1.0 until the first GitHub release exists, not merely this Thunderstore publication.

Committed the remaining release work at the maintainer's request: 7a07ed2 (grouped runtime Renovate updates) and 9800a2c (synchronized 0.1.0 product versions, release automation, tests and documentation). Focused release/package/manifest suite rerun: 117 passed; git diff --check clean. Unrelated untracked GitHub funding/actionlint/composite-action scaffolding remains untouched. No push, release trigger or visibility change performed. All acceptance criteria and Definition of Done items are now satisfied.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Packaged and published Megabonk Level Editor 0.1.0 under the configured Thunderstore team. The runtime-only ZIP includes the mod, NLayer and its MIT notice, declares BepInExPack IL2CPP, and excludes levels, packs, music and loader/game assemblies. Clean-profile Wine/r2modmac testing and maintainer-reported final-version testing verify installation and gameplay/editor use; the published CDN archive matches the tested ZIP byte-for-byte. Preserved the MelonLoader rollback tag and documented manager/runtime limitations.

Added synchronized product versions and one root Release Please workflow, with targeted updaters and regression tests that preserve dependency/toolchain versions. Renovate covers npm, NuGet, Go and Python manifests/inline scripts. Full checks previously passed with 2786 C# and 1277 Python tests plus website checks; final focused rerun passed 117 tests. Implementation is conventionally committed.

Follow-ups: the repository remains private, so public GitHub documentation/issues links are inaccessible; direct installation from the published manager listing is not separately tested. Remove the temporary release-as pin only after the first GitHub release exists. No push, repository visibility change or website deployment was performed.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
