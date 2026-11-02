---
id: TASK-006.04.01
title: Linux player installer
status: In Progress
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-11-02T03:08:00Z'
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
- [x] #6 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless, such as over ssh; a failure it cannot resolve exits nonzero with a message that says what to do
- [x] #7 Uninstall restores a vanilla game
- [ ] #8 The verified command sequence is documented and the player guide's Linux section points at the installer
- [ ] #9 Headless versus desktop is chosen from an attached tty (/dev/tty) as well as the session environment, and --non-interactive or MEGABONK_NON_INTERACTIVE forces plain text; nothing is ever read from stdin, which under a piped run is the pipe itself
- [ ] #10 Every discovery failure names the candidates considered and why each was rejected (unmounted library, Flatpak root not granted, missing prefix) and prints the exact flag to retry with: --library, --game-dir, --prefix or --proton
- [ ] #11 A step skipped because of the environment (no GUI backend, no flatpak CLI, no prefix, launch option not written) prints the command that finishes it by hand and leaves the exit code unchanged
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

Python slice, landed before any Go work. (1) Lower the floor: MIN_PYTHON (3,13) to (3,11) in scripts/build_player_package.py. Measured cause, running the bundled modules directly: install, --check, prefix-mode registry override and uninstall all exit 0 on 3.11.18 and 3.12.11; 3.10.22 and 3.9.25 die on one line, `from datetime import UTC` at plan.py:14, so UTC becomes timezone.utc and nothing else changes. That makes the AlmaLinux host's system python3 3.12.15 usable with no installs, where the 3.13 floor refused it. (2) --python PATH plus MEGABONK_PYTHON, handled inside install.sh before the version gate and stripped from the arguments handed to the module: a PATH python too old to parse the module cannot reach an argparse flag, so the choice has to live in the wrapper. (3) kdialog as a third dialog backend in ui.py: the host has neither zenity nor yad but ships kdialog 25.12.3 with KDE, so AC #6 needs no package install; kdialog's --progressbar answers over D-Bus (qdbus-qt6) instead of stdin, so GuiProgress needs a per-flavour driver and a text fallback when D-Bus is absent. (4) Guards: every bundled module parsed with ast feature_version (3,11) so newer syntax is caught on any machine, and the built install.sh run under a mise 3.11 where one is installed. Docs re-stated honestly in the same pass, including that the 3.12 refusal recorded earlier belongs to the 3.13 floor.

Sequencing after this slice: TASK-006.04.01.01 ports the installer to a single static Go CLI binary (no cgo, CGO_ENABLED=0; bitfield/script where pipeline sugar helps, stdlib elsewhere), keeping the package/manifest contract and exit codes, with the Python installer as reference until the Go binary reproduces the live checks. TASK-006.04.01.02 adds a MyGo native-UI progress window on that binary - native UI, not the webview mode, because the webview path dlopens WebKitGTK 4.1 on Linux while native UI needs only GTK 3.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Scope decisions from the user before implementation: (1) Offline only for now - no changes to mf or wm2 beyond the read-only survey already done; the installer, its tests, the package task and the docs are built on the macOS dev box, and all on-machine verification (including the manual Proton proof on wm2) waits for a window the user schedules. (2) The shared pieces the parent TASK-006.04 owns - the package build command, the package/manifest layout, and the written installer contract - are built here, extracted from the working Linux installer, so Windows and macOS inherit a proven shape; what is still missing from the parent is recorded rather than assumed done. (3) If a live run later shows the mod does not load under Proton, stop and report with logs and repro rather than working around it.

Offline verification strategy: build the package locally with pinned downloads (real URLs + checksums exercised), then run the installer against synthetic game trees assembled from the two machines' real libraryfolders.vdf/localconfig layouts captured read-only, plus a tree unpacked from the real MelonLoader archive. The only claim that cannot be evidenced offline is the game launching with the mod loaded under Proton.

What was built (offline pass). Shipped: scripts/player_installer/ (11 stdlib-only modules: cli, plan, manifest, content, gamebuild, proton, steam, vdf, ui) run as python3 -m player_installer, plus a generated install.sh wrapper; scripts/build_player_package.py and taskfiles/package.yml (task package:linux, task package:check) which produce .tools/player-package/ plus a deterministic zip; docs/player-installer.md (the shared contract + the Linux implementation), a Linux section in docs/modding-setup.md and a pointer from docs/development.md.

