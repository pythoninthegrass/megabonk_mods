---
id: TASK-006.04.01
title: Linux player installer
status: In Progress
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-11-03 07:14'
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
The Linux player package installs the Windows build of Megabonk under Proton/Wine. Native Linux game installs are out of scope: keep the existing refusal and switching instructions, but do not install or verify the native loader.

The fleet has three Linux hosts: wm2 (CachyOS, native Steam, Windows game on removable SD-card storage with the active Proton prefix in the home library), fedora (Fedora 42, GNOME Wayland, Intel Arc, gamescope + Steam gamepadui; Windows build under Proton), and mf (AlmaLinux 10.2, relocated Flatpak Steam root at /media/steam). wm2 and fedora are the Proton end-to-end verification targets; mf supplies Flatpak/relocated-library discovery and desktop-progress evidence without requiring a game-depot migration.

The wm2 verification documented in docs/gamepadui.md has proven the mod loads under Proton: Windows .NET 6 inside the active prefix, version.dll=native,builtin, Windows MelonLoader 0.7.3, and Windows pack bundles. Prefix and game libraries may differ, so measure and pass --prefix explicitly until discovery supports that layout. Fedora setup confirms Windows depot 3405342, GUI-triggered depot switching, and DX11 renderer selection; do not treat vanilla game startup as installer/mod-load evidence.

docs/player-installer.md is the current player setup and package contract. Keep verified results separate from pending clean-install and machine-specific checks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 From a wiped mod install, running the installer on wm2 (CachyOS) and fedora (Fedora 42) leaves the Windows game under Proton launchable with the mod loaded: pinned checksum-verified MelonLoader, the mod DLL, and .NET 6 runtime in place; native Linux installs are out of scope
- [x] #2 The Steam install and the Megabonk directory are detected in the supported layouts: native Steam, Flatpak Steam including a client and library relocated outside the default path, and a library on removable media
- [x] #3 The installer distinguishes the native Linux build from the Windows build and steers the player to the working one, stating why the native build cannot be used with the current MelonLoader
- [x] #4 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not
- [x] #5 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [x] #6 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless, such as over ssh; a failure it cannot resolve exits nonzero with a message that says what to do
- [x] #7 Uninstall restores a vanilla game
- [x] #8 docs/player-installer.md documents the current player setup, verified Proton command sequence, and outstanding verification limits, linking to the Linux gamepadui guide
- [x] #9 Headless versus desktop is chosen from an attached tty (/dev/tty) as well as the session environment, and --non-interactive or MEGABONK_NON_INTERACTIVE forces plain text; nothing is ever read from stdin, which under a piped run is the pipe itself
- [x] #10 Every discovery failure names the candidates considered and why each was rejected (unmounted library, Flatpak root not granted, missing prefix) and prints the exact flag to retry with: --library, --game-dir, --prefix or --proton
- [x] #11 A step skipped because of the environment (no GUI backend, no flatpak CLI, no prefix, launch option not written) prints the command that finishes it by hand and leaves the exit code unchanged
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
## Current scope and evidence

Windows Megabonk under Proton/Wine only. Native Linux installation is excluded; preserve the refusal and switching instructions. wm2 (CachyOS) and fedora (Fedora 42/GNOME/gamescope) are end-to-end targets. mf retains relocated Flatpak discovery and KDE dialog evidence without migrating its game.

Shipped: vendored package and manifest contract, stdlib Python 3.11 installer and interpreter-selecting POSIX wrapper, idempotent repair/check/uninstall, content placement, and progress backends. Historical offline/mf findings remain in implementation notes. CachyOS mod-load evidence and the actual cross-library prefix workflow are documented in docs/gamepadui.md; Fedora depot/DX11 setup is not a clean installer proof.

## Approved sequence

1. Verify wm2 removable-media Steam/game discovery read-only, and measure the active prefix instead of assuming it lives beside the game. Direct SSH and a retry through mini both timed out; leave AC2 open until reachable. No remote mutation occurred.
2. Document current player setup and verified-versus-pending state in docs/player-installer.md, linking to gamepadui.md. Completed; this is the AC8 setup document, not a dependency on a future guide.
3. Implement AC9 tests first: /dev/tty open/isatty/close with no stdin reads; GUI requires tty plus display/backend; --non-interactive and MEGABONK_NON_INTERACTIVE force text for install and uninstall. Preserve --no-gui and --json. Completed with real controlling-PTY versus no-tty subprocess tests using piped stdin, and flag/environment lifecycle tests.
4. Remaining: clean-install/fresh mod-load evidence on wm2 and fedora (AC1); live removable-media discovery (AC2); actionable discovery diagnostics (AC10); manual commands for environment-skipped steps (AC11). Do not infer completion from old logs or synthetic fixtures.
5. Go static CLI and MyGo native-UI remain the existing To Do subtasks; not started in this pass.

