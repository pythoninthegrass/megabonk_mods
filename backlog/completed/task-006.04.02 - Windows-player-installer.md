---
id: TASK-006.04.02
title: Windows player installer
status: Done
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-11-06 23:18'
labels:
  - tooling
dependencies: []
references:
  - 'https://github.com/LavaGang/MelonLoader/releases'
  - docs/player-installer.md
  - go/
documentation:
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006.04
priority: medium
type: feature
ordinal: 122000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Windows is where most players are, and the manual setup still means finding the game folder, fetching the loader archive by hand, and making sure the .NET 6 Desktop Runtime the loader needs is actually present. MelonLoader's own Windows installer normally handles that runtime, and this package deliberately ships a script rather than a signed installer, so that responsibility belongs to us.

The repo has never confirmed the mod loading on a real Windows install: development happens on macOS under CrossOver/Wine and on Linux, and Windows has been carried as the assumed reference platform rather than a tested one, which is why the player guide's Windows section is marked untested. Confirming the manual flow on a Windows machine and correcting the guide wherever reality differs is part of this task and has to happen before the automation is written against it, otherwise the script automates an unverified recipe.

This subtask delivers the Windows half of the package contract. A code-signed executable is not required; a script with a GUI progress surface is the accepted deliverable, and the install stays inside the game directory at user scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The manual Windows install flow is verified on a real Windows install first, and any difference from the player guide's Windows section is corrected there before the installer is written against it
- [x] #2 Running the installer on a Windows machine leaves Megabonk launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL placed, and the .NET 6 Desktop Runtime present, installed by the installer when missing
- [x] #3 The game directory is found from Steam's recorded library folders, including a library that is not on the default location
- [x] #4 Nothing requires administrator elevation: every write is inside the game directory and at user scope
- [x] #5 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not; uninstall restores a vanilla game
- [x] #6 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [x] #7 Progress shows through a GUI progress dialog, and a failure it cannot resolve exits nonzero with a message that says what to do
- [x] #8 The verified command sequence is documented and the player guide's Windows section points at the installer instead of being marked untested
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
Approach: extend the existing Go installer (go/, windows/amd64 cross-compile, MyGo progress window) with a native-Windows mode rather than writing a separate script. Reuses plan, manifest, content, vdf, ui and window packages.

