---
id: TASK-056.01
title: >-
  Prove the end-user BepInEx install flow with r2modmac against the Wine-hosted
  game
status: In Progress
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-08T23:59:00Z'
labels:
  - bepinex
  - thunderstore
dependencies: []
references:
  - 'https://github.com/Zard-Studios/r2modmac'
  - 'https://thunderstore.io/c/megabonk/p/BepInEx/BepInExPack_IL2CPP/'
parent_task_id: TASK-056
priority: medium
type: spike
ordinal: 1100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
End-user distribution is the point of the migration, and the risky unknown is the manager flow on macOS: r2modmac must find Megabonk inside the plain-Wine prefix's Steam library, apply a profile into that game directory, and the game must boot with the loader. r2modmac's launch support may not extend to a Windows game under Wine; if it cannot launch, the fallback is manager-managed files plus the existing Wine launch path, which is still shippable but must be known before committing the port. Wine is the preferred runtime over CrossOver here. Timebox: one working session; ends with a recorded go/no-go.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 r2modmac runs on macOS (unsigned-app xattr fix applied if needed) and lists the Megabonk community
- [ ] #2 A profile installs BepInExPack_IL2CPP 6.0.788 plus at least one published community BepInEx plugin, and applying the profile writes the doorstop files and BepInEx folder into the Wine prefix's game directory (exact paths recorded)
- [ ] #3 The game launches with the profile applied - through r2modmac if it can, otherwise through the existing Wine launch path - and the working launch method is documented
- [ ] #4 The community plugin demonstrably loads (its lines present in BepInEx/LogOutput.log or visible in-game)
- [ ] #5 A rollback manifest of every file the install added outside the profile is recorded, and a MelonLoader-only launch still works after removing them
- [ ] #6 Go/no-go decision recorded on this task within the timebox of one working session
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Branch: all repo changes (docs, rollback manifest) go on a `bepinex-spike` branch off main; the spike itself mostly touches the game dir, not the repo.
2. Baseline: record the Wine game dir contents (MelonLoader launch works: version.dll, MelonLoader/, Mods/, UserLibs/) and snapshot a file manifest (path + sha256) of the game dir before any change; Wine is 11.18 from the `wine11` app, prefix `~/.local/share/megabonk/wine`.
3. AC1: download r2modmac v1.1.0 `r2modmac_macos_aarch64.dmg` into a fresh scratch dir, install to `~/Applications` (no sudo), clear quarantine with `xattr -cr` if needed, launch, confirm the Megabonk community is listed.
4. AC2: create a profile, install BepInExPack_IL2CPP 6.0.788 plus one published Megabonk BepInEx plugin, Apply; diff the game-dir manifest to record exactly what was written (doorstop files, BepInEx folder) and whether r2modmac found the game inside the Wine prefix or needs a manual path.
5. AC3/AC4: try Play from r2modmac; if it cannot drive Wine, launch through `task game:run` / `scripts/launch_game.py` with the doorstop `winhttp.dll` override set in the prefix. Confirm `BepInEx/LogOutput.log` has the plugin's lines. Watch for conflict with the existing MelonLoader `version.dll` proxy.
6. AC5: from the manifest diff, write the rollback manifest, remove those files, confirm a MelonLoader-only launch still reaches `Mods loaded` in `MelonLoader/Latest.log`, and undo any prefix DLL override added.
7. AC6: record go/no-go in the task notes, update docs (docs/development.md) with the working launch method, run `task check`, commit.

Risks: r2modmac may not detect a Wine-hosted Steam library; BepInEx doorstop needs a `winhttp` DLL override in Wine; `version.dll` (MelonLoader) and doorstop may both be loaded.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-08: r2modmac v1.1.0 (macos_aarch64) is running on the CrossOver box (`mini`), unsigned-app quarantine cleared by the maintainer; its screenshot shows Megabonk selectable with Create New / Import Profile / Browse Mods. Settings have no Steam or game path configured (`steam_path`, `game_paths` empty), so game detection is untested. Mismatch to resolve: that box's prefix is the CrossOver `Steam` bottle, not the plain-Wine prefix the parent task prefers; the plain-Wine prefix lives on the authoring box, where r2modmac is not installed. Baseline sha256 manifest of the plain-Wine game dir (958 files) taken before any change.

HANDOFF 2026-11-08 (1/2) - what was done on the CrossOver box (`mini`; see CLAUDE.local.md for ssh/tailscale details; over SSH use the tailscale address via `-o HostName=`, the LAN address gave 'No route to host'). Plain-Wine prefix on the authoring box (mbp) is UNTESTED; r2modmac is not installed there.

Setup: r2modmac v1.1.0 (macos_aarch64) installed in /Applications on the CrossOver box by the maintainer, runs, lists Megabonk (AC1 met). `settings.json` game path was set to the CrossOver bottle's game dir (key `game_paths.megabonk`; steam_path keys stay null). Profile `Megabonk` created in the UI with BepInExPack_IL2CPP 6.0.788 + wafuruns-MegabonkBetterMinimap 1.4.1. r2modmac asked for a `winhttp` DLL override; `wine reg add` fails over SSH (even `cmd /c echo` exits 1), so a line `"winhttp"="native,builtin"` was inserted into the bottle's `user.reg` DllOverrides section with a script (safe only with no wine process running).