## Validation

Run focused installer/build tests and task check. Keep the task In Progress while remaining criteria and subtasks are open. Changes in this pass are uncommitted.

wm2 verification resumed successfully after connectivity recovered. AC2 blocker is now reproduced incorrect game identification: a generic GameAssembly.dll in another home-library game wins before the SD-card Megabonk is searched. Fix needs a regression fixture with an unrelated IL2CPP game in the first library and Megabonk in a later library, plus identity-safe selection; preserve explicit --game-dir/--prefix workaround. Not implemented in the verification-only retry.

Commit/push requested after the verification retry. Commit the completed AC8/AC9 slice and measured AC2 findings; task remains In Progress. The prior uncommitted-state note is superseded by this requested commit.
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

wm2 SSH verification attempted from the authoring machine: ssh -o ConnectTimeout=10 wm2 timed out to LAN address 192.168.8.76:22 before any remote command ran. AC2 remains open; no install, game, Steam, or remote files changed. This host is LAN-only per CLAUDE.local.md.

Current-state docs replace the stale claim that Proton mod loading has never been proven. docs/player-installer.md now includes the measured prefix-mode install/check/log sequence, Windows-only scope, Fedora setup, published-download limitation, cross-library-prefix workaround, and remaining clean-install/runtime-fallback verification limits. AC8 is documented without waiting for a separate player guide.

AC9 implemented in ui.py/cli.py after tests exposed 10 expected failures. has_tty opens /dev/tty nonblocking without acquiring a terminal, checks isatty and closes it without reading stdin; GUI selection requires display plus controlling tty. --non-interactive or MEGABONK_NON_INTERACTIVE=1/true/yes/on forces text for install and uninstall. --no-gui is retained; --json now also suppresses uninstall dialogs/progress. Real subprocess tests prove no-tty -> TextProgress and controlling PTY -> GuiProgress while stdin is still an untouched pipe. Unit tests cover missing/non-tty terminal and descriptor closure; CLI tests cover flags and environment through install/uninstall.

Validation: 89 focused UI/CLI/package-build tests passed (including Python-floor guards); task check passed with 1549 C# tests, 919 Python tests, markdownlint and ruff. Existing nullable/analyzer and pytest asyncio warnings remain. git diff --check clean. No commit created in this pass.

A second wm2 connectivity attempt using mini's Tailscale IP as a jump host also timed out during banner exchange. This does not establish which hop failed. No remote command ran; AC2 remains blocked on connectivity.

wm2 reachable on retry. Read-only verification: hostname wm2; /media/sdcard is mounted from /dev/sda1 (ext4); no Megabonk.exe process was running. Native Steam libraryfolders lists home library, stale /run/media/lance/SDCARD/SteamLibrary and mounted /media/sdcard/SteamLibrary. library_roots returns the home and mounted SD libraries with source=client, skipping the stale path. However find_install(home, []) returns /home/lance/.local/share/Steam/steamapps/common/1000xRESIST, NOT Megabonk. Its GameAssembly.dll satisfies _looks_like_game; find_game_dir scans unrelated directories in the first library before considering the second. 1000xRESIST has no Megabonk.exe. SD-library-only discovery correctly returns /media/sdcard/SteamLibrary/steamapps/common/Megabonk. Remote packaged steam.py, remote checkout and current local steam.py share SHA256 c4609f5d445e71cbb25a80b35bdd44898c28d5448fe93a7e066198ae17a4990b, so the failure applies to current source. AC2 remains open for a measured discovery bug, no longer simply connectivity.

The existing install record points at the home-library prefix /home/lance/.local/share/Steam/steamapps/compatdata/3405340/pfx (drive_c exists), whereas prefix_for_game_dir returns the SD-library prefix. Read-only --check using explicit --game-dir and the recorded home --prefix exits 10 with exactly one stale file: Mods/MegabonkLevels.Mod.dll versus the old ~/mb-player package. No repair performed. Existing Latest.log (mtime 2026-11-01) contains MelonLoader v0.7.3, 1 Mod loaded, and mod initialized; this is prior-launch evidence, not a new clean-install proof. No Steam/game launch, install/uninstall, sync or remote file edit was performed.

User requested commit and push of the current documentation, AC9 implementation/tests, task-premise update and wm2 verification findings. Preparing a conventional commit; AC2's discovery bug is documented but deliberately not fixed in this changeset. Earlier notes saying this pass was uncommitted describe the pre-commit state.

