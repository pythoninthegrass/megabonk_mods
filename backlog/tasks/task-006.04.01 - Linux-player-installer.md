---
id: TASK-006.04.01
title: Linux player installer
status: In Progress
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-10-31T04:29:00Z'
labels:
  - tooling
dependencies: []
references:
  - AGENTS.md
  - 'https://melonwiki.xyz/#/README?id=linux-instructions'
documentation:
  - docs/modding-setup.md
  - docs/development.md
  - docs/player-installer.md
modified_files:
  - scripts/player_installer/
  - scripts/build_player_package.py
  - tests/test_player_installer_vdf.py
  - tests/test_player_installer_steam.py
  - tests/test_player_installer_manifest.py
  - tests/test_player_installer_proton.py
  - tests/test_player_installer_plan.py
  - tests/test_player_installer_ui.py
  - tests/test_player_installer_cli.py
  - tests/test_build_player_package.py
  - taskfiles/package.yml
  - taskfile.yml
  - docs/player-installer.md
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006.04
priority: medium
type: feature
ordinal: 121000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Linux is where the manual setup is worst and where this repo has real machines to verify against. Two maintainer Linux machines exist: an AlmaLinux 10 host that runs Steam only as a Flatpak, whose Steam client and library were relocated outside the home directory to a path granted to the sandbox with a flatpak override, and a CachyOS host running native Steam where Megabonk is installed as the Windows build played under Proton with a gamepad. A player on either machine has to find their own Steam library among several possible layouts, choose between two game builds, and supply a .NET 6 runtime their distribution may not offer at all. This subtask delivers the Linux half of the package contract so that is one command rather than a wiki page.

The build choice is not obvious to a player and the installer has to handle it: Megabonk ships a native Linux binary, but the pinned MelonLoader fails to initialize against that build and the upstream fix is unreleased, while the Windows build under Proton works and is the path the player guide recommends. Detecting which build is installed, and steering the player instead of silently installing into a build that cannot load the mod, is core scope — the native build's LD_PRELOAD launch-option recipe in AGENTS.md is contributor tooling for a path that does not currently work.

How the .NET 6 runtime reaches the loader under Proton — a runtime directory placed inside the game folder, versus installing the runtime into the Proton prefix — and whether any DLL-override launch option is required, are settled by the verification run of the player guide on these same two machines. Implement whichever that run confirms and keep the other as a fallback.

Packs are per-platform: the windows bundle is the one that matters on the recommended Proton path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 From a wiped mod install, running the installer on both Linux test machines leaves the game launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL, and the .NET 6 runtime all in place
- [ ] #2 The Steam install and the Megabonk directory are detected in the supported layouts: native Steam, Flatpak Steam including a client and library relocated outside the default path, and a library on removable media
- [x] #3 The installer distinguishes the native Linux build from the Windows build and steers the player to the working one, stating why the native build cannot be used with the current MelonLoader
- [x] #4 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not
- [x] #5 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [ ] #6 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless, such as over ssh; a failure it cannot resolve exits nonzero with a message that says what to do
- [x] #7 Uninstall restores a vanilla game
- [ ] #8 The verified command sequence is documented and the player guide's Linux section points at the installer
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan (Linux player installer)

### Research findings that shape the approach
- Both maintainer Linux machines are reachable over SSH from the macOS dev box:
  - `mf` - AlmaLinux 10.2, Flatpak Steam only (`com.valvesoftware.Steam` 1.0.0.87), library relocated to `/media/steam` and granted with `flatpak override --filesystem=/media/steam`; a second, stale library entry points at `/mnt/games/GameLibrary/Steam` which is not mounted. Native Linux build (`Megabonk.x86_64`, buildid 21750826) with inert MelonLoader 0.7.3 + generated Il2CppAssemblies, portable .NET 6 at `/media/steam/dotnet6`, repo checkout present. Steam not running.
  - `wm2` - CachyOS, native Steam running in SteamOS/gamepadui mode, three libraries in `libraryfolders.vdf`: `/home/lance/.local/share/Steam`, `/run/media/lance/SDCARD/SteamLibrary`, `/media/sdcard/SteamLibrary`. Megabonk **Windows** build (`Megabonk.exe`, same buildid) lives on the SD-card library; its Proton prefix `compatdata/3405340` is a 168K skeleton, so the game has not effectively run under Proton there. No dotnet on PATH, no repo checkout.