Contract settled here for the parent to inherit: manifest schema megabonk-player-package/1 with vendors[] (name is the filename under vendor/, kind is the lookup key - melonloader and dotnet are required) and files[] (path/sha256/dest, dest relative to the game dir); install record megabonk-levels-install/1 in the game dir drives --check and --uninstall; exit codes 0/1/2/3/4/10. Bundled levels and packs are ordinary files[] entries (dest UserData/Levels/<name> and UserData/LevelPacks/<id>/...), so no schema special-casing and uninstall covers them for free. Levels go to UserData/Levels because that is what LiveEditPatch.LevelsDirectoryPath lists - an earlier draft used UserData/CustomLevels, which the game never reads.

Corrections found while verifying: levels were being written to a directory the mod does not read; the mod build's generic dll sweep double-placed NLayer.dll into Mods/ (UserLibs is the right one); uninstall listed the install record twice; the install record's dll_override.via read a key nothing ever wrote, so it printed None - it now carries the method actually used (wine | registry | already set) and describe_record says "not set" instead of "None via". Nothing is bundled into a package unless --level/--pack names it, so a dev regression map cannot reach a player by accident.

Evidence gathered offline (macOS, synthetic Windows-layout game dirs + a synthetic steamapps/compatdata/3405340/pfx prefix, real vendored archives with their pinned sha256s): package builds and verify_package is clean; full install -> --check (no drift) -> --uninstall in both gamedir and prefix modes, leaving the game's own files and an untouched UserData; version.dll written to user.reg as native,builtin and cleared on uninstall; .NET extracted to drive_c/Program Files/dotnet in prefix mode and to dotnet6-win beside the exe in gamedir mode with the DOTNET_ROOT=Z:\... %command% line printed; rerun says "already installed" and after deleting two files --check exits 10 naming exactly those two and the repair run takes exactly 2 steps; a native-Linux game dir is refused with exit 4. 822 python tests pass (149 in the 8 player-installer/build files) and task lint is clean.

Still pending the machine window the user schedules: AC #1 (mod loads under Proton on wm2 from a wiped install) and the AC #6 live half (the zenity/yad dialog on a real desktop), plus wm2's removable-media SD-card libraries. The task premise that the Windows build under Proton works has never been proven in this repo, so per scope decision (3) the first live run is a proof, and if it shows the mod not loading the outcome is a report with logs, not a workaround. AC #8 needs the player guide (TASK-006.02), which does not exist yet. Missing from the parent TASK-006.04 still: any Windows or macOS package build reusing this contract, and a published download URL for the package.

Live pass 1 on mf (AlmaLinux 10.2, Flatpak Steam 1.0.0.87 with its whole root relocated to /media/steam), the discovery/verification half of the scheduled window; the machine's game dir and Steam config were not modified. Two bugs the offline pass could not see: (a) install.sh could never have worked for any player - `python3 -m player_installer` resolves modules from the working directory, not the script's own, and the package keeps its modules under installer/, so every invocation died with "No module named player_installer" wherever it was run; the wrapper had only ever been exercised with PYTHONPATH exported by hand. It sets PYTHONPATH itself now, and a test runs the built install.sh from outside the package (5cef532). (b) steam.client_roots found no client at all here, so the sandbox-grant line never printed and flatpak_granted_paths was never consulted - it was gated on already having a Flatpak client, and none of the fixed home-relative locations holds a Steam root when config/, userdata/ and steamapps/ have all been moved to a data disk. Grants are now client candidates as well as library roots and are read on every run; the library is found through the real libraryfolders.vdf (source=client, granted=True) rather than by luck of the media scan (e94ca4d).

Also from that machine: the Python floor bump landed on a host whose system python3 is 3.12.15, so the gate is what a player without a devbox toolchain meets - it refuses with exit 1 and the dnf hint and passes under mise's 3.13.16. mise is only on PATH from the interactive rc, so a non-interactive ssh needs the absolute ~/.local/bin/mise exec -- (bash -lc still gives 3.12), and python3.13 is an EPEL package, absent by default. Verified against the real layout: the distributed zip's sha256 survives transfer; install.sh is mode 755; the default run and --check exit 4 with the native-build refusal naming /media/steam/steamapps/common/Megabonk; --uninstall with no record exits 0 and leaves the dev-built Mods/MegabonkLevels.Mod.dll alone; prefix_for_game_dir correctly returns None while compatdata/3405340 is an empty skeleton with no pfx. 829 python tests pass and task lint is clean.

