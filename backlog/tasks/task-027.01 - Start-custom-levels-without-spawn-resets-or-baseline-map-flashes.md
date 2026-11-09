---
id: TASK-027.01
title: Start custom levels without spawn resets or baseline-map flashes
status: Done
assignee: []
created_date: '2026-10-31T18:48:00Z'
updated_date: '2026-11-01T01:09:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - src/MegabonkLevels.Mod/custom_level_state_patch.cs
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - scripts/run.py
  - taskfiles/mod.yml
documentation:
  - docs/development.md
parent_task_id: TASK-027
priority: high
type: bug
ordinal: 133000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Linux runtime investigation confirmed Calcium's ordinary half-pipe slide is repeatedly reset during the authored-start watchdog's five-second window. The generated Forest baseline also becomes visible before Warehouse edits finish, making startup feel broken. Preserve normal movement and conceal incomplete custom-level setup without changing vanilla starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Authored player placement permits falling, sliding and movement immediately after placement, including within the former five-second window.
- [x] #2 Late vanilla spawn placement still resolves to the authored start, without continuously enforcing distance from that start.
- [x] #3 Custom-level startup remains covered until generation, custom edits and initial player placement are ready; vanilla launches and failed/cancelled starts do not retain a cover.
- [x] #4 Regression tests cover startup lifecycle, missing/late player, cancellation, timeout and vanilla isolation; development docs explain the behavior.
- [x] #5 Stock-menu Calcium/Warehouse startup is verified on Linux with no input after launch, with evidence of no repeated correction and no exposed Forest frame.
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
Evidence-driven plan (recorded after runtime tracing on the Linux target; supersedes the handoff plan).

## Runtime evidence (wm2, Proton, stock menus, Calcium + Warehouse, zero input after launch)
Temporary Harmony probe on TransitionUI / MapGenerationController / MyPlayer, plus 0.1s body samples. Wall clock, CONFIRM at 13:58:01.978:

