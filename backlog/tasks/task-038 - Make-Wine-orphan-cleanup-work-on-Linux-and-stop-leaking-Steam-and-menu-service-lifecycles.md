---
id: TASK-038
title: >-
  Make Wine orphan cleanup work on Linux and stop leaking Steam and menu-service
  lifecycles
status: In Progress
assignee: []
created_date: '2026-11-03 07:09'
updated_date: '2026-11-03 07:23'
labels:
  - tooling
  - process-hygiene
  - linux
dependencies: []
references:
  - 'scripts/run.py:683'
  - 'scripts/run.py:700'
  - 'scripts/run.py:713'
  - 'scripts/run.py:730'
  - 'tests/test_run.py:1319-1410'
  - 'taskfiles/game.yml:34-76'
documentation:
  - docs/development.md
  - docs/gamepadui.md#driving-stock-menus-with-runpy
  - AGENTS.md
modified_files:
  - scripts/run.py
  - tests/test_run.py
  - taskfiles/game.yml
  - docs/development.md
priority: high
type: bug
ordinal: 148000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Quitting or relaunching the game on the Linux player box leaves the Wine prefix's system processes behind, along with their console windows, and leaves Steam and the menu input service running indefinitely. Observed after a normal quit/relaunch cycle: 63 live processes in 10 prefix-boot groups, all parented to init with no wineserver, no Steam and no game running - 20 x winedevice.exe, 10 each of plugplay.exe, rpcss.exe, svchost.exe, tabtip.exe, and 3 x conhost.exe, the last being MelonLoader's console windows, which the compositor listed as "(not responding)" because their wineserver was already gone.

Four independent causes, all confirmed in the code:

1. scripts/run.py:730 reap_wine_leftovers_on_host() returns immediately unless platform.system() == "Darwin". On Linux the quit path only calls wait_for_wineserver_to_exit(), so no stub is ever killed. The CrossOver-on-macOS topology was the only one when this was written; the Linux native build and the Proton Windows build came later and the gate was never widened.

2. The WINE_SYSTEM_COMMAND alternation at scripts/run.py:127 lists services|plugplay|conhost|explorer|rpcss|svchost|lsass|winedevice and omits tabtip.exe. Those lines do pass the WINDOWS_COMMAND filter at scripts/run.py:126, so tabtip lands in the "others" bucket, and reap_wine_leftovers (scripts/run.py:703) aborts the whole cleanup whenever "others" is non-empty ("Windows processes still running ... skipping Wine cleanup"). Wine starts tabtip on essentially every prefix boot, so this veto makes the reap a permanent no-op even after cause 1 is fixed. It is the reason the pile reached ten generations rather than stalling at one class of survivor.

3. Classification runs over ps text, so the Steam/Proton launcher chain is invisible to it: "reaper SteamLaunch AppId=3405340 ...", "srt-bwrap ...", and ".../Proton - Experimental/.../pv-adverb .../Megabonk.exe" all begin with absolute Linux paths and can never match ^[A-Za-z]:\. Hard-killing a Steam-launched game leaves those wrappers holding the prefix; sweeping them afterwards is the harness's job.

4. No lifecycle owner for Steam or the menu service. task game:run starts Steam (taskfiles/game.yml:56-62, native binary with a Flatpak fallback) and nothing anywhere stops it; the only "shutdownsteam" in tracked files is docs/gamepadui.md:380, which records that it is a no-op under a gamescope session. run.py menu serve likewise outlived its last use by over three hours; "menu stop" exists and works, but no lifecycle step ever calls it.

Deliverable: orphan cleanup that actually runs on Linux, classifies processes without depending on which family of coreutils the host has, scopes itself to the prefix it launched, and gives Steam and the menu service an explicit opt-in teardown.

Portability rules (these are the point of the task, not an afterthought):
- Do not depend on GNU-only or BSD-only command-line flags, and do not introduce pgrep or pkill. macOS ships neither; GNU ps and FreeBSD/macOS ps disagree on keyword names (args vs command), on comm truncation, and on -ax vs -e/-A.
- Prefer not shelling out where the OS offers something better. On Linux read /proc/<pid>/comm and /proc/<pid>/cmdline: cmdline is NUL-separated argv, so backslashes and spaces inside C:\windows\system32\... cannot corrupt field splitting, and comm is exact rather than display-truncated. macOS has no /proc, so keep a ps fallback there and confine every ps quirk to that single function.
- Any ps invocation must use flags accepted by both BSD and GNU, must suppress the header (pid=,comm= style), and must run with LC_ALL=C so keyword and column output is locale-stable. No shelling out to sed, awk or grep for the matching itself - BSD sed does not expand \n in a replacement, which is already a recorded repo gotcha.
- Do not classify Windows paths with ad-hoc regex over raw text. Normalize argv[0]: backslashes to slashes, casefold, take the basename, and match against an explicit set of stub basenames. Wine emits these paths in mixed case depending on the build, /proc/<pid>/exe is useless here (it points at the Wine loader, not the Windows binary), and a basename match must not be a substring match, so C:\games\svchost_my.exe is not a stub.
- Kills stay os.kill with explicit pids, SIGTERM, a grace of WINE_STUB_KILL_GRACE_SECONDS, then SIGKILL - the shape force_kill_wine_leftovers already has. Never add a pattern-based kill: it can match the caller's own command line, which AGENTS.md forbids.