Follow-up worth its own decision, noticed on the Flatpak host: a library listed in libraryfolders.vdf but never granted to the Flatpak is still installed into, and nothing warns the player that Steam then cannot read those files - LibraryRoot.granted is metadata only, with no consumer.

Live pass 2 on mf, the Python slice (4de078c, 6df2663, d8eeb30), on the distributed zip (sha256 survived transfer). The 3.11 floor makes the host's system python3 3.12.15 usable with nothing installed: with a bare PATH=/usr/bin:/bin, --help exits 0, the default run exits 4 with the grant line and native-build steps, and --uninstall with no record exits 0. --python and MEGABONK_PYTHON are honoured - a mise 3.13.16 reaches argparse with rc 0, a dead path exits 2 naming itself - and --python survives the hand-off into the module. Progress on the host's KDE session: pick_progress chose GuiProgress /usr/bin/kdialog with qdbus-qt6, and the scripted harness read the live dialog's D-Bus properties back - value 40 at 2/5 with the label set, 100 at 5/5, close clean - while the same call with no session bus chose TextProgress. The real entry point was then exercised: ./install.sh doing a prefix-mode install with the registry override against a synthetic Windows-layout tree under /tmp (not the machine's game dir) exited 0, a pgrep -x watcher saw the real /usr/bin/kdialog --title MegabonkLevels --progressbar process, the install record landed, user.reg carried the override, and --uninstall exited 0 with the value gone. That closes AC #6: dialog proven on a real desktop, text on every ssh run, and the nonzero-exit-with-message paths (4 native build, 2 dead interpreter path, 1 below floor) all observed live. The zenity/yad branches stay test-only - the host has neither installed. Go follow-ups created as subtasks: TASK-006.04.01.01 (single static Go binary, CGO_ENABLED=0, bitfield/script only for pipeline sugar) and TASK-006.04.01.02 (MyGo native-UI progress window, blocked on the first); an earlier plan note cited them as 006.04.02/006.04.03, which are the Windows and macOS installer tasks.

Reference review of the curl|sh installer genre (setup.atuin.sh, getmic.ro), folded into ACs #9-#11. What transfers: (1) atuin decides interactivity by opening /dev/tty and testing it as a terminal, not by trusting the environment - DISPLAY/WAYLAND_DISPLAY/DBUS_SESSION_BUS_ADDRESS are stripped by sudo and systemd-run where a desktop exists and are set by ssh -X where no kdialog exists, and the gamescope gamepadui layout is unusual both ways; it also honours an explicit non-interactive flag so a piped or CI run is deterministic, and reads answers only from /dev/tty with a shell-level default so a piped stdin can never hang it. ui.py decides on env alone today. (2) getmic.ro answers every detection failure by printing the full list of accepted values plus the literal export/retry command; our discovery failures should name the candidates tried, why each was rejected, and the flag to retry with. (3) atuin treats optional integrations as non-fatal, prints the command to finish them later, and keeps going - the generalisation of the DOTNET_ROOT line we already print. What is already stronger here and should not regress toward the reference scripts: the package is fully vendored with per-file sha256 in the manifest and pinned versions, so getmic.ro's whole latest-tag machinery (API scrape, rate-limit branch, redirect fallback, post-hoc tag regex) has no analogue; zip members are resolved against the game root before extraction (plan.py) and pack ids match an allowlist regex (content.py), the two injection paths getmic.ro leaves open by interpolating a scraped value into a URL it evals; the download path already writes to a .part file, unlinks on failure and says delete-and-retry. Two build-time tightenings from the same comparison: scripts/build_player_package.py verify_sha256 skips the check when no digest is passed, so a future pin that forgets its sha256 ships unverified - make the expected digest required; and any future download must check the HTTP status before writing the body, because a 404 or captive-portal HTML page currently reads as a checksum mismatch. install.sh stays POSIX sh (#!/bin/sh, set -eu, no bashisms) so it runs under dash as well as bash - both reference scripts hold that line and it is worth keeping.
<!-- SECTION:NOTES:END -->
