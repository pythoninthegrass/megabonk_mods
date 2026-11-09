---
id: TASK-009
title: Run Megabonk on macOS with free Wine instead of CrossOver
status: Done
assignee: []
created_date: '2026-10-22 03:00'
updated_date: '2026-11-09 05:26'
labels: []
dependencies: []
documentation:
  - docs/development.md
  - docs/modding-setup.md
  - taskfiles/game.yml
  - scripts/run.py
  - scripts/game_paths.py
  - scripts/install_melonloader.py
priority: high
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The CrossOver trial expired, so the macOS launch path (task game:run, MelonLoader install, dev harness relaunch) no longer works. Wine 11.18 (Gcenx build) plus DXVK-macOS was verified by hand against the existing CrossOver Steam bottle: Steam logs on with -silent, Megabonk reaches Steamworks, MelonLoader loads and the mod initializes, and Steam Cloud saves load. Required runtime conditions found in that spike: the Windows user must stay "crossover" (set USER=crossover), because Wine otherwise creates a "the maintainer" profile with no saves; d3d11 and d3d10core need native DXVK DLLs in the prefix's system32; version.dll needs the native,builtin override for MelonLoader; Steam must run with -silent (its UI renders as a black window); SteamAppId and SteamGameId must be 3405340. Wine's own D3D path and the Game Porting Toolkit cask (Wine 7.7 base) do not work. CrossOver must stay available as an alternate macOS runtime, selected by MEGABONK_MACOS_RUNTIME (wine default, crossover), with its tasks moved to taskfiles/crossover.yml. Plain Wine is the new default. Both runtimes share the bottle. Also fix the duplicate run: key in taskfiles/game.yml.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MEGABONK_MACOS_RUNTIME (wine or crossover, default wine) and MEGABONK_WINE (wine binary path) are read through the same precedence as other keys (process env, then .env, then default) in both scripts/game_paths.py and scripts/run.py, with unit tests
- [x] #2 The wine launch command builder sets WINEPREFIX from the bottle, USER and LOGNAME to crossover, WINEMSYNC, SteamAppId and SteamGameId 3405340, and the version, d3d11 and d3d10core DLL overrides, with unit tests that assert the exact argv and env
- [x] #3 The game and Steam client start detached from the task runner and survive the terminal closing; Steam starts with -silent
- [x] #4 scripts/install_melonloader.py applies the version.dll native,builtin override through plain wine when the runtime is wine, and through CrossOver's wine when the runtime is crossover; the existing CrossOver behavior is unchanged and tested
- [x] #5 scripts/run.py relaunch uses the crossover task when the runtime is crossover and the wine task otherwise, with a unit test for the choice
- [x] #6 taskfiles/crossover.yml holds the CrossOver launch and MelonLoader install tasks, is included in taskfile.yml, and is darwin-only; taskfiles/game.yml has a single run task and a steam task for the wine runtime
- [x] #7 docs/development.md documents the wine setup (Wine build, DXVK DLL install with prefix backup, USER=crossover and why, -silent and why, unverified DXVK checksum) and keeps the CrossOver section pointing at the crossover tasks; docs/modding-setup.md and .env.example describe the new keys
- [x] #8 task test and task lint pass
- [x] #9 On macOS, task game:steam then uv run scripts/run.py relaunch reaches EditorMode: entered in MelonLoader/Latest.log, and uv run scripts/run.py quit ends the game
- [x] #10 A darwin-only taskfiles/wine.yml (included in taskfile.yml) installs the pinned Wine 11.18 build and DXVK-macOS DLLs: it downloads each archive, verifies the sha256 against the pin, strips quarantine and ad-hoc signs the Wine app, backs up the prefix's existing d3d11.dll and d3d10core.dll, and installs the x64 DXVK DLLs into the prefix's system32
- [x] #11 The install fails closed: a download whose sha256 differs from the pin stops the task before anything is extracted or copied, and the task errors when a required pin is unset; the failure path is exercised by running the task against a deliberately wrong pin and recording the result
- [x] #12 Pins (Wine URL, version and sha256; DXVK URL, version and sha256) are defined once in taskfiles/wine.yml vars and can be overridden through the environment or .env; no var or dir uses {{.HOME}} (use $HOME), per the Taskfile SmartJoin bug
- [x] #13 The install tasks are idempotent through status checks: a second run with the pinned versions already installed reports up to date and makes no changes, and never overwrites the DXVK originals backed up on the first run
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Phase 1 (runtime spike) is done by hand and verified; no repo files have changed yet. Everything below is Phase 2, in TDD order (failing test first, per the user's global rules).

1. Runtime keys. Add MEGABONK_MACOS_RUNTIME (wine | crossover, default wine) and MEGABONK_WINE (default ~/Applications/wine11/Wine Devel.app/Contents/Resources/wine/bin/wine) to scripts/game_paths.py and scripts/run.py. Both files duplicate the game-dir resolution (DEFAULT_BOTTLE_MACOS, lookup precedence); keep them in step and do not add a third copy. WINEPREFIX is the parent of the bottle's drive_c.
2. Launch builder. Add a pure function that returns argv and env for the game and for the Steam client, with unit tests asserting exact values (see Implementation Notes for the verified values). Put it in scripts/run.py as a launch subcommand unless that makes the file unwieldy, then use a small scripts/launch_game.py. Keep Popen(start_new_session=True) for detaching; a trailing & is killed by Task's shell.
3. scripts/install_melonloader.py. Keep _find_crossover_wine and _apply_crossover_dll_override. Add a plain-wine override path (reg add HKCU\Software\Wine\DllOverrides /v version /d native,builtin /f under WINEPREFIX with MEGABONK_WINE) and choose by runtime on Darwin. The override is already set in the existing bottle, so this must stay idempotent.
4. Taskfiles. Create taskfiles/crossover.yml (darwin only) with the current inline cxstart launch moved verbatim as crossover:run and crossover:melonloader:install; include it in taskfile.yml. In taskfiles/game.yml delete the duplicate first run: key (it currently runs install_melonloader.py by mistake), point the darwin run command at the wine launcher, and add game:steam (darwin). Make scripts/run.py relaunch (line ~197, runs task game:run) call task crossover:run when the runtime is crossover; add a test.
5. Docs. docs/development.md: add Launching under Wine (macOS) covering the setup in Implementation Notes; keep Launching under CrossOver and point it at the crossover:* tasks. Update docs/modding-setup.md, .env.example, and the scripts/game_paths.py docstring. Put design rationale in docs, not in code comments (project rule: no multi-line comments).
6. Verify: task check, then on the Mac: task game:steam, wait for Steam logon, uv run scripts/run.py relaunch, expect EditorMode: entered in the MelonLoader Latest.log, then uv run scripts/run.py cycle levels/example-forest.mblevel.json <png>, then uv run scripts/run.py quit.

Install tooling (replaces any Python install script): implement the pinned Wine and DXVK install as taskfiles/wine.yml, not a uv script. Use vars for the pins (one place), requires for unset pins, platforms: [darwin], and status: checks for idempotency (installed wine --version equals the pinned version; the prefix's d3d11.dll and d3d10core.dll hash equals the DXVK DLL; dxvk-orig backup already exists). Do the checksum with shasum -a 256 -c in a cmd that exits non-zero on mismatch so Task stops before extraction. Use $HOME, never {{.HOME}}, in vars and dir. Task-level env overrides dotenv, so document that pins can be overridden by exporting them or by a .env if the root Taskfile declares dotenv. Context7 reference: /websites/taskfile_dev (status, sources/generates, requires, dotenv, includes).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
STATE AT HANDOFF (2026-10-21): the manual spike passed. A 20-minute run was played to completion under Wine 11.18 with the mod loaded and saves intact. Nothing in the repo is changed. Not yet tested under Wine 11: scripts/run.py to_game_path (Z: mapping), the harness load/screenshot/quit commands, and relaunch. The process regex GAME_COMMAND matched the game's ps line (C:\Program Files (x86)\Steam\steamapps\common\Megabonk\Megabonk.exe), so quit_game should work, but confirm.

WORKING SETUP (installed on this Mac, host arm64, macOS 26.5.1, Rosetta on)
- Wine: Gcenx wine-devel 11.18 from https://github.com/Gcenx/macOS_Wine_builds release 11.18, asset wine-devel-11.18-osx64.tar.xz (sha256 aa0ea4c82e636ae7bca2076387cb0a5affa26509ad13f119ecd0d62bd7ba6f82 matches the release digest). Extracted to ~/Applications/wine11/Wine Devel.app, then xattr -drs com.apple.quarantine and codesign --force --deep -s - on the app. Binary: ~/Applications/wine11/Wine Devel.app/Contents/Resources/wine/bin/wine (wineserver is beside it). Do NOT use the wine64 on PATH: /opt/homebrew/bin/wine64 is the GPTK cask's Wine 7.7 base, which crashes Steam with an unhandled page fault.
- Graphics: DXVK-macOS async v1.10.3-20230507-repack from https://github.com/Gcenx/DXVK-macOS (asset dxvk-macOS-async-v1.10.3-20230507-repack.tar.gz, local sha256 acd1520ad105d8ef124a09c8e11a259a5dc8bdc565ad18e0e52693f9807b2477; the release publishes NO digest for this asset, so it is unverified and the docs must say so). Only x64/d3d11.dll and x64/d3d10core.dll are copied into drive_c/windows/system32. Originals saved in drive_c/windows/dxvk-orig/. MoltenVK ships inside the Wine build. Without DXVK, Wine's wined3d reports no supported D3D feature level and Unity shows Failed to initialize player / InitializeEngineGraphics failed.
- Prefix: the existing CrossOver bottle, in place: ~/Library/Application Support/CrossOver/Bottles/Steam (drive_c, system.reg, user.reg). Backups: Bottles/Steam.regbak/ (system.reg, user.reg, userdef.reg, cxbottle.conf) and Bottles/Steam.savebak/ (Ved save tree and remotecache.vdf). The version=native,builtin override is already in the registry from the CrossOver setup.
- Leftover, unused: brew cask gcenx/wine/game-porting-toolkit 3.0-3 is installed at /Applications/Game Porting Toolkit.app with its lib/external and lib/wine overlaid by the GPTK 4.0b3 redist (originals kept as lib/external.old). It can be uninstalled; the wine runtime does not use it. A Game Porting Toolkit dmg is still mounted at /Volumes/Game Porting Toolkit. Homebrew core wine-stable is disabled (Gatekeeper, 2026-09-01).

VERIFIED GAME LAUNCH (run from the game directory drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk)
  env: WINEPREFIX=<bottle> WINEMSYNC=1 USER=crossover LOGNAME=crossover SteamAppId=3405340 SteamGameId=3405340 WINEDLLOVERRIDES='version=n,b;d3d11,d3d10core=n,b' WINEDEBUG=-all (use err+all and DXVK_LOG_LEVEL=info DXVK_LOG_PATH=<dir> when debugging)
  argv: <wine> C:\Program Files (x86)\Steam\steamapps\common\Megabonk\Megabonk.exe
VERIFIED STEAM LAUNCH (same WINEPREFIX, WINEMSYNC, USER, LOGNAME)
  argv: <wine> C:\Program Files (x86)\Steam\steam.exe -silent -no-cef-sandbox -cef-disable-gpu -cef-disable-gpu-compositing
  Steam must be running and logged on before the game starts, or Steamworks fails to initialize. Shut it down with <wine> C:\Program Files (x86)\Steam\steam.exe -shutdown, and never while the game is running (risks the Steamworks session and cloud sync). Quit the game with <wine> taskkill /im Megabonk.exe or the in-game menu.

GOTCHAS FOUND
- USER=crossover is mandatory. Wine takes the Windows profile name from the macOS user. Without it Wine creates C:\users\the maintainer with no saves and Rewired/SaveManager start from empty. CrossOver ran as crossover, so saves live in drive_c/users/crossover/AppData/LocalLow/Ved/Megabonk/Saves/CloudDir/<steamid>/. An empty profile can also make Steam Cloud see local files as missing; remotecache.vdf was verified untouched, but keep USER=crossover set on every wine call, including reg and taskkill.
- Steam UI is black under Wine here (CEF fails to draw). -silent keeps the main window closed; the client still works. The only visible window seen was Steam's New Controller Firmware Available popup, caused by a connected DualSense. With the controller unplugged and off, no Wine window is on screen. -no-browser is ignored by this Steam build (steamwebhelper still starts). The user cannot re-authenticate through the Steam UI in this setup; use the macOS Steam client or CrossOver if a login prompt is needed.
- Steam first start after a client update crashed once with a page fault under Wine 7.7 only; Wine 11.18 ran the updated client without a crash.
- List Wine windows without Accessibility permission: osascript -l JavaScript with CGWindowListCopyWindowInfo (kCGWindowListOptionOnScreenOnly) filtered by owner name wine.
- When waiting for Steam logon, do not match an old line in Steam/logs/connection_log.txt; count RecvMsgClientLogOnResponse ... 'OK' lines before launch and wait for the count to rise. Steam logon takes about 30 seconds.
- Shell caution from the user's rules: use pkill -x for process names, never pkill -f with a pattern that appears in the calling command line. A foreground sleep of 30+ seconds is blocked by the harness; poll with a loop of short checks instead.
- Another CrossOver bottle (dopewars) may be running at the same time; its winewrapper processes are unrelated. wineserver is per prefix, so wineserver -k with WINEPREFIX set only affects the Steam bottle.

OPEN QUESTIONS FOR the maintainer
- Whether to pin the Wine build and DXVK version and checksum in a script (like install_melonloader.py does for MelonLoader) or only document the manual steps. The task currently asks for documentation only.
- Whether to uninstall the unused GPTK cask.

DECISIONS (the maintainer, 2026-10-21): pin the Wine build and DXVK version with checksums in an install script, modeled on scripts/install_melonloader.py (acceptance criteria 10 to 12 added). The unused Game Porting Toolkit cask was uninstalled with brew uninstall --cask game-porting-toolkit: /Applications/Game Porting Toolkit.app and the /opt/homebrew/bin wine64, wine64-preloader and wineserver links are gone, so the wine64 on PATH gotcha above no longer applies. No --zap was used. The GPTK dmg may still be mounted at /Volumes/Game Porting Toolkit and can be ejected. The 'open questions' above are answered.

DECISION (the maintainer, 2026-10-21): the pinned install is a Taskfile (taskfiles/wine.yml), not a Python script. This supersedes the earlier note that modeled it on scripts/install_melonloader.py; acceptance criteria 10 to 13 were rewritten to match. Caveat for the implementer: the root taskfile.yml has no dotenv key, so .env pin overrides need dotenv: ['.env'] added there; that would also export every .env key (including GLINET_PASSWORD) to all task commands, so prefer overriding through the environment, or scope dotenv to the wine tasks.

2026-10-21 implementation: scripts/launch_game.py (builders, detached spawn), runtime keys in game_paths.py and run.py, wine/crossover override split in install_melonloader.py, taskfiles/wine.yml, crossover.yml, game.yml cleanup, docs. task check passes. Verified on the Mac: task wine:dxvk with a wrong pin (FAILED, exit 201, nothing copied), empty pin (refused), wine:app with a wrong pin (FAILED, installed Wine untouched), second wine:install up to date, dxvk-orig unchanged. run.py relaunch reached 'EditorMode: entered' and run.py quit ended the game.

AC12 not fully met: pins are defined once in wine.yml vars and overridable through the process environment, but not through .env. Task rejects dotenv in an included Taskfile, and a root dotenv would export every .env key (GLINET_PASSWORD) to all tasks. Documented in docs/development.md. Needs a decision from the maintainer: accept env-only, or add root dotenv.

Not committed yet: DoD #4 pending.

AC12 resolved: root taskfile.yml now has dotenv: ['.env'] (propagates to included tasks). wine.yml pins use '{{.X | default ...}}' so both the process environment and .env override them; verified with a wrong DXVK_SHA256 in each (FAILED, nothing installed). An unset or empty override falls back to the pin, so the earlier unset-pin guards were removed. Side effect: every .env key is now exported to all task commands.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