- Task premise check: the repo has **no record of the mod ever loading under Proton on Linux**. MelonLoader 0.7.3 + the native build segfaults (TASK-002.01), which is why the installer must steer players to the Windows build - but "the Windows build under Proton works" is an unverified claim in the task text. AC #1 cannot be met by writing a script alone; the manual Proton flow has to be proven first, on wm2, before it is automated. This is the same "verify the recipe before automating it" rule TASK-006.04.02 states for Windows.
- No packaging or installer exists yet (TASK-006.04 parent AC #1/#2 are To Do), so the Linux installer has to define the package layout and the vendor-pin manifest it consumes; the parent's contract doc should be extracted from it rather than the other way round.
- Reusable pieces: `scripts/install_melonloader.py` pins (MelonLoader 0.7.3, per-platform asset + sha256), `taskfiles/pack.yml` pack layout (`UserData/LevelPacks/<id>/<bundle>`, `manifest.json`, optional `attachments.json`), mod build output (`MegabonkLevels.Mod.dll` + pdb + `NLayer.dll` into `Mods/` and `UserLibs/`).

### Steps
1. **Settle the Proton questions on wm2 (manual, before code).** Install MelonLoader 0.7.3 Windows build into `/media/sdcard/SteamLibrary/steamapps/common/Megabonk`, then try both .NET 6 delivery mechanisms and record which one loads the mod in `MelonLoader/Latest.log`:
   a. portable Windows .NET 6 Desktop Runtime zip inside the game folder + `DOTNET_ROOT=Z:\...` launch option (needs Steam stopped to edit localconfig.vdf);
   b. runtime installed into the Proton prefix at `drive_c/Program Files/dotnet` (no launch option, no Steam config edit).
   Also determine whether a `version.dll -> native,builtin` DllOverrides entry is required under Proton, as it is under CrossOver/Wine on macOS. Keep the loser as the documented fallback.
2. **Write the installer as stdlib-only Python 3** (no uv, no repo checkout, no third-party deps) plus a one-line `install.sh` wrapper: `player/linux/installer.py` with importable pure logic (VDF parsing, Steam/library discovery, build detection, plan/diff computation, manifest verification) and a thin CLI; `player/linux/gui.py` for progress via zenity/yad when a desktop session exists, plain text otherwise.
3. **Tests first for the testable logic** (`tests/test_player_installer_linux.py`): libraryfolders.vdf parsing including missing/stale paths, Flatpak layout + relocated library, native-vs-Windows build detection, manifest/checksum verification, idempotency plan (no-op vs repair set), pack/level placement, uninstall set. Run with `task scripts:test`.
4. **Vendor + package step** (`taskfiles/package.yml`, `task package:player-linux`): assemble the package dir from pinned downloads (MelonLoader Windows + Linux archives, .NET 6 runtime(s)), the built mod DLLs, and a `manifest.json` recording game buildid, MelonLoader version, file sha256s. Installer accepts either a vendored package or a download-with-checksum run.
5. **Verify AC #1-#7 on both machines from a wiped mod install**: wm2 (Proton path, end to end, mod loads), mf (detection of the Flatpak/relocated layout, native-build refusal message, level + pack install, idempotent re-run, uninstall). Confirm the mod actually loads on mf too if the Windows build can be installed there.
6. **Docs**: Linux section in `docs/modding-setup.md` (contributor), a verified command sequence for the player flow, and the player guide's Linux pointer. Record the Proton findings (.NET delivery mechanism, DLL override) wherever the guide will consume them.
7. Commit as a conventional commit with no attribution; finalize per the finalization guide.

### Risks
- Proton path may not work at all (MelonLoader under Proton has never been proven here). If it fails, this task cannot deliver AC #1 and the outcome becomes "documented blocker + installer with the native-build refusal path only" - needs a user decision.
- Verification touches live machines: writing into a real game install on an SD card, creating Proton prefixes, stopping Steam, editing `localconfig.vdf`, and launching a game on a gamepadui box's display. Needs user consent per machine.
- `mf` has no Windows build; AC #1 "both machines" may need a multi-GB Steam download there.
- Package/contract pieces overlap the unstarted parent TASK-006.04 and the player guide TASK-006.02.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Scope decisions from the user before implementation: (1) Offline only for now - no changes to mf or wm2 beyond the read-only survey already done; the installer, its tests, the package task and the docs are built on the macOS dev box, and all on-machine verification (including the manual Proton proof on wm2) waits for a window the user schedules. (2) The shared pieces the parent TASK-006.04 owns - the package build command, the package/manifest layout, and the written installer contract - are built here, extracted from the working Linux installer, so Windows and macOS inherit a proven shape; what is still missing from the parent is recorded rather than assumed done. (3) If a live run later shows the mod does not load under Proton, stop and report with logs and repro rather than working around it.

Offline verification strategy: build the package locally with pinned downloads (real URLs + checksums exercised), then run the installer against synthetic game trees assembled from the two machines' real libraryfolders.vdf/localconfig layouts captured read-only, plus a tree unpacked from the real MelonLoader archive. The only claim that cannot be evidenced offline is the game launching with the mod loaded under Proton.

What was built (offline pass). Shipped: scripts/player_installer/ (11 stdlib-only modules: cli, plan, manifest, content, gamebuild, proton, steam, vdf, ui) run as python3 -m player_installer, plus a generated install.sh wrapper; scripts/build_player_package.py and taskfiles/package.yml (task package:linux, task package:check) which produce .tools/player-package/ plus a deterministic zip; docs/player-installer.md (the shared contract + the Linux implementation), a Linux section in docs/modding-setup.md and a pointer from docs/development.md.

Contract settled here for the parent to inherit: manifest schema megabonk-player-package/1 with vendors[] (name is the filename under vendor/, kind is the lookup key - melonloader and dotnet are required) and files[] (path/sha256/dest, dest relative to the game dir); install record megabonk-levels-install/1 in the game dir drives --check and --uninstall; exit codes 0/1/2/3/4/10. Bundled levels and packs are ordinary files[] entries (dest UserData/Levels/<name> and UserData/LevelPacks/<id>/...), so no schema special-casing and uninstall covers them for free. Levels go to UserData/Levels because that is what LiveEditPatch.LevelsDirectoryPath lists - an earlier draft used UserData/CustomLevels, which the game never reads.

Corrections found while verifying: levels were being written to a directory the mod does not read; the mod build's generic dll sweep double-placed NLayer.dll into Mods/ (UserLibs is the right one); uninstall listed the install record twice; the install record's dll_override.via read a key nothing ever wrote, so it printed None - it now carries the method actually used (wine | registry | already set) and describe_record says "not set" instead of "None via". Nothing is bundled into a package unless --level/--pack names it, so a dev regression map cannot reach a player by accident.

Evidence gathered offline (macOS, synthetic Windows-layout game dirs + a synthetic steamapps/compatdata/3405340/pfx prefix, real vendored archives with their pinned sha256s): package builds and verify_package is clean; full install -> --check (no drift) -> --uninstall in both gamedir and prefix modes, leaving the game's own files and an untouched UserData; version.dll written to user.reg as native,builtin and cleared on uninstall; .NET extracted to drive_c/Program Files/dotnet in prefix mode and to dotnet6-win beside the exe in gamedir mode with the DOTNET_ROOT=Z:\... %command% line printed; rerun says "already installed" and after deleting two files --check exits 10 naming exactly those two and the repair run takes exactly 2 steps; a native-Linux game dir is refused with exit 4. 822 python tests pass (149 in the 8 player-installer/build files) and task lint is clean.

Still pending the machine window the user schedules: AC #1 (mod loads under Proton on wm2 from a wiped install) and the AC #2/#6 live halves (real Flatpak/relocated/removable-media layouts on mf, the zenity/yad dialog on a real desktop). The task premise that the Windows build under Proton works has never been proven in this repo, so per scope decision (3) the first live run is a proof, and if it shows the mod not loading the outcome is a report with logs, not a workaround. AC #8 needs the player guide (TASK-006.02), which does not exist yet. Missing from the parent TASK-006.04 still: any Windows or macOS package build reusing this contract, and a published download URL for the package.
<!-- SECTION:NOTES:END -->
