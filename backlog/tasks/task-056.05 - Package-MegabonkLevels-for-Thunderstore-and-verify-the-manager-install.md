---
id: TASK-056.05
title: Package MegabonkLevels for Thunderstore and verify the manager install
status: In Progress
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-09 02:59'
labels:
  - bepinex
  - thunderstore
dependencies:
  - TASK-056.04
  - TASK-056.01
modified_files:
  - thunderstore.toml
  - pkg/README.md
  - pkg/manifest.json
  - pkg/icon.png
  - pkg/NLayer.LICENSE.txt
  - scripts/check_thunderstore_package.py
  - tests/test_thunderstore_package.py
  - taskfiles/package.yml
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
  - README.md
  - docs/thunderstore.md
  - docs/development.md
  - docs/player-guide.md
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
- [ ] #5 Publishing uses the Thunderstore team account with no personal credentials in the repo, and any superseded release is deprecated, not deleted
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
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