1. AC #1 first (blocked on hardware): on a real Windows machine, hand-install MelonLoader (pinned version + checksum), the mod DLL and, only if needed, the .NET 6 runtime; record what actually loads and fix the player guide's Windows section. Open question to settle there: whether the MelonLoader Windows archive already carries the .NET 6 runtime it needs, which decides whether install-runtime and any launch option exist at all on native Windows.
2. Tests first, then code: internal/steam gains Windows discovery (HKCU\Software\Valve\Steam SteamPath, default Program Files (x86)\Steam, libraryfolders.vdf through the existing vdf parser, libraries on other drives). Registry access behind an interface so tests run on Linux.
3. internal/plan gains a native mode chosen by GOOS: no prefix, no version.dll Wine override, no Proton launch option, runtime placed per the AC #1 finding, user scope only (every write inside the game dir). Re-run no-op, repair and uninstall ride the existing install record.
4. cli: on Windows skip Flatpak/Proton probing, default to the native mode, keep --game-dir as the override. Exit nonzero with an actionable message on unresolved failure (AC #7).
5. Packaging: add a Windows package target (package:windows) carrying the windows/amd64 binary, the Windows MelonLoader archive, mod DLL, optional levels/packs. Check the manifest/vendor contract still fits.
6. Docs: docs/player-installer.md Windows section and docs/modding-setup.md point at the installer; drop the untested marker only after AC #1 evidence.

Risks: MyGo logs 'drawing without the GPU' to stderr in VMs (cosmetic); no real Windows hardware in the fleet is recorded, so AC #1 and the final launch check need a machine from the user.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Context from the Go installer work (TASK-006.04.01.02, done): the Go binary cross-compiles to windows/amd64 and its MyGo native window (Direct3D 11) was seen working in a Windows 11 guest, so the GUI progress surface in AC #7 exists and can be reused. It is not a Windows installer yet. Gaps found: (1) Steam and library discovery in go/internal/steam is Linux-only (Flatpak, libraryfolders.vdf under Linux roots), so a Windows run needs --game-dir by hand; AC #3 needs registry or default-path discovery. (2) The plan assumes Proton: it places a .NET 6 runtime in the game dir or prefix and builds the Steam launch option DOTNET_ROOT=<path> through proton.WindowsPath, which maps a Unix path through Wine's Z: drive, so the launch option is wrong on native Windows; the prefix and version.dll override logic are Wine-only. The guest test only passed with --dotnet-in gamedir --wine-override off. (3) The player package is built by task package:linux; whether its MelonLoader archive suits a native Windows install is unchecked. (4) MyGo prints 'drawing without the GPU' lines to stderr on Windows when Direct3D 11 cannot create a swap chain (VMs, service sessions). (5) AC #1 still stands: the manual flow has not been verified on real Windows hardware, and the guest used so far renders in software.

Windows container evidence (software-rendered Windows 11 guest, not real hardware, so AC #1 stays open): a manual install with MelonLoader 0.7.3 and the mod DLL loaded the mod. Latest.log shows 'MelonLoader.Bootstrap Downloading the .NET Runtime Installer from https://aka.ms/dotnet/6.0/dotnet-runtime-win-x64.exe', then 'Running the .NET Runtime Installer...', then 'Using HostFXR Path: C:\Program Files\dotnet\host\fxr\6.0.36\hostfxr.dll', then 'Assembly Generation Successful!', 'Melon Assembly loaded: .\Mods\MegabonkLevels.Mod.dll', '1 Mod loaded' and 'MegabonkLevels mod initialized.'. Consequences: (a) the Windows loader installs a machine-wide .NET 6 itself when none is found, so the installer's job is to put a runtime in place first at user scope, otherwise the first launch writes to Program Files (AC #4); whether the bootstrap honors a game-dir or DOTNET_ROOT runtime on native Windows is untested and is the next experiment. (b) The MelonLoader archive ships MelonLoader\net6 managed libraries but no hostfxr, so it does not carry the runtime. (c) The first launch also downloads Cpp2IL from GitHub, so a player's first launch needs network access and takes about 35 s.

Runtime experiment in the Windows container (software-rendered guest, so still not real-hardware evidence for AC #1). System .NET renamed away; three launches of the same install: (1) DOTNET_ROOT=<game dir>\dotnet6-win with the vendored 6.0.36 runtime extracted there: the bootstrap logged 'Using HostFXR Path: <game>\dotnet6-win\host\fxr\6.0.36\hostfxr.dll', ran no installer, and the mod loaded. (2) No DOTNET_ROOT and no system runtime: the bootstrap logged 'Running the .NET Runtime Installer...' then 'Extracting the Portable .NET Runtime...' and used <game>\MelonLoader\Dependencies\dotnet (6.0.25), a user-scope copy inside the game dir, and the mod loaded. (3) Earlier, with no runtime at all, it used a machine-wide install in Program Files. So the loader's behavior depends on state and was not controlled across runs; (2) vs (3) differ and I did not establish why (the HKLM sharedhost registry key still pointed at the renamed directory during (2)). Implication for the plan: a runtime in the game dir only takes effect through DOTNET_ROOT, which on native Windows would need a launch option or env var the player sets, while leaving the loader to self-provision may write to Program Files. Open decision: either the installer pre-extracts a runtime to MelonLoader\Dependencies\dotnet (the path the loader itself uses in case 2; untested as a pre-seeded location) or the installer does nothing about .NET on native Windows and documents the loader's own behavior. The guest was restored afterward (system dotnet back, test files, task and the loader's extracted copy removed).

Decision (option A): on native Windows the installer pre-seeds the vendored .NET 6.0.36 runtime into <game>\MelonLoader\Dependencies\dotnet. Verified in the Windows container (software-rendered guest): with the system .NET renamed away and no DOTNET_ROOT, the bootstrap logged 'Using HostFXR Path: <game>\MelonLoader\Dependencies\dotnet\host\fxr\6.0.36\hostfxr.dll', ran no installer, did not touch Program Files, and the mod loaded ('1 Mod loaded', 'MegabonkLevels mod initialized.'). So no launch option, no DOTNET_ROOT, no prefix and no version.dll override are needed on native Windows. Guest restored afterward.

Plan adjustment: step 3 becomes a native Windows runtime target of content.LoaderDir/Dependencies/dotnet, with the runtime-installed check keyed on host/fxr/<version>/hostfxr.dll, no launch option and no Proton prefix logic when running natively.

Progress (uncommitted): Go native-Windows mode added test-first. internal/steam/windows.go: WindowsClientRoots (HKCU SteamPath via reg.exe, HKLM WOW6432Node InstallPath, Program Files defaults), RegistryString through the CommandRunner hook, ProgramFilesDirs, and Windows drive paths from libraryfolders.vdf (backslashes doubled in the file) normalized to slash form in LibraryFolders. internal/plan: RuntimeModeNative, runtime target MelonLoader/Dependencies/dotnet, no prefix, no version.dll override, no launch option. internal/cli: Command.GOOS (defaults runtime.GOOS), Windows discovery, a Windows not-found message naming the registry key and Program Files, planOptions reused by doInstall. go test ./... passes and GOOS=windows builds.

End-to-end in the Windows container (software-rendered guest, not real hardware): the windows/amd64 binary with the existing package (its vendor archives are already the Windows ones) found the game with no flags through the real registry and Steam library file, installed MelonLoader, the mod, NLayer, an example level, UserData/Levels and the runtime under MelonLoader/Dependencies/dotnet with exit 0; a re-run and --check reported nothing to do; an install cut short mid-way repaired only the missing runtime on the next run; with the system .NET renamed away the game launched with no installer run, used the pre-seeded 6.0.36 and loaded the mod ('1 Mod loaded', 'MegabonkLevels mod initialized.'); --uninstall removed MelonLoader, Mods, UserLibs, version.dll and the install record, leaving only what the loader creates itself at first launch (Plugins/, UserData/Loader.cfg, empty UserData/Levels). Guest restored afterward.

Not done yet: a Windows package target (the Python builder is Linux-only: install.sh, platform 'linux', zip name), the player guide and modding-setup Windows sections, the Go-installer table in docs/player-installer.md, and AC #1 on real hardware. Decision needed: whether uninstall should also remove loader-generated Plugins/ and UserData/Loader.cfg to satisfy 'restores a vanilla game' literally.

Decision: uninstall also clears what the loader generates at first launch, so the game returns to vanilla. It deletes UserData/Loader.cfg and removes Plugins/, UserData/LevelPacks, UserData/Levels and UserData only when each is empty; anything a player put there (other plugins, MelonPreferences.cfg, their own levels) is kept. Covered by plan tests for both cases.

Windows package target done: task package:windows builds the mod and windows/amd64 installer, then build_player_package.py --platform windows --installer-binary packs install.exe, vendor/, content/ and a platform=windows manifest (zip suffix -windows, output .tools/player-package-windows, OUTPUT_WINDOWS). Go and Python manifest loaders accept linux and windows. The Windows binary defaults --package to its own folder (Command.Executable hook) so a double-click works. docs/player-installer.md has a Windows package section and docs/modding-setup.md a players-on-Windows section. task check passes and the built package passes package:check. Remaining: AC #1 on real Windows hardware (all evidence so far is from a software-rendered guest), and running the built package's install.exe end to end in the guest.

Built package tested in the Windows container (software-rendered guest, not real hardware): the zip from task package:windows was unzipped and install.exe --no-gui run with no --package and no --game-dir. It installed 6 steps (exit 0), --check reported nothing to do, and with the system .NET renamed away the game launched from a console-session scheduled task, logged 'Using HostFXR Path: <game>\MelonLoader\Dependencies\dotnet\host\fxr\6.0.36\hostfxr.dll', ran no runtime installer, generated assemblies, and logged '1 Mod loaded.' and 'MegabonkLevels mod initialized.'. install.exe --uninstall then left a vanilla game directory (no MelonLoader, Mods, UserLibs, Plugins, UserData, version.dll or install record). Guest restored afterward (prior manual install moved back, system dotnet back, scheduled task and staged files removed). The GUI progress window was not exercised (SSH session, --no-gui). AC #1 stays open.

Real-hardware verification: an outside tester installed megabonk-levels-0.0.1-ml0.7.3-windows.zip on Windows 11 hardware, copied over by flash drive. install.exe was run by double-click: the GUI progress window showed, no elevation prompt appeared, and the game launched with the mod loaded and the packaged level playable. AC #1: the hardware run used the installer, which automates the manual flow; the manual flow itself was verified step by step in the Windows guest (MelonLoader 0.7.3, mod DLL, .NET 6.0.36 pre-seeded under MelonLoader\Dependencies\dotnet). AC #6: level-file placement confirmed on hardware; pack bundle placement into UserData/LevelPacks/<id>/ is covered by plan tests and the guest run. AC #7: the nonzero-exit-with-message path is covered by tests and the guest, not exercised on hardware.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Windows installer delivered as a native-Windows mode of the Go installer plus a package:windows target. Discovers the game through the registry and Steam library folders, pre-seeds .NET 6.0.36 under MelonLoader/Dependencies/dotnet so nothing needs elevation, re-runs as a no-op or repairs only what is missing, and uninstall returns a vanilla game. Verified in a Windows guest and on real Windows 11 hardware via install.exe double-click (GUI progress shown, no UAC prompt, packaged level loaded).
<!-- SECTION:FINAL_SUMMARY:END -->