Discovery identity and prefix selection fixed (commit e7c3b0f). Game discovery had been accepting any directory holding GameAssembly.dll, so wm2's home-library 1000xRESIST was chosen over the SD-card Megabonk; that false positive is gone.

Selection now runs through steam.game_candidates in trust order - the library's own appmanifest_3405340.acf installdir, then steamapps/common/Megabonk by name, then any other Il2Cpp install - and accepts a candidate only on Megabonk's own names (Megabonk.exe, Megabonk.x86_64, Megabonk_Data/). find_game_dir takes the first accepted candidate; the not-found report names each rejected install with its reason, so an unrelated Unity/Il2Cpp title is reported rather than installed into.

Prefix selection: steam.find_prefix now searches the libraries Steam reported, not just the one beside the game. It prefers the game's own library, falls back to the only other usable prefix (the wm2 SD-card layout) and prints "Proton prefix: <path> (Steam keeps it in that library, not beside the game)"; two usable prefixes is treated as a guess - both are printed with the --prefix hint and the plan falls back to gamedir mode. Passing --prefix silences that reporting (found while writing the container evidence: the nag contradicted the flag).

Latent bug fixed on the way: _install_dir_from_manifests never matched a real manifest. It looked up appid/installdir as nested keys, but a real appmanifest is one top-level section holding both, so the manifest tier had never contributed a candidate.

Evidence: new Python and Go unit tests (identity, ordering, prefix selection, reporting), four new scenarios in tests/test_installer_parity.py (decoy library, decoy-only report, remote prefix, two prefixes with and without --prefix), and a container matrix run as a non-root user on fedora:42 and ubuntu:24.04 with --network none - four layouts x {host python reference, host go binary, fedora container, ubuntu container}, all compared on exit codes, stdout, stderr and tree digests, with the decoy directory digest-checked before and after every install to prove nothing was written into it. AC #10 and #11 are ticked on this; #1 and #2 stay open until the same layouts are run against the real wm2 card and fedora install, which needs those machines idle.

wm2 live proof closed the CachyOS half of AC #1/#2 (2026-11-03): wiped the mod install with the package's own --uninstall (10 items including the old prefix dotnet), reinstalled the 0.4.2 player package with the documented pinned flags (--game-dir on the SD-card library, --prefix home-library compatdata pfx, --dotnet-in prefix, --wine-override registry), --check reported match, and steam://rungameid launched the Windows build under Proton with the mod loaded: Latest.log showed "Assembly Generation Successful!", "1 Mod loaded." and "[MegabonkLevels] MegabonkLevels mod initialized.", stable 160 s, clean TERM shutdown. Bootstrap used the vendored .NET 6.0.36 at C:\Program Files\dotnet (prefix mode) after the MelonLoader/Dependencies/dotnet dev leftover was removed - so prefix mode is now proven on the player path. Findings: a Steam Cloud save-conflict dialog silently blocks every steam://rungameid ("You must make a selection to launch the application") - clear it first; a direct-Proton launch (proton run or pressure-vessel waitforexitandrun) exits 0 within ~10 s on this gamescope host even with everything right, so use the Steam client to launch; the client's --remote-debugging-port 8080 answers Chrome DevTools queries, which is how the blocking dialog was identified without a screenshot (gamescope hides its compositor from X grabs - x11grab of :0 returns an all-black frame).

fedora live proof closed the other half (2026-11-03), completing AC #1/#2: backed up the development install (Mods/MelonLoader/UserData, 90 MB + 265 MB saves), ran the package's --uninstall (13 items including the thps pack and prefix dotnet) to a vanilla tree, then ran install.sh with no flags at all against the real decoy layout - a single library holding Heroes of Might and Magic Olden Era (an Il2Cpp title sorting before Megabonk) - and discovery chose Megabonk through the appmanifest and the library's own prefix, --check matched. With Steam stopped, the game launched directly under Proton Experimental through the offline steamstub (SteamLinuxRuntime_4 _v2-entry-point --verb=waitforexitandrun + proton waitforexitandrun, SteamAppId/SteamGameId exported, XAUTHORITY set to the desktop's /run/user/1000/.mutter-Xwaylandauth.* cookie - the taskfile's xauth_* fallback finds nothing on this GNOME host and the game hangs pre-MelonLoader on "Authorization required" without it). Fresh Latest.log: HostFXR from C:\Program Files\dotnet\host\fxr\6.0.36 (prefix mode, dev leftover gone), Assembly Generation Successful!, 1 Mod loaded., [MegabonkLevels] MegabonkLevels mod initialized.; stable over 180 s with the mod's Perf telemetry in the log, clean TERM shutdown, --check still matching. Both player boxes are left in the verified installed state.
<!-- SECTION:NOTES:END -->
