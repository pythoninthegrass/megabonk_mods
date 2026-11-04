---
id: TASK-006.04.03
title: macOS player installer
status: In Progress
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-11-04 00:14'
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
- [ ] #1 Running the installer on a Mac with Megabonk installed leaves the game launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL placed, and the game's Windows build running under the prefix
- [ ] #2 It works with both plain Wine and CrossOver's Wine, and does not require the commercial product to be installed
- [ ] #3 It applies the DLL override the loader needs and installs the .NET 6 runtime into the prefix when absent
- [ ] #4 The prefix and game directory are discovered without asking the player to install the repo's toolchain, with an explicit override for a non-default location
- [ ] #5 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not; uninstall restores a vanilla game
- [ ] #6 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [ ] #7 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless; a failure it cannot resolve exits nonzero with a message that says what to do
- [ ] #8 Verified end to end on the macOS machine, documented, and the player guide's macOS section becomes a real install route pointing at the installer rather than the contributor doc
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
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions: CrossOver licence is expired here, so plain Wine is the development and verification runtime and the preferred discovery target; CrossOver bottles stay a fallback that is unit-tested but not run end to end on this box. Packaging: no .command or .sh on macOS or Linux; the package carries a bare installer binary meant to be fetched by a curl-to-sh bootstrap (a curl download is not quarantined, so Gatekeeper does not gate it). Developer ID certificates are in the keychain, so the darwin/arm64 binary is codesigned and notarized for browser downloads. A published download URL and the bootstrap script are not part of this task unless scoped in. Windows keeps install.exe (a .ps1 bootstrap could scaffold it later).

Progress (uncommitted, all Go and Python tests green on the Mac): steam.WineClientRoots (plain Wine ~/.local/share/megabonk/wine and ~/.wine before CrossOver bottles), winePath drive-letter mapping (C: drive_c, Z: root, others via dosdevices), PrefixOfGameDir; plan.RuntimeModeWine (runtime under MelonLoader/Dependencies/dotnet plus the version.dll override in the prefix); proton.FindWineBinary (MEGABONK_WINE, PATH, Wine*.app under ~/Applications or /Applications, else the user.reg fallback); cli darwin mode (discovery, --prefix, --game-dir derives the prefix, not-found message, default --package to the executable's folder); package:macos task and build_player_package.py --platform macos (bare megabonk-installer, mode 0755 in the zip), both manifest loaders accept macos. Also fixed plan.resolve so a path whose tail does not exist yet compares equal under a symlinked parent (/var vs /private/var made every plan test fail on macOS, so this was a real darwin bug); the cli tests now pin GOOS=linux so the Linux-shaped cases do not take the Wine path on a Mac host. Built the darwin/arm64 package and ran a --dry-run against this Mac's CrossOver bottle: discovery, plan and no writes behave as expected. Not done: real end-to-end install with plain Wine and a game launch (AC #1, #2, #8), docs, signing and notarization run. Found, not fixed: package:linux/windows/macos read mod output from bin/Release/net6.0 but task mod:build builds Debug, so on this box Release is a stale build without NLayer.dll.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