What Apply wrote into the game dir (45 files, nothing modified or removed): `winhttp.dll` (26112 B, the pack's doorstop proxy), `doorstop_config.ini` (rewritten with absolute Z:\ paths to BepInEx\core\BepInEx.Unity.IL2CPP.dll), `BepInEx/config/BepInEx.cfg`, `BepInEx/core/*` (38 files), `BepInEx/plugins/wafuruns-MegabonkBetterMinimap-1.4.1/*` (4 files), `.r2modmac/active-bepinex-profile.json`. FINDING: Apply did NOT write the pack's `dotnet/` folder (188 files incl. coreclr.dll), `.doorstop_version` or `changelog.txt`, though doorstop_config.ini points at `dotnet\coreclr.dll`. With only Apply's files, doorstop's native winhttp.dll loaded (wine log) but BepInEx never started (no BepInEx/LogOutput.log).

Launch findings: (a) r2modmac Play detects the Windows build, finds the bottle's `steam.exe` and launches Steam through CrossOver's runner ('Using CrossOver bottle ... runner .../CrossOver-Hosted Application/wine'), log says outcome=success after ~53 s; it does not use plain Wine 11. We did not confirm BepInEx loaded from that path. (b) The repo launch path (`task game:run`, plain Wine 11.18 via scripts/launch_game.py, which sets WINEDLLOVERRIDES=version=n,b;d3d11,d3d10core=n,b) with only Apply's files: no BepInEx start. After manually copying `dotnet/`, `.doorstop_version`, `changelog.txt` from the pack zip into the game dir: still no BepInEx start while MelonLoader's `version.dll` was present. After ALSO renaming `version.dll` to `version.dll.r2spike-off` (MelonLoader off): BepInEx 6.0.0-be.788 started under Wine 11.18, downloaded unity libs from unity.bepinex.dev (needs network on first run), ran Cpp2IL + interop generation (~20 s), and loaded the plugin: LogOutput.log has 'Loading [MegabonkBetterMinimap 1.4.1]', 'Loaded MegabonkBetterMinimap', 'Chainloader startup complete'; ErrorLog.log empty (AC4 met, BepInEx-only). Only noise: Steamworks SteamAPI_Init failed because launch was not via Steam/steamstub. Conclusion so far: MelonLoader and BepInEx doorstop cannot be active together in this setup, so the port must replace MelonLoader, not coexist; r2modmac Apply alone is insufficient (missing dotnet/) - unknown whether r2modmac copies dotnet/ at Play time (the r2modmac Play run never produced a LogOutput.log in the one attempt).

HANDOFF (2/2) - rollback state and what remains.

Artifacts on the CrossOver box in `~/r2-spike/`: `game-dir-before.sha256` (721-file baseline, excludes harness/, Megabonk_Data/, D3D12/, *.dxvk-cache), `game-dir-after.sha256`, `game-dir-final.sha256`, `added.txt` (422 paths), `rollback-files.txt` (419 paths = added.txt minus MelonLoader log files and the renamed version.dll), `settings.json.bak` (r2modmac settings before the game path was set), `user.reg.before`, `user.reg.pre-winhttp`, `user.reg.with-winhttp`, `add_override.py`. On the authoring box scratchpad: `baseline/game-dir-before.sha256` (958 files, plain-Wine game dir, no change made there).

Rollback manifest (everything added outside the profile or by manual steps), paths relative to the game dir: `winhttp.dll`, `doorstop_config.ini`, `.doorstop_version`, `changelog.txt`, whole trees `BepInEx/` (227 files, includes generated interop/ and unity-libs/ and LogOutput.log), `dotnet/` (187 files), `.r2modmac/`; the rename `version.dll` -> `version.dll.r2spike-off` (undo by renaming back); bottle registry line `"winhttp"="native,builtin"` under `[Software\\Wine\\DllOverrides]` in the bottle's `user.reg`. Side effects not worth reverting: failed `wine reg` attempts rewrote Wine font entries in user.reg (Y: wine11 paths to Z: CrossOver paths); MelonLoader rotated away two old log files in MelonLoader/Logs; r2modmac settings.json now has game_paths.megabonk; r2modmac profile `Megabonk` still exists in its own data dir.

Rollback STATE: already applied on the CrossOver box (419 files removed via the manifest, empty dirs pruned, version.dll restored, winhttp registry line deleted; game was quit first and no wine process was running). NOT VERIFIED: the last command (compare a fresh sha256 snapshot against game-dir-before.sha256, then `task game:run` and look for 'MegabonkLevels mod initialized' in MelonLoader/Latest.log) was interrupted by the maintainer before it ran. So AC5 is unproven until that check passes. Expected diff vs baseline: only MelonLoader/Latest.log, wine-latest.log, wine-latest.prev.log changed and two old MelonLoader/Logs/*.log files gone.

REMAINING: (1) run the verification above; (2) decide whether to test r2modmac's own Play path properly (does it produce BepInEx/LogOutput.log if Apply is done and `dotnet/` exists, and does it require the CrossOver runner?); (3) repeat on the plain-Wine prefix on the authoring box (needs the maintainer to install and launch r2modmac there, the sandbox blocks running the unsigned app; set game path to the plain-Wine game dir, add winhttp override via the same user.reg edit with wine stopped, use Wine 11.18 at ~/Applications/wine11); (4) record go/no-go: leaning GO for BepInEx as the loader (it works under Wine 11.18 once MelonLoader is out) but with the conditions that r2modmac Apply omits dotnet/ and winhttp needs a manual override, so the Thunderstore package/docs must cover those; (5) docs/development.md update, `task check`, conventional commit on a `bepinex-spike` branch off main with no attribution and no usernames/IPs; the task notes above are already PII-clean, keep them that way; (6) tick ACs only with evidence.
<!-- SECTION:NOTES:END -->
