---
id: TASK-027.02
title: Startup cover drops the player below the level after a restart
status: Done
assignee: []
created_date: '2026-11-03 03:51'
updated_date: '2026-11-03 05:14'
labels:
  - thps-warehouse
  - harness
  - startup
dependencies: []
references:
  - src/MegabonkLevels.Mod/startup_cover.cs
  - src/MegabonkLevels.Mod/startup_gate.cs
  - docs/development.md
  - levels/thps.mblevel.json
  - scripts/run.py
  - src/MegabonkLevels.Mod/death_restart_patch.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - scripts/mcp_server.py
  - tests/MegabonkLevels.Tests/startup_gate_tests.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
modified_files:
  - src/MegabonkLevels.Mod/startup_gate.cs
  - src/MegabonkLevels.Mod/startup_cover.cs
  - src/MegabonkLevels.Mod/death_restart_patch.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - scripts/run.py
  - scripts/mcp_server.py
  - tests/MegabonkLevels.Tests/startup_gate_tests.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
  - tests/test_run.py
  - tests/test_mcp_server.py
  - docs/development.md
parent_task_id: TASK-027
priority: high
type: bug
ordinal: 146000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Restarting into the THPS Warehouse (loading levels/thps.mblevel.json into a game that already ran, e.g. scripts/run.py relaunch) consistently leaves the player below the level; the first boot into the level works. The player rests on the warehouse mesh's underside at y=-18.075 near (108, -18, 5.7): the level's floor is about y=-4.9 and the authored kill floor is -35, so the player is stuck under the floor without dying, and the run cannot be tested.

Live evidence (2026-11-02, fedora, Windows build under Proton Experimental, MelonLoader/Latest.log):
- 21:47:16 DevHarness: load-level thps.mblevel.json; 21:47:17 StartupCover: held where the game put the player; 21:47:18 KillFloor armed at y=-35.
- 21:47:19 DevHarness: teleport to (60.80, 18.60, -70.50) succeeded (state confirmed the position), then 21:47:22 StartupCover: player placed at the level start (109.00, 36.08, -116.00) overwrote it 3 s later.
- 21:48:44 and 21:48:45 two further StartupCover placements a second apart while KillFloor re-armed: a fall-through -> kill -> respawn loop. Later harness state shows the player at (108.3, -18.075, 5.73), below the floor and above the kill floor.

Context a fresh implementer needs: the Warehouse is one bundle-placed mesh (bundle:thps/Warehouse, scripts/build_thps_level.py), not tiles. The generated tile mesh (LiveEditPatch.GroundCollider()) does not cover the bundle mesh (independent live finding on 2026-11-02: BossSpawnRedirect down-rays against it logged "no ground under the boss" for both spawns). The startup cover (src/MegabonkLevels.Mod/startup_cover.cs, gated by startup_gate.cs, see "Custom-level startup cover" in docs/development.md) releases the player at the authored playerStart; if the bundle mesh's colliders are not ready at that moment on a restart, the player falls through the mesh skin onto its underside skirt, which is above the kill floor, so nothing kills them and they stay stuck. The cover also re-placing after a harness teleport breaks scripted verification.

Wanted outcome: after a restart the player stands on the level's floor at the authored start, and a harness teleport sent after load is not overwritten by the cover. Root cause (collider readiness vs cover timing, cover re-arming, or both) to be established from the running game before choosing the fix; the harness, state readout and logs are documented in docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Relaunching levels/thps.mblevel.json on a Proton host leaves the player standing on the level's floor: a state readout taken at least 5 seconds after the last StartupCover placement reports the player above the floor surface (not at y about -18), on a second and third restart of the same game process
- [x] #2 A harness teleport sent after load is not undone by the startup cover: no 'StartupCover: player placed at the level start' log line follows a 'DevHarness: teleport' line, and state still reports the teleport point
- [x] #3 No fall-through loop after a restart: KillFloor does not re-arm repeatedly at startup and no repeated StartupCover placements appear within a second of each other
- [x] #4 First-boot into the level and stock non-custom startup behave exactly as before, and the TASK-027.01 guarantees (no spawn resets, no baseline-map flash) still hold
- [x] #5 The established root cause is recorded in the task with the log evidence, and the 'Custom-level startup cover' section of docs/development.md covers the restart case
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
Verification host: fedora (ssh fedora, tailscale only) — Windows depot 3405342 under Proton Experimental, harness enabled, thps pack installed, game dir ~/.local/share/Steam/steamapps/common/Megabonk. Build on mf (dotnet + Directory.Build.local.props), scp MegabonkLevels.Mod.dll/.pdb to fedora's Mods, drive the harness with ssh fedora 'cd ~/git/megabonk_mods && .venv/bin/python scripts/run.py ...'. Sync tracked files mf -> fedora (fedora was at 745ccd7; do not rsync the unrelated in-progress player_installer files).

