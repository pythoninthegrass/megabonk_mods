---
id: TASK-069.04
title: Install BepInEx and the level editor mod into the game folder
status: Done
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies:
  - TASK-069.02
  - TASK-069.03
references:
  - docs/modding-setup.md
  - scripts/repair_bepinex.py
  - go/internal/proton/proton.go
  - pkg/README.md
parent_task_id: TASK-069
priority: high
ordinal: 240000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When the player opts in, the installer replaces the manual BepInEx install in `docs/modding-setup.md` ("Installing by hand"). It works from the downloads that TASK-069.02 resolves.

**Steps:**
1. Extract everything under the BepInEx pack zip's `BepInExPack/` next to `Megabonk.exe`. This includes `dotnet/`, `.doorstop_version` and `changelog.txt`, which r2modmac's Apply misses.
2. Merge the mod zip's `BepInEx/` into the game folder.
3. Park a leftover MelonLoader `version.dll` as `version.dll.bak`.
4. Make sure Wine loads the native `winhttp`:
   - Plain Wine or CrossOver prefix: write `winhttp=native,builtin` into the prefix's `user.reg`. `go/internal/proton` already has `SetDllOverride` and `ReadDllOverride` for this.
   - Proton: give the player the Steam launch option `WINEDLLOVERRIDES="winhttp=n,b" %command%` through the existing `ShowLaunchOption` Copy UI.
   - Native Windows: no override.

`scripts/repair_bepinex.py` is the reference for the expected file set and the `version.dll` handling.

Detecting whether the mod is already installed, so the GUI checkbox can default sensibly, belongs here as well: `BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll` together with the install record.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 After install, the game folder contains every file from the pack's BepInExPack/ tree, including dotnet/, .doorstop_version and changelog.txt, and the mod's BepInEx/plugins/MegabonkLevels/ files
- [x] #2 An existing version.dll is renamed to version.dll.bak and restored on uninstall
- [x] #3 A Wine or CrossOver prefix has the winhttp native,builtin override after install and it is removed on uninstall
- [x] #4 Under Proton the player is shown the WINEDLLOVERRIDES launch option with a copy button
- [x] #5 Native Windows installs set no override
- [x] #6 Whether the mod is already installed, and at which version, is detectable
- [x] #7 Unit tests cover each platform branch with temporary game folders and prefixes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes — **not runnable in this worktree**: `task check` starts with `mod:build`, which fails with 1228 `CS0246` errors for Unity/TextMeshPro types because the game's Il2Cpp assemblies (`.tools/il2cpp_dump`, gitignored) are absent here. This is a worktree-environment limitation, not a regression: the change is Go-only and touches no `.cs`, and the runnable `task check` components all pass — `installer:test` (gofmt + `go vet` + `go test` over all 17 packages), `installer:build`, `installer:verify-static`, and `scripts:test` (1498 passed, 60 skipped).
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution

## Implementation Notes

New package `go/internal/modinstall` is the Thunderstore install path (`Install` / `Uninstall` / `Detect` / `DetectAgainst`), separate from the offline package path in `plan`. The file-level loader work is in the new `go/internal/content/bepinex.go`; the `winhttp` override naming is in the new `go/internal/proton/bepinex.go`; the archive download half is in `thunderstore`.

The run is ordered resolve → pin → fetch → unpack-and-check → write: nothing is fetched before both versions are known, and nothing touches the game directory before both archives are verified. The loader pack is always checked against a SHA-256 (caller `--bepinex-sha256` wins, else the built-in `thunderstore.bepinexPins` table, else refusal before any download). Thunderstore publishes no checksum for the mod, so its archive is checked against a caller pin, or the digest the install record kept for that exact version on a repair, or fetched fresh and proven by unpacking the complete plugin set (`MegabonkLevels.Mod.dll`, `NLayer.dll`, `NLayer.LICENSE.txt`) in a temporary folder before any of it reaches the game directory; the digest it turns out to carry is recorded so the next repair can validate the cache. An archive in the cache with no digest to check it against is never reused — cache names derive from the version alone, so a release republished under the same version would otherwise answer from stale bytes forever.

The whole run is one transaction: a cancelled or failed run removes what it placed, restores every file it overwrote from a pre-write backup (including a player-edited `doorstop_config.ini`), collapses only folders it emptied, and clears a prefix override it set. What a rollback could not restore is named in the error rather than swallowed. Foreign installs are left alone — the install record is the only thing distinguishing this installer's files from a mod manager's, so without a recorded loader install uninstall removes nothing, and a `version.dll` is parked only when a `MelonLoader/` folder sits behind it (a proxy nobody can account for is refused by name).

Per platform: Wine/CrossOver get `winhttp=native,builtin` via `wine reg add` when a wine binary is supplied, falling back to the `proton` registry writer otherwise (the run reports which); Proton gets the launch option through the existing `ShowLaunchOption` Copy UI; native Windows sets neither override nor prefix.

Two already-merged packages carry minimal additions this task needs: `ppath.SafeRelative` (one archive-member safety rule, replacing a duplicate) and `thunderstore`'s `DownloadMod`/`CheckModDigest`/`ArchiveName` plus a consolidated `cachedArchive` cache-read helper. Dead duplicates found and removed rather than left in place: a second `version.dll` parking implementation in `modinstall` (content's `inspectVersionProxy`/`parkVersionProxy` is the single rule) and a second proxy restore. 40 unit tests cover all three platform branches, verification refusal paths, dry-run, cancel/rollback, and the detect/uninstall round-trip, with no test reaching the network.
<!-- DOD:END -->