- 01.978 MapController.StartNewMap (mod's awaited start) -> 01.981 TransitionUI.A_transitionStart, 01.984 A_MapTransitionStart, 01.985 A_NewRunStarted
- 03.203 MapGenerationController.A_PreGeneration (Forest baseline)
- 03.240 MyPlayer.Spawn (120,0,0) -> 03.242 A_PrePlayerSpawn -> 03.244 StartPlayer (Calcium): the stock spawn lands INSIDE generation, exactly once
- 03.437 game raises A_GenerationComplete; mod subscribers then index 1559 objects, remove the Forest baseline (03.5-03.9), apply 1241 edits (rails/objects 05.0x)
- 05.187 our placement #1, then again at 06.005, 06.856, 07.690, 08.523, 09.373 - six TeleportPlayerImmediate calls, all from live_edit_patch.cs:603, ~0.84s apart
- player comes to rest at (109, 29.75, -112.4) about 10.4; level playerStart=[109,38,-116], killFloorY=-35

## Root causes
1. TickPlayerStart enforces an XZ distance of 1m from the authored start for 5s (PlayerStartWatchSeconds/ToleranceXz). The authored start sits ~6m above a curved half-pipe, so a legitimately falling/sliding player always drifts past 1m and is yanked back every ~0.84s until the window expires. That is the "stuck in place, dropping, resetting" symptom, and it re-arms the half-pipe launch each time.
2. The stock transition's visible fade completes around t=1s (isTransitioning clears at ~0.97s) although its animation event A_transitionEnd fires at 3.7s; content is not ready until ~5.2s. The baseline Forest map, its teardown and the build-up are therefore exposed for seconds.

## Design
A. Pure, game-independent policy in src/MegabonkLevels.Mod/startup_gate.cs (no UnityEngine or game types; linked into tests/MegabonkLevels.Tests) - a phase machine Idle/Covering/Placing/Open that emits recorded commands (ShowCover, HideCover, HoldPlayer, PlacePlayer, ReleaseHold, Log). Rules: cover arms only for a custom run; placement is requested once, when generation and edits are done, and retried only until it succeeds; a game-driven spawn re-places exactly once per burst (Spawn+StartPlayer+TeleportPlayerNextStage arrive within 4ms); timeout/cancel/failure/vanilla release the cover exactly once and never re-cover; no distance-based teleports exist anywhere in the policy.
B. Adapter in src/MegabonkLevels.Mod/startup_cover.cs: owns the cover UI (EditorUi.NewCanvas + full-screen black Image + the level title, hidden by default, built lazily), Harmony postfixes on MyPlayer.Spawn / StartPlayer / TeleportPlayerNextStage -> gate.GameSpawnedPlayer, and the OnUpdate tick that drives timeout, placement attempts and the hold.
C. Hold instead of re-teleport: between the stock spawn and the single placement, keep the body at the position the game chose (write rb.position, zero rb.velocity) so it cannot fall through the map being rebuilt. One TeleportPlayerImmediate per placement; nothing writes to the player after placement except a game-spawn trigger. Skipped while the editor is active so harness teleports stay untouched.
D. Arm from the single choke point: CustomLevelStatePatch's MapController.StartNewMap prefix calls the gate with CustomLevelState.IsActive, so vanilla runs never cover. LevelLoaderPatch's StartNewMap catch releases the cover.
E. Delete the temporary probe (startup_probe.cs and its two call sites) once verification is done.

## Steps
1. Tests first for the policy (lifecycle order, vanilla isolation, missing player, late spawn, burst coalescing, cancel, error, timeout, no repeated placement) in tests/MegabonkLevels.Tests, linked in its csproj.
2. startup_gate.cs to satisfy them; dotnet test green.
3. startup_cover.cs adapter + wiring; remove PlayerStartWatchSeconds/PlayerStartToleranceXz/SchedulePlayerStart/TickPlayerStart distance logic.
4. Docs: docs/development.md startup lifecycle; correct the "re-apply for 5s" text in docs/thps-warehouse-layout.md.
5. Remote rebuild on wm2, relaunch, stock menus PLAY -> Calcium -> CONFIRM -> Warehouse -> CONFIRM, then no input; evidence = log shows exactly one placement and no repeated correction, plus a burst of existing DevHarness screenshot captures during startup showing no Forest frame.
6. Restore the pre-experiment DLL/PDB if verification fails; leave no probe, markers or attribution.

## Risks
- Cover above the stock TransitionUI canvas: sorting order must beat the game's transition canvas; if the game re-parents or disables our canvas the cover could vanish - the timeout always releases it, so a failure degrades to today's behaviour, never to a stuck black screen.
- Holding the body via Rigidbody writes: Megabonk's MyPlayerMovement is Rigidbody-based, so pinning position plus zeroing velocity should stop the fall; if the movement script overrides it, the player may drift a little while hidden - placement still corrects once.
- Longer levels could still expose build-up work if it exceeds the timeout; the timeout is a config constant, logged when it fires.

User-approved review follow-up (items 2–4 only), test target ssh mini: explicitly handle/document polled PlacePlayer and ReleaseHold decisions; add validated MEGABONK_STARTUP_TIMEOUT_SECONDS (8s default) as a no-progress timeout renewed by generation milestones, changing tile counts and completed edit actions, with pure regression tests; document that authored-start corrections including next-stage teleports assume a single-stage level file. Do not change teleport exception behavior or unrelated review items. Build and run tests on mini, then fresh-launch and capture rendered gameplay evidence.

User reproduced Tony below Warehouse through stock menus on MBP. Installed level preserved: playerStart [109,38,-116], 1294 edits (repo 1241), no killFloorY. Live paused state at (120,-18.075,-2.83) despite placement log. Native disassembly confirmed MyPlayer.TeleportPlayerImmediate RVA 0x4B6E00 calls PlayerMovement.TeleportPlayer RVA 0x343A80, which queues Rigidbody.MovePosition RVA 0x232D2C0 and zeros velocity, not a synchronous Rigidbody.position write. Fix the startup adapter by calling the game routine once for facing/velocity then committing rb.position directly to authored body position before reporting completion and dropping the cover. Require a live rb; preserve level files, no continuous position enforcement, no new Harmony targets. Regression verification: fresh harness run with editor auto-entry cancelled, screenshot and state showing correct authored-start neighborhood; then request stock-menu manual confirmation.

Root-cause correction after failed synchronous-body candidates: temporary trace proves SAME player/body stays at authored (109,38,-116) for ~1.8s then moves to native (120,2,-3) without another TeleportPlayer call. Native SpawnPlayerPortal.MovePlayer RVA 0x361080 lerps the player Transform between cached baseline positions; DoPortal MoveNext RVA 0x362AD0 enables that after generation, disables it before emitting A_PortalClosed. StartPortal skipped-animation branch also emits A_PortalClosed. Replace speculative body/Transform/SyncTransforms writes with an explicit portal-readiness prerequisite: adapter arms custom gate waiting for A_PortalClosed; pure gate may owe placement when content ready but cannot attempt until portal completion. Subscribe once through existing Install flow; no new permanent Harmony targets. Cover and hold remain until BOTH content and portal are done, bounded by inactivity timeout; completion renews progress and never requests another placement after success. Add tests first for both event orders, duplicates, spawn bursts while waiting, late portal after timeout, cancel and vanilla isolation. Remove temporary trace fields and TeleportPlayer patch, rebuild/deploy and verify Tony on original installed Warehouse before claiming fixed.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
USER INTENT / CURRENT STATUS: The user said Yes to fixing both repeated teleporting and loading transition, then asked to update this Backlog task for the next agent to finish. Stop at handoff. This task is To Do; do not mistake its existence for implementation. Parent TASK-027 is the completed diagnostic spike, not the fix. No production source changes remain, and no tests for this fix have been written. No Unity Editor is installed on the Linux target, but one is not needed for this runtime C# fix.

CONFIRMED REPRO: Windows Megabonk 1.0.69 under Proton Experimental on CachyOS (not native Linux), MelonLoader 0.7.3. Stock menus: select Calcium, Confirm, select Warehouse, Confirm; send no movement afterward. Diagnostic run used normal enemy damage/spawns, no developer load-level, no invulnerability, no editor freeze and no altered spawn behavior. Temporary StartupProbe logged every 0.1s for 9s, plus every actual correction. Initial correction t=43.420 from body (120,2.43,0) to feet target (109,36.08,-116). Five further corrections at t=44.262,45.096,45.947,46.780,47.615 (~0.84s apart). Each repeat was from body (109,30.65,-114.89), velocity (0,-3.44,6.92): the player had fallen onto/slid down the ramp past the one-metre X/Z tolerance, not returned to Forest. After expiry he settled at body (109,29.75,-112.40) without input. frozen=False, paused=False, teleporting=False. The authored point itself is above the surface (body initially ~38, settles ~29.75); changing spawn height alone would mask rather than fix the watchdog defect. Linux-specific exclusivity is NOT established; this is shared code, and macOS was not runtime-tested in this investigation.

LOADING EVIDENCE: Forest A_GenerationComplete at 13:45:42.360, LiveEdit applied 1241 edits at 13:45:44.044 (1.684s), first authored correction 13:45:44.119. Only one generation occurred; no repeated cross-map travel. This matches the reported 1–2s Forest exposure, but the early screenshot captured loading/black, so actual exposed-frame duration was NOT independently measured. The fix needs sequential rendered-frame evidence, not just matching log timing.

EXACT CODE LOCATIONS (verify after updates): live_edit_patch.cs SchedulePlayerStart around 542–552 sets a five-second real-time deadline; TickPlayerStart around 587–609 compares body X/Z against authored target with 1m tolerance and TeleportPlayerImmediate on displacement. It ignores height deliberately but repeatedly resets ramp motion. _playerStartLogged logs only the FIRST correction, concealing subsequent resets in ordinary logs. OnGenerationComplete around 484–528 applies edits synchronously then schedules start, for both tile and terrain paths. megabonk_levels_mod.cs OnUpdate calls DevHarness.Poll, LevelLoaderPatch.Pump, TickPlayerStart, then slope/kill-floor/editor ticks. level_loader_patch.cs PrepareRun around 192–209 sets pending edits/metadata, marks custom start and creates RunConfig. HoldForNextStart / AwaitedStartPrefix prepare stock-menu starts. custom_level_state_patch.cs hooks MapController.StartNewMap to activate/deactivate custom state. Account for prefix ordering (AwaitedStartPrefix has Priority.First), stale static metadata between runs, in-place load and terrain maps; do not accidentally arm a cover for an editor-only settings change.

AVAILABLE STOCK SIGNATURES from local .tools/il2cpp_dump/dump.cs: MyPlayer.Spawn(Vector3 position, Vector3 direction, bool useHeightOffset=false), RVA 0x4B6770; StartPlayer(ECharacter,Vector3), 0x4B6A90; TeleportPlayerNextStage(), 0x4B6EB0; TeleportPlayerImmediate(Vector3 position,Vector3 dir,Vector3 cameraDir,float cameraPitch=20), 0x4B6E00. Immediate's last argument is camera pitch, NOT delay. Existing runtime docs confirm it places feet, offsets body by 1.925 and zeros velocity; transform.position updates only after physics sync. MapGenerationController has A_PreGeneration/A_GenerationComplete, isGenerating, tileSpawnPosition/tileSpawnDir (private stock setters). TransitionUI has Instance, RawImage overlay, bool isTransitioning, StartLoadingMap(string), StartTransition(Action,float transitionTime=.5,float delay=.5), StopTransition(), IsTransitioning(), private IEnumerator EndTransition and DoTransition, plus transition start/end/map-start events. These are candidate hooks only: native bodies/coroutine ordering have NOT been traced for the fix. Do not assume StopTransition interception alone pauses an already-running fade.

DESIGN RISKS / NON-GOALS: Do not merely shorten the five-second window, increase tolerance or alter half-pipe collision. Do not keep respawning on position drift, add a five-second freeze, or block intentional harness teleports. Handle late stock spawn explicitly with evidence, deduplicating events that refer to the same startup. For a dedicated cover, ensure persistence across scene change, correct sorting over game UI, cleanup on failed/cancelled/vanilla starts and a bounded real-time fail-open path with useful warning. Stock transition hold and custom cover remain alternatives; neither has been chosen or coded. No unrelated installer/menu-driver/THPS content rebuild needed.

TARGET / BUILD: SSH alias wm2, checkout ~/git/megabonk_mods, game /media/sdcard/SteamLibrary/steamapps/common/Megabonk. Shell tools via ~/.local/bin/mise exec --. Remote tree was clean after restoring probe source. Initial task mod:build failed because gitignored Directory.Build.props was absent, not due to source errors. Successful diagnostic build: ~/.local/bin/mise exec -- dotnet build src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj -p:MelonLoaderFolder=/media/sdcard/SteamLibrary/steamapps/common/Megabonk/MelonLoader/net6 -p:Il2CppAssembliesFolder=/media/sdcard/SteamLibrary/steamapps/common/Megabonk/MelonLoader/Il2CppAssemblies -p:ModInstanceFolder=/media/sdcard/SteamLibrary/steamapps/common/Megabonk/Mods -p:GameFolder=/media/sdcard/SteamLibrary/steamapps/common/Megabonk. It deploys DLL/PDB and NLayer automatically. Save the installed DLL AND PDB before the next experiment; diagnostic run saved only DLL. The original DLL has been restored byte-for-byte; its PDB may remain from diagnostic build. MelonLoader loads DLL only at startup: always fresh launch.

MAINTAINED REMOTE INPUT: local `mise exec -- uv run scripts/run.py menu start --host wm2 --remote-repo '~/git/megabonk_mods' --display :1`; `menu drive '<JSON>'` with same options, --game-dir /media/sdcard/SteamLibrary/steamapps/common/Megabonk --out .tools/<name>.png; `menu stop` afterward. Use actual display from game's environment if changed. Stock menu keys require OS-level service, not editor injection. Confirmed coordinates at 1920x1080: Calcium tile (450,260); character Confirm (1560,850); Warehouse row (350,790); map Confirm (1550,835). Inspect screenshots between batches; controller A initially selects focus rather than always confirming. Successful explicit mouse sequence after Enter: move/click Calcium, move/click character Confirm, inspect Map Selection, move/click Warehouse, move/click map Confirm. Start service before game. Do not recreate retired scratch input scripts.

HARNESS / LAUNCH / CLEANUP: marker <game>/harness/enabled initially absent and is again absent. Enable with MEGABONK_GAME_DIR=<game> ~/.local/bin/mise exec -- uv run scripts/run.py enable before launch; use Steam `steam steam://rungameid/3405340`. User authorized restart/testing; game was quit at end and is currently expected stopped (verify). No owned input service/socket remains; verified /run/user/1000/megabonk-menu/input.sock absent. Temporary probe source removed locally/remotely, original DLL restored. Do not leave devices running, harness enabled or stale instrumented DLL after an unsuccessful fix attempt. Prefer harness quit when enabled; if disabled and necessary use exact-name `pkill -TERM -x Megabonk.exe`, never a self-matching pkill -f pattern.

EVIDENCE / TEST BASELINE: local and remote .tools/startup-probe/calcium-stock-start.log contain full confirmed trace. Remote .tools/startup-probe/original.dll and original-live-edit.cs are pre-probe backups; before.log is pre-restart log. Local screenshots .tools/startup-character.png, startup-map-selected.png, startup-launch.png (loading/black), startup-settled.png. .tools is gitignored; grep/rg needs explicit path and rg -u when needed. Before investigation, full local task check passed 1498 C# + 900 Python tests. Known unrelated Linux test limitations: ten THPS fixtures search Taskfile.yml instead of tracked taskfile.yml; two Wine-exit Python tests attempt unmocked kill PID 7 and raise PermissionError. Do not run tests elevated to work around these. No full test rerun during diagnostic spike since source was restored. Working tree at handoff has only untracked TASK-027 and TASK-027.01 backlog files, assuming no intervening user changes; no commits or pushes for either investigation/fix yet.

Prior validation: local task check passed 900 Python tests plus lint/format; C# suite 1517 passed. Previous wm2 stock-menu verification showed one hold, one placement and no timeout; no-input run confirmed smooth after removing screenshot bursts. Current follow-up runtime target is mini.

Review items 2–4 implemented: adapter explicitly acknowledges PlacePlayer/ReleaseHold as polled decision-log entries; MEGABONK_STARTUP_TIMEOUT_SECONDS parses positive finite invariant seconds (fallback 8s), and the deadline renews only on pre-generation, changing tile counts, generation completion, successful edit actions and content readiness; docs/code state the single-stage next-stage-teleport assumption. Added 16 regression cases, written before implementation (initial compile red on missing Progress/ParseTimeoutSeconds), including progress beyond initial deadline, stall release, placement retry non-renewal and no resurrection after timeout/cancel/vanilla/placement. mini mod build: 0 warnings/errors; full C# suite 1533 passed after dependency restore. Local task check: 900 Python tests and lint passed. mini task check: C# passed, 898 Python passed, 2 unrelated THPS prefab fixture failures (missing piece-room-wall-south.prefab / obsolete kit or alias entries). Runtime verification BLOCKED: fresh run.py relaunch --no-level handed off to GUI but Wine stalled before mod loading (Latest.log ends at 0 Plugins loaded; Unity Player.log at graphics device initialization); harness did not become ready. Launcher force-cleaned only the attempted Megabonk processes; no game remains. Other Wine apps were left untouched. Boot evidence mini:.tools/startup-review-mini/boot.log; test/check logs mini:.tools/startup-tests-restored.log and .tools/startup-check.log. No runtime behavior claim for these follow-up changes; no commit.

Independent mini lint attempt also blocked because markdownlint is not installed/in PATH; local lint passed. No dependencies installed or unrelated THPS fixtures changed to mask these target-environment failures.

User requested retrying runtime verification on the local mbp after mini stalled before mod load. Verify rebuilt DLL is deployed to the locally resolved plain-Wine prefix, then fresh-launch and inspect cover/startup/placement with sparse captures; leave unrelated Wine apps untouched.

MBP runtime retry: direct dotnet build succeeded with 0 warnings/errors; built and installed DLL SHA256 both 53d1d30b31479831692684c7e9a7a9bf379bd6a2dad81dea13356158fca70ec7 in ~/.local/share/megabonk/wine. Plain Wine boot/harness/Steam readiness succeeded. Fresh Warehouse harness load as Calcium with editor auto-reentry immediately cancelled: cover screenshot black + Warehouse title; logs StartNewMap 19:47:40.085, held 19:47:41.448, generation complete 19:47:41.577, one placement at (109,36.08,-116) 19:47:43.112, no timeout or further placement. HOWEVER subsequent state (editor=false, frozen=false, normal damage/spawns) reported player transform around (120,0.57,2.03), not authored start, and frame lacked normal gameplay HUD / showed a low view into Warehouse. After attempted focus it reported (120,-18.075,-2.41). Do NOT treat this as successful authored-placement verification. Harness loads initially auto-enter editor; first attempt was invalid for movement and was discarded. Local stock menu automation attempts with Accessibility/Quartz input did not activate Play in Wine, so no stock-menu conclusion. Possible background/focus/initialization ordering remains unconfirmed; no source change attempted for this separate finding.

MBP timeout runtime case: fresh launch with process-only MEGABONK_STARTUP_TIMEOUT_SECONDS=2 and MEGABONK_DEV=true, loaded existing example-forest fixture (no playerStart) then cancelled editor auto-entry. Black Loading cover captured. StartNewMap 19:50:46.952, hold 19:50:48.688, generation complete 19:50:48.820, timeout release 19:50:50.886 (~2.07s after completion, ~3.93s after start), proving configured interval and progress renewal rather than a fixed launch deadline. Later screenshot shows Forest gameplay, no cover; state editor=false/frozen=false/invulnerable=false/spawnsOff=false. Evidence .tools/startup-review-mbp/{warehouse-cover.png,warehouse-playing.png,warehouse.log,timeout-cover.png,timeout-released.png,timeout.log}. No .env edits, no diagnostic source or commits; game quit and Wine leftovers cleaned with maintained run.py quit.

Stock-menu MBP evidence (19:55 run): StartNewMap 19:55:33.188, hold 34.334, generation complete 34.440, placement log 36.007, but user and live state confirm Tony remains underneath Warehouse at native spawn XZ. Existing file cleanup moved extras only; kept original thps byte-for-byte, including authored start matching repo. isTeleporting=false, hasStarted=true. Game currently paused by user; do not unpause or alter installed level to mask defect.

Native TeleportPlayerImmediate/MovePosition alone was not root cause. Both direct Rigidbody assignment and Transform+Physics.SyncTransforms failed because a later spawn-portal animation overwrites them. Do not retain those speculative body-placement changes. Trace saved .tools/startup-review-mbp/tony-trace.log; temporary trace code must be removed from final DLL.

Confirmed fix for Tony-under-Warehouse: final implementation waits for SpawnPlayerPortal.A_PortalClosed AND content readiness before the ONE authored placement, in either event order. No extra body/Transform writes, SyncTransforms, polling player distance or new permanent Harmony targets. Portal completion is also a progress milestone. Native StartPortal skipped-animation branch and normal DoPortal both emit A_PortalClosed after ownership of player position ends. Temporary trace fields/sampling/TeleportPlayer Harmony patch removed; final game log verified contains no StartupTrace. Require live rb before placing; cancelled pending placements cannot run while gate Idle.

Regression tests written first: 6 new cases for portal/content event order (2 cases), duplicate completion/no second placement, spawn bursts while waiting, timeout plus late portal, and cancellation/vanilla isolation (2 cases). Full C# suite now 1539 passed, clean mod build 0 warnings/errors, full task check green (900 Python + lint). Final MBP harness-driven Tony test used exact installed UserData/Levels/thps.mblevel.json (1294 edits), SHA256 b82246effd8dc22158037d598e072f4cb28f59732f9cf59ee461fae6404c8f18 confirmed unchanged. Editor auto-reentry cancelled before generation; normal damage/spawns, no movement input, no invulnerability. StartNewMap 20:06:17.225, hold 18.687, generation complete 18.819; cover still black/Warehouse at ~3.8s while awaiting portal; single authored placement at 20:06:24.345 (~7.12s), no timeout. At ~8s state position [109,30.774754,-115.17125], later [109,29.747574,-111.17714], editor=false/frozen=false, and rendered frame shows Tony inside Warehouse on the starting ramp with normal HUD. Exactly one placement logged; no reset to native (120,2,-3). Evidence .tools/startup-review-mbp/tony-portal-{cover,wait,playing}.png and tony-portal.log. Prior direct-body and sync candidates were discarded; previous speculative root-cause notes are superseded by portal evidence.

Final build deployed locally. Relaunching to main menu for user stock-menu manual verification; do not claim a new automated stock-menu pass (that was user-reproduced before the fix). No level content modified, extra installed JSONs remain safely archived outside Levels with only thps.mblevel.json selectable. No commits.

User manually verified the final portal-readiness fix on MBP and confirmed "That works." User explicitly authorized committing the tested fix. Runtime evidence: prior wm2 stock-menu Calcium verification for no yo-yo/no Forest frame and vanilla isolation; final portal-readiness correction verified on MBP with the original installed Warehouse and confirmed manually by the user. No claim of a fresh Linux run after the portal-readiness correction.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Replaced the five-second distance watchdog with event-driven startup cover, hold and single authored placement. Placement waits for both custom edits and the stock spawn portal to finish, preventing the portal animation from moving the player back underneath Warehouse. Added a configurable progress-aware inactivity timeout and lifecycle regression coverage; documented polled decisions and the single-stage assumption. Verification: 1539 C# tests, 900 Python tests and lint pass; prior Linux stock-menu/vanilla-isolation evidence recorded; final portal fix verified on MBP and manually confirmed by the user. Committed conventionally with no attribution. No continuous correction, temporary probes or level-file edits.
<!-- SECTION:FINAL_SUMMARY:END -->