Both enumeration sources must sit behind one injected provider so tests never depend on the host's ps.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 reap_wine_leftovers_on_host no longer returns early on non-Darwin systems; the gate is removed or replaced by a 'nothing to reap' check, and a Linux quit/relaunch kills the Wine stubs.
- [x] #2 The stub set covers what Wine actually leaves behind: winedevice, plugplay, rpcss, svchost, conhost, tabtip, services, explorer, lsass, winemenubuilder. A test with a tabtip.exe present proves the reap no longer vetoes itself.
- [x] #3 Stub classification normalizes the Windows path (backslashes to slashes, casefold, basename) and matches the basename exactly, so a test asserting C:\games\svchost_my.exe and a differently-cased C:\WINDOWS\SYSTEM32\TABTIP.EXE both classify correctly.
- [x] #4 Linux enumeration reads /proc/<pid>/comm and /proc/<pid>/cmdline and execs no ps, pgrep or pkill; the macOS ps fallback uses only flags valid on both BSD and GNU, suppresses the header, and sets LC_ALL=C. Both hide behind one injected provider that tests substitute.
- [x] #5 The Steam/Proton launcher chain for this app id is reaped via explicit anchored patterns (reaper SteamLaunch AppId=3405340, srt-bwrap naming Megabonk, pv-adverb naming Megabonk.exe); a test proves an identical line for a different app id is not matched.
- [x] #6 The all-or-nothing 'others' veto is replaced by prefix-scoped reaping: stubs referencing the Megabonk compatdata prefix are killed while a test proves a live foreign-prefix Windows process is left untouched, and the foreign case still refuses to kill anything outside our prefix.
- [x] #7 Steam teardown is opt-in and verified: quit and relaunch gain a --stop-steam flag (plus a task verb) that requests a graceful client shutdown, verifies the client exited, and falls back to a comm-exact kill of explicit pids.
- [x] #8 The menu input service gains a documented lifecycle step (--stop-menu or a menu stop in the relaunch chain) and menu stop is idempotent when the service is already down.
- [x] #9 Tests cover Linux-shaped and macOS-shaped process listings, task check passes, and the existing reap tests at tests/test_run.py:1319-1410 are updated rather than duplicated where their pinned semantics change.
- [x] #10 docs/development.md gains the reaper's platform support matrix, the portability rules (why /proc, why never pkill, which ps flags are allowed), and a note that Steam and menu teardown are opt-in with the gamescope shutdownsteam caveat.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
- [ ] #5 Verified on the Linux player box: a full quit and relaunch cycle leaves zero Wine stub processes, no orphaned console windows, and no zombies
- [x] #6 The macOS CrossOver path is either exercised on a mac or explicitly reasoned about in the final summary, since it is the only path the old code supported
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Research done in the worktree (branch off local main f1c91cb). Current shape confirmed: five enumeration sites all shell out and parse text - running_game_pids (ps -axo pid=,command=), running_wineserver_pids (pgrep -f /wineserver, which macOS does not even ship), find_wine_leftovers, force_kill_wine_leftovers, find_harness_pids/force_kill_games. Tests monkeypatch these at function level, so internals can move freely; only find_game_pids/find_harness_pids/find_wine_leftovers are pinned by their own unit tests.

Approach: one process-table provider, table-based classification, prefix attribution to replace the veto, and opt-in lifecycle teardown.

1. Process table provider (scripts/run.py, new block above find_wine_leftovers)
   - ProcessInfo(NamedTuple): pid, argv (tuple[str, ...]), environ (Mapping|None). NamedTuple matches the repo idiom in build_thps_level.py.
   - read_process_table_proc(proc_root=Path("/proc")): iterate numeric entries, NUL-split cmdline, NUL-split environ (OSError -> None). Kernel threads/zombies have empty cmdline and are skipped. Tests build a fake /proc tree in tmp_path, so there is real coverage without host dependence.
   - read_process_table_ps(): the no-/proc fallback, exactly one exec of ["ps", "-axo", "pid=,args="] with LC_ALL=C and the header suppressed. args (not command) is the keyword both BSD and GNU accept. argv is the whitespace split; environ stays None there, which the attribution rules below rely on.
   - process_table(system=None, proc_root=Path("/proc")): /proc when system is Linux and the dir exists, otherwise ps. Every consumer takes an injected table so tests never depend on the host.
