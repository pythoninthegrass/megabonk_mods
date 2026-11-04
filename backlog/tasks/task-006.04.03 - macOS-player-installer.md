---
id: TASK-006.04.03
title: macOS player installer
status: In Progress
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-11-04 01:29'
labels:
  - tooling
dependencies: []
references:
  - scripts/install_melonloader.py
documentation:
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006.04
priority: low
ordinal: 123000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Megabonk has no macOS build, so a Mac player runs the Windows build under Wine or CrossOver — the same mechanism this repo's own contributor flow uses. Their setup is the most manual of the three platforms: a Wine prefix or CrossOver bottle to get right, the DLL override that MelonLoader's own installer would normally set for version.dll, a .NET 6 runtime inside that prefix, and the windows-platform pack bundles. The contributor tooling already solves most of it — game-directory and prefix resolution, the DLL override, the pinned loader version — but only for someone with a repo checkout and the task toolchain, which a player does not have.

This subtask delivers the macOS half of the package contract so a Mac player has one command too. CrossOver is commercial software, so the flow has to work with free Wine as well and must not assume CrossOver is installed. A notarized .dmg is not required; a script with a GUI progress surface is the accepted deliverable.

Until this lands, the player guide covers macOS only by pointing at the contributor setup doc, which is not a route a non-technical player can follow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Running the installer on a Mac with Megabonk installed leaves the game launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL placed, and the game's Windows build running under the prefix
- [ ] #2 It works with both plain Wine and CrossOver's Wine, and does not require the commercial product to be installed
- [x] #3 It applies the DLL override the loader needs and installs the .NET 6 runtime into the prefix when absent
- [x] #4 The prefix and game directory are discovered without asking the player to install the repo's toolchain, with an explicit override for a non-default location
- [x] #5 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not; uninstall restores a vanilla game
- [x] #6 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [x] #7 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless; a failure it cannot resolve exits nonzero with a message that says what to do
- [x] #8 Verified end to end on the macOS machine, documented, and the player guide's macOS section becomes a real install route pointing at the installer rather than the contributor doc
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approach: extend the Go installer (go/) with a darwin/arm64 target and a Wine runtime mode, the way TASK-006.04.02 added native Windows. Reuses plan, manifest, content, ui, window (MyGo Metal backend; no cgo, so darwin/arm64 cross-compiles from any host). arm64 only: no x86_64 Mac is available to test.