1. Baseline repro on fedora: quit the running game, relaunch, load levels/thps.mblevel.json, and repeat the load/restart in the same process; capture MelonLoader/Latest.log (StartupCover, KillFloor, DevHarness lines) plus timed state readouts. Reproduce the y=-18.075 resting spot before changing anything.
2. Instrument, do not guess (AC#5). Temporary harness-gated probe, removed before the commit:
   - body position/velocity sampled ~4 Hz for ~12 s from load, tagged with the gate phase;
   - down-ray from the authored start and from the player at placement: hit yes/no, distance, collider name+instance id, plus the Warehouse object's collider count/enabled state;
   - postfix on SpawnPlayerPortal.MovePlayer logging the player's position before/after, and on the placement teleport logging the position one and several seconds later.
   Decide between (a) SpawnPlayerPortal writing cached baseline positions after the single placement, (b) placement before the bundle mesh's colliders can stop a fall, (c) hold/re-arm interaction in the gate.
3. Fix in the same shape as today: decisions in the pure StartupGate (startup_gate.cs), Unity/game calls in StartupCover (startup_cover.cs). Candidate changes pending step 2: a harness teleport cancels an owed placement and releases cover/hold (AC#2); do not place until the ground under the authored start actually exists rather than trusting content readiness (AC#1/#3); respond to the real late-write event instead of distance enforcement, keeping the TASK-027.01 guarantees (AC#4).
4. Tests first for whatever lands in the gate: tests/MegabonkLevels.Tests/startup_gate_tests.cs covers the new decisions, plus task mod:test and task check.
5. Verify on fedora: player above the floor surface on the second and third restart >=5 s after the last placement (AC#1); no StartupCover placement after a DevHarness teleport and state still shows the teleport point (AC#2); no repeated KillFloor re-arms or placements within a second of each other (AC#3); first boot and a stock non-custom run behave as before (AC#4).
6. Remove the probe, extend the "Custom-level startup cover" section of docs/development.md with the restart case and what to read in the log (AC#5), record the root cause with its log evidence in this task, conventional commit with no attribution.

Risks: launching on fedora needs the gamescope/desktop session and Steam; the Photosensitivity Warning has to be dismissed with run.py menu drive + KEY_ENTER before a load returns MapData; stale harness commands must be cleared (run.py relaunch does it).

Final solution as executed (supersedes the candidate changes in step 3; the probe from step 2 was deleted before the commit).

Decisions live in the pure gate, game calls in the adapter:
- StartupGate gains PortalOpened(now) and HarnessTeleported(now). PortalOpened only takes ownership when the authored start has already landed (_placed): it shows the cover, pins the body, and PortalClosed then re-owes exactly one placement. A portal that opens before the first placement leaves holding to the game's own spawn, so the boot path is unchanged. _ignoringPortal suppresses further placements after a deliberate teleport; it clears on the next GameSpawnedPlayer or RunStarted. Tick gives up an opened-portal wait once the cover timeout passes (_portalDeadline) so a portal that never reports back cannot strand the run.
- StartupCover.OnHarnessTeleported() nulls the cached _holdPoint as well as telling the gate.
- DeathRestartPatch's RestartRun prefix calls StartupCover.OnRunStarting(true) beside RearmLevelEdits.
- LiveEditPatch.Install subscribes SpawnPlayerPortal.A_PortalOpen next to A_PortalClosed.
- New harness verb restart-run (HarnessCommandKind.RestartRun -> MapController.RestartRun), run.py subcommand, MCP restart_run tool: makes the stock restart path reachable without OS-level input on the Rewired death menu, which is how this was reproduced and verified.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started (Linux host, this machine). Researching startup cover/gate, kill floor, and bundle collider readiness in the running game before choosing the fix, per the task's root-cause-first requirement.

Root cause (established from the running game with a temporary env-gated probe, since deleted; two defects had to be fixed together):

1. The stock death-screen Retry never arms the gate. MapController.RestartRun does not call MapController.StartNewMap, so LevelLoaderPatch/CustomLevelStatePatch's StartNewMap prefix - the only arming point - does not run. After the restart the log had no 'CustomLevelState: run starting' and no 'StartupCover:' line at all: no cover, no hold, no owed placement.

2. Even with the gate armed, the baseline map's spawn portal is the last writer. Probe samples on the restart path (22:41:16-22:41:19, fedora): two 'StartupCover: player placed at the level start (109.00, 36.08, -116.00)' lines landed and stuck - body (109.00, 38.00, -116.00), vel(0,0,0) - for about 1.8 s, then portal#-56858 with cached 'playerStart(120.00, 1.93, -3.00) desired(120.00, 1.93, 3.00)' switched to 'movePlayer=True' and its 1 s lerp walked the body (120.00, 1.93, -3.00) -> (120.00, 2.13, -1.80) -> (120.00, 2.13, -0.60) off the Warehouse, down onto the baseline 'CombinedCollisionMesh' whose surface is y=-20: body y=-18.08 (feet -20.00), about 121 units from the authored start and above the authored kill floor y=-35, which is exactly the reported stuck spot (108.3, -18.075, 5.73).

Because PortalClosed early-returns when the gate is not waiting, defect 1 also disabled the portal wait that keeps the placement from racing defect 2. Fix: arm the cover in DeathRestartPatch's RestartRun prefix, and subscribe SpawnPlayerPortal.A_PortalOpen so a portal that runs after the start landed re-owns the player and re-owes exactly one placement.

Third defect found only by live integration (the unit tests could not see it): StartupCover caches the point the hold follows (_holdPoint). After a harness teleport the cached point was stale, so the hold that keeps following dragged the teleported player back to the pre-teleport point and it fell through the still-rebuilding map (ac2-mid run 1: player at (120, 1.93, -3) instead of the teleport target). OnHarnessTeleported now clears _holdPoint as well as cancelling the owed placement.

A_PortalOpen is live, not inert: with a temporary log line in the handler it fired on the first boot (23:04:42.150) and on a stock restart (23:05:05.021), both before the placement line, so the re-ownership path is exercised by both entries into a run. The instrumentation was removed before the commit.

Verification on fedora (Windows depot, offline steamstub, final probe-free build, .env restored):

- AC#1: boot places once after the portal and the player is stable at (109, 38, -116). Stock 2nd, 3rd and 4th restarts of the same process each log exactly one 'StartupCover: held where the game put the player' -> 'LiveEdit: applied 1241 edit(s)' -> 'KillFloor: armed at y=-35 (authored, catch floor y=-80)' -> one 'player placed at the level start (109.00, 36.08, -116.00)', and rest on the Warehouse floor at (109, 29.75, -111.18/-111.42) for 10-22 consecutive 1 s state samples (floor ray hit y=29.19). Driven by run.py kill + run.py restart-run; spawns turned off again 2 s after the restart so nothing but the cover could move the player.
- AC#2: teleport to (105, 33, -112) on a settled restart logs 'DevHarness: teleport' then 'StartupCover: harness teleport kept' and nothing else; state stays (105, 29.75, -112) for 12 samples. Same verdict sending the teleport 3 s after restart-run, inside the cover window before the placement was due. A further stock restart after a teleport re-arms and places normally.
- AC#3: no 'KillFloor: player fell' and no repeat 'KillFloor: armed' anywhere in the session; placements never appear within a second of each other.
- AC#4: not one cover or kill-floor line before the first 'DevHarness: load-level' of a session (stock menu phase clean); boot sequence byte-identical to the pre-fix one. A harness screenshot taken about 1.2 s after restart-run shows the black cover with the Warehouse title, so the restart is covered end to end - the TASK-027.01 guarantees (no repeated correction, no baseline-map frame) hold on the new path too.

Tests: task mod:test 1756 passed (51 in StartupGateTests; 8 new cases for portal re-ownership, portal-never-closes give-up, and harness-teleport cancellation/pinning; 2 existing cases reworked to the new semantics). tests/test_run.py and tests/test_mcp_server.py cover the new restart-run CLI and MCP surface; tests/MegabonkLevels.Tests/harness_command_tests.cs covers the wire command. task lint clean.

task check reports 8 Python failures that are environmental and reproduce identically at HEAD in a clean worktree (/tmp/opencode/mb-head): 6 need the gitignored .tools/thps1/warehouse/warehouse.obj, 2 wineserver tests reach os.kill(7) and hit PermissionError on this box. None touch the files this task changed (the run.py diff is 4 unrelated lines).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
After a stock death-screen Retry into a custom level the player ended at body y=-18.08 on the baseline map's CombinedCollisionMesh, under the Warehouse floor and above the kill floor, because the run's startup cover never armed on that path and the baseline SpawnPlayerPortal's cached baseline-position animation was the last writer on the player's position.

Root cause (two defects, established with a temporary probe on the running game and then removed): MapController.RestartRun does not call MapController.StartNewMap, so the StartNewMap prefix that arms the gate never runs - no cover, no hold, no owed placement after a restart. Independently, even with the gate armed the portal's 1 s lerp from its cached playerStart (120.00, 1.93, -3.00) dragged the body off the authored start, which had stuck for about 1.8 s, and dropped it onto the baseline mesh at y=-20.

Changes: the RestartRun prefix in DeathRestartPatch now arms the cover; StartupGate gained a portal re-ownership rule (A_PortalOpen re-owns the player after the start landed and PortalClosed re-owes exactly one placement, with a timeout give-up so a portal that never closes cannot strand the run) and a harness-teleport rule (a deliberate teleport cancels the owed placement and pins the harness point through any pending portal animation); StartupCover drops its cached hold point on a harness teleport, which was pulling teleported players back into a rebuilding map; LiveEditPatch subscribes A_PortalOpen beside A_PortalClosed. New harness verb restart-run (run.py subcommand, MCP restart_run tool) drives MapController.RestartRun directly, so the stock restart path is testable without OS-level input on the Rewired menu.

Tests: 1756 C# tests pass, 51 of them in StartupGateTests (8 new, 2 reworked), plus the harness_command and Python CLI/MCP coverage for restart-run. Focused pytest green; task lint clean. task check still reports 8 Python failures that reproduce identically at HEAD in a clean worktree - 6 need the gitignored .tools/thps1/warehouse/warehouse.obj, 2 wineserver tests hit os.kill PermissionError on this box - none in files this task touched.

Verified on fedora: single placement per run on boot and on the 2nd, 3rd and 4th stock restarts of one process, with the player resting on the Warehouse floor at (109, 29.75, -111.18) for 10-22 s of 1 s state samples; no KillFloor re-arming and no fall-through loop; a harness teleport survives both on a settled restart and mid-cover-window (state holds the teleport point, no placement line follows); the stock menu phase logs nothing from the cover and the boot log sequence is unchanged; a screenshot 1.2 s into a restart shows the cover, so no baseline-map frame is exposed.

Risks / follow-ups: the cover now appears on the restart path where it previously did not, so a restart shows the black title screen for the ~2 s it takes to generate and place; if the portal's A_PortalClosed ever failed to fire, the cover releases at MEGABONK_STARTUP_TIMEOUT_SECONDS (default 8 s) and the run stays playable. PauseUi.Restart and ResetRunUi also reach RestartRun and were not exercised; they share the prefix, so they arm the cover the same way.
<!-- SECTION:FINAL_SUMMARY:END -->