2. Classification without regex-over-text for Windows paths
   - WINE_STUB_BASENAMES frozenset: services, plugplay, conhost, explorer, rpcss, svchost, lsass, winedevice, tabtip, winemenubuilder (.exe each). Exact basename membership, so C:\games\svchost_my.exe is not a stub.
   - windows_basename(token): strip quotes, require a drive root, backslashes to slashes, casefold, basename. Empty string for non-Windows tokens, which is also the native-process filter that WINDOWS_COMMAND does today.
   - LAUNCHER_CHAIN_COMMAND: anchored per-chain alternatives for reaper SteamLaunch AppId=<id>, srt-bwrap naming Megabonk, pv-adverb naming Megabonk.exe, against the joined argv. App id is a parameter so a test proves a foreign AppId line is not matched.
   - STEAM_COMMAND for client detection: argv0 basename steam, or the flatpak id com.valvesoftware.Steam in argv.
3. Prefix attribution replacing the all-or-nothing veto
   - prefix_owner(info, prefix): ours | foreign | unknown. Sources in order: environ WINEPREFIX, then any argv element matching a (?:^|/)(drive_c|pfx)(?:/|$) root, compared posix-normalized and casefolded to our resolved prefix.
   - find_wine_leftovers(table, prefix=None) -> (stubs, orphans, others) keeps its 3-tuple but others becomes foreign-attributed Windows processes (Steam, other prefixes). Kill set is stubs + orphans; the old blanket veto is replaced by: kill unknown-attributed stubs only when no foreign-attributed process is present. That preserves today's macOS/CrossOver semantics exactly (steam.exe present, stubs unattributable, nothing killed) while letting Linux kill its own stubs with Steam up, because environ WINEPREFIX attributes them.
   - Anything attributed foreign is never killed.
4. Killers and the host reaper
   - force_kill_wine_leftovers / force_kill_games / running_wineserver_pids / running_game_pids all go through process_table(); table-based find_harness_pids_from_table and find_game_pids_from_table back them, with the existing text versions kept for the ps path and their current tests untouched.
   - reap_wine_leftovers_on_host: the platform.system() != "Darwin" gate is deleted. It resolves the prefix in a try (resolve_wine_prefix raises SystemExit when the game dir is not in a prefix) and passes None, keeps TERM -> WINE_STUB_KILL_GRACE_SECONDS -> force kill, and is a no-op when the kill set is empty.
5. Opt-in lifecycles
   - stop_steam(timeout, table=None): no-op true when no client is found; otherwise asks the client down through steam or the flatpak form when that binary exists, waits, then SIGTERMs and SIGKILLs the pids it listed. Only ever signals pids it found in the table.
   - stop_menu_service(timeout, path=None): extracted from the tail of run_menu's stop branch so the CLI and the teardown path share it; reports not-running and returns true when the socket is absent, so it is idempotent.
   - quit_game gains stop_steam/stop_menu kwargs called after the reap; relaunch_run passes both through prepare_harness. New flags on the quit and relaunch parsers, and a new teardown verb (run.py teardown [--stop-steam] [--stop-menu]) plus task game:stop in taskfiles/game.yml.