1. Tests first, then discovery on macOS: prefer plain Wine over CrossOver. Order: explicit --prefix / --game-dir, plain-Wine prefixes (~/.local/share/megabonk/wine, ~/.wine), then CrossOver bottles under ~/Library/Application Support/CrossOver/Bottles/*. Find drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk, reuse Steam library parsing and gamebuild classification. No dependency on the repo .env or game_paths.py.
2. DLL override: find a wine binary (plain Wine from PATH or /Applications/Wine*.app, or CrossOver's wine with the bottle set), run through proton.SetDllOverride; fall back to editing user.reg when none is found.
3. .NET 6: pre-seed into MelonLoader/Dependencies/dotnet as on Windows; fall back to drive_c/Program Files/dotnet in the prefix if that does not work under Wine.
4. plan/cli: a wine runtime mode with no launch option, a --prefix override, uninstall removes the override and runtime; re-run no-op and repair ride the install record.
5. Packaging: task package:macos builds the darwin/arm64 binary and runs build_player_package.py --platform macos; Go and Python manifest loaders accept macos. Launcher and Gatekeeper handling decided separately (see notes).
6. Verify end to end on both Macs (plain Wine and CrossOver), update docs/player-installer.md and docs/modding-setup.md, point the player guide's macOS section at the installer.

Risks: first launch under Wine downloads Cpp2IL (~35 s, needs network); unsigned binary and Gatekeeper; the second Mac is asleep when work starts.

Plan changes during execution: step 6 verified on plain Wine on one Mac (mbp) instead of both Macs, since CrossOver's licence expired; step 5 gained notarization through scripts/notarize_macos.py; the .NET fallback into the prefix in step 3 was not needed because the Dependencies/dotnet placement worked under Wine.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions: CrossOver's licence is expired, so plain Wine is the development and verification runtime and the preferred discovery target; CrossOver bottles are a fallback covered by unit tests and a --dry-run against a real bottle, not run end to end. Arm64 only (no Intel Mac to test). No .command or .sh on macOS or Linux: the package carries a bare megabonk-installer binary, meant to be fetched by a curl-to-sh bootstrap (a curl download is not quarantined, so Gatekeeper does not gate it); the bootstrap and a published download URL are not part of this task. Windows keeps install.exe.

Delivered (all committed on main): steam.WineClientRoots (plain Wine ~/.local/share/megabonk/wine and ~/.wine before CrossOver bottles), winePath drive-letter mapping (C: drive_c, Z: root, others via dosdevices), PrefixOfGameDir; plan.RuntimeModeWine (runtime under MelonLoader/Dependencies/dotnet, version.dll override in the prefix); proton.FindWineBinary (MEGABONK_WINE, PATH, Wine*.app under ~/Applications or /Applications, else the user.reg fallback); cli darwin mode (discovery, --prefix, --game-dir derives the prefix, macOS not-found message, --package defaults to the executable's folder); task package:macos and build_player_package.py --platform macos (mode 0755 in the zip); both manifest loaders accept macos; scripts/notarize_macos.py. Docs: docs/player-installer.md (macOS package section) and docs/modding-setup.md (players on macOS).

Also fixed along the way: plan.resolve compared a not-yet-written path with its symlink-resolved directory (/var vs /private/var), which failed every plan test on macOS and would break an install through a symlinked path; the package tasks built nothing the builder read (they read bin/Release, task mod:build builds Debug), so they now run dotnet build -c Release; the cli tests pin GOOS=linux; the parity harness skips on macOS because the Go binary takes its Wine path there (so those 29 tests only run on Linux).

Verification on mbp (Apple silicon, plain Wine 11, a copy of the working prefix with MelonLoader, the mod, UserData, UserLibs, version.dll and the override stripped; the scratch copy has been deleted): the Developer ID signed package installed 7 steps with --prefix (exit 0); a re-run and --check reported nothing to do; --uninstall returned the game directory to its vanilla contents and removed the override; a launch without --melonloader.agfoffline logged the vendored HostFXR path under MelonLoader/Dependencies/dotnet, Assembly Generation Successful, '1 Mod loaded.' and 'MegabonkLevels mod initialized.'. A launch through scripts/launch_game.py gave a black screen because that launcher passes --melonloader.agfoffline, which refuses the Unity dependency download ('UnityDependencies_2023.2.22.zip does not Exist!'); documented. A GUI run from Terminal in the desktop session (no --no-gui) opened the window, waited for its Install confirmation and finished with exit 0; the person at the screen confirmed it (AC #7). Default discovery of the plain-Wine prefix was checked with --dry-run on mbp and of the CrossOver bottle on mini. Pack bundles on macOS are covered by the shared plan tests, not a Mac run.

Notarization: package:macos reads APPLE_SIGNING_IDENTITY and submits the zip through scripts/notarize_macos.py using NOTARY_PROFILE or APPLE_API_KEY, APPLE_API_ISSUER and APPLE_API_KEY_B64 (the variables the mt repo uses; the key goes to a 0600 temp file removed afterwards). A real run signed the installer with the Developer ID Application identity (hardened runtime) and Apple returned Accepted. A ticket cannot be stapled to a bare binary or zip, so Gatekeeper checks online. The credentials live in the gitignored .env.

Still open: AC #2 (CrossOver's Wine not run end to end) and DoD #1 (task check fails on this Mac with 2 failures in tests/test_thps_pack_pieces.py, unrelated to the installer and failing before this work).
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