6. Tests (tests/test_run.py)
   - Update the pinned reap tests to table-shaped fixtures; keep assertions where semantics do not change (notably the Steam-runs skip, which now passes through attribution rather than a veto).
   - New: fake-/proc read; tabtip.exe classified and reaped (today's regression); mixed-case Windows path; lookalike svchost_my.exe not a stub; launcher chain matched for our app id and not for another; our stubs reaped while a foreign-prefix process is untouched; the Linux path execs no ps/pgrep/pkill (assert the injected provider is the only source); stop_steam escalate sequence and no-op; stop_menu_service idempotence.
7. Docs: docs/development.md section with the platform matrix, why /proc over ps, the never-pkill rule, the ps flags allowed on both families, and that Steam/menu teardown is opt-in with the gamescope shutdownsteam caveat.

Risks and deliberate limits
- WINEPREFIX is only readable for our own processes; a stub we cannot read is left alone, which is the conservative direction.
- No real Wine or Steam process is touched during development: no game launches and no player-box contact, per the instruction that another agent is finishing work there. On-box verification (first DoD item) is therefore deferred and must be recorded as such.
- The Windows tasklist branch stays as is.

Deviations from the plan, settled during implementation:
- find_wine_leftovers returns a WineLeftovers NamedTuple (stubs, orphans, others, withheld) rather than a bare 3-tuple, so a withheld count can be reported without re-walking the table.
- No separate *_from_table functions: find_game_pids, find_harness_pids and find_wineserver_pids take the table directly and the ps text parser was deleted along with WINDOWS_COMMAND and WINE_SYSTEM_COMMAND. Tests pin the table shape.
- The veto is per prefix group, not global. A candidate attributed to our prefix is killed only while no live Windows process shares that prefix; one attributed to nothing is killed only while no Windows process is live at all. Without the first rule, widening the gate to Linux would have made a Wine-under-CrossOver quit kill the services Steam itself was using inside the bottle, which is exactly what the old blanket skip existed to prevent.
- wine_prefix_root normalizes each argv token before matching drive_c/pfx, so a Windows-style prefix path attributes as well as a POSIX one.
- process_table(system, proc_root) is the only place the platform choice happens; current_wine_prefix() swallows the SystemExit from resolve_wine_prefix so an unresolvable prefix degrades to the blanket rule instead of killing the quit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified locally: task check passes end to end (mod:build, installer tests, 1756 xUnit tests, 1088 Python tests, markdownlint + ruff). The build was run against a scratch symlink farm of the game directory with its own Mods folder so the worktree build never wrote the shared install.

Read-only check against the real /proc on the Linux development host: 346 rows enumerated, no game, wineserver or Steam pids matched, and find_wine_leftovers classified nothing as a leftover. Nothing was signalled during development; there was no contact with the player box and no game launch.

Deferred: DoD item 5 (a full quit/relaunch cycle on the Linux player box leaving zero Wine stubs, no orphaned console windows and no zombies). The box was off-limits while another agent finished work there, so the Linux reap path is covered by unit tests only, including a Linux-shaped table with the Steam client running and a test asserting the Linux path execs no ps, pgrep or pkill.

macOS CrossOver path (DoD item 6) reasoned about rather than executed: the Darwin gate is gone, so the reaper now runs there too, and the same-prefix veto reproduces the old behaviour for the bottle layout where Steam's steam.exe lives inside the prefix. CrossOver stubs are only killable there if their environ can be read and no same-prefix Windows process is live, which is the conservative direction.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Wine orphan cleanup now works on Linux and the Steam and menu-service lifecycles have an owner.

What changed in scripts/run.py:
- One process-table provider. ProcessInfo(pid, argv, environ) rows come from /proc/<pid>/cmdline plus /proc/<pid>/environ on Linux (NUL-separated, so backslashes and spaces in a C:\ path cannot corrupt splitting) and from exactly one ps -axo pid=,args= with LC_ALL=C and the header suppressed elsewhere. args is the keyword both the BSD and the GNU family accept. Windows keeps its tasklist branch. pgrep is gone, pkill was never used, and every consumer takes an injected table.
- Classification by exact, casefolded Windows basename over argv against WINE_STUB_BASENAMES (services, plugplay, conhost, explorer, rpcss, svchost, lsass, winedevice, tabtip, winemenubuilder), so tabtip.exe is a stub rather than a veto and C:\games\svchost_my.exe is not one. The Steam/Proton launcher chain for app id 3405340 (reaper SteamLaunch AppId=, srt-bwrap, pv-adverb) is a candidate now; a different app id is not.
- The all-or-nothing others veto is replaced by prefix attribution through WINEPREFIX or a drive_c/pfx path in argv. Foreign-prefix processes are never killed; our own candidates are killed unless a live Windows process shares the prefix; unattributed candidates wait for a quiet host, which is the old rule kept for the hosts that cannot read an environment. The Darwin gate is deleted.
- Opt-in teardown: stop_steam_client asks the client down through steam or the Flatpak form, waits, then signals only the pids it listed; stop_menu_service is idempotent and shared with menu stop. quit and relaunch take --stop-steam and --stop-menu, run.py teardown runs the teardown with no harness marker, and task game:stop wraps it.
- docs/development.md documents the platform matrix, why /proc over ps, the never-pkill rule, the allowed ps flags, and the opt-in client teardown with the gamescope shutdownsteam caveat.

Tests: tests/test_run.py fixtures are argv-shaped (proc, wine_stub, windows_process, fake_proc) instead of ps text; 1088 Python tests pass, 1756 xUnit tests pass, task check passes clean. New coverage: tabtip regression, case-insensitive Windows path, lookalike basename, launcher chain matched by app id and not by another, foreign prefix spared, our stubs reaped with the Steam client up, same-prefix Windows process holding the reap back, fake /proc read, ps flags and LC_ALL, no subprocess at all on the Linux path, wineserver matcher, stop_steam no-op and escalation, stop_menu idempotence, teardown wiring, relaunch flag forwarding.

Not verified on hardware: the player box was off-limits, so DoD item 5, a real quit/relaunch leaving zero stubs and no orphaned console windows, is still open. The macOS CrossOver path is reasoned about rather than executed; it now runs the reaper too, and the same-prefix veto is what preserves the old behaviour there.
<!-- SECTION:FINAL_SUMMARY:END -->
