---
id: TASK-021.23
title: Start a grind on demand with the slide button instead of automatically
status: Done
assignee: []
created_date: '2026-10-29 03:41'
updated_date: '2026-10-29T23:05:00Z'
labels:
  - thps
  - mod
dependencies:
  - TASK-021.21
documentation:
  - docs/development.md
  - docs/thps-warehouse-layout.md
  - src/MegabonkLevels.Mod/rail_handoff_patch.cs
  - src/MegabonkLevels.Mod/grind_assist.cs
  - src/MegabonkLevels.Mod/grind_assist_watcher.cs
parent_task_id: TASK-021
priority: medium
ordinal: 114000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The game starts a rail grind automatically when the player touches a rail. With coping rails laid along every half pipe and wall quarter pipe lip (TASK-021.21), the player now catches a grind whenever they touch a lip, including when they only want to ride over it or ollie off it. The outcome is that a grind starts only while the player holds the slide button, so touching a lip without it passes over the rail, and holding it on contact begins the grind.

Context for a fresh implementer: the game's slide input is a Rewired action; confirm its name and whether it is already bound on keyboard and gamepad in the running game, since Rewired bindings live in serialized assets and are in neither the dump nor the code (see docs/development.md, "Reading the game's code"). The grind begins in the game's PlayerMovement rail logic (fields such as railSpeed and canJumpOffRailTime in .tools/il2cpp_dump/dump.cs, regenerate with task re:dump). RailHandoffPatch (src/MegabonkLevels.Mod/rail_handoff_patch.cs) already patches PlayerMovement.StopRail and starts rails itself for handoffs, so the gating must decide how a handoff behaves: a player already grinding and holding slide should chain, and one who released it should not. Decide whether the gate applies to every rail or only to levels that opt in through the level file, and keep Forest and other levels without the key on the game's behaviour. The harness injects no gameplay input, so the in-game check needs a manual run or a harness extension.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 With the slide button released, touching a coping rail does not start a grind and the player moves over it
- [x] #2 With the slide button held on contact, the grind starts as it does today
- [x] #3 A grind in progress chains to the next rail through RailHandoffPatch while slide is held and ends when it is released
- [x] #4 Levels that do not opt in keep the game's automatic grinding
- [x] #5 The gating logic is covered by tests written first, and the behaviour and any level-file key are documented in docs/level-format.md and docs/thps-warehouse-layout.md
- [x] #6 Checked in game on the main half pipe lips and the north wall tier
- [x] #7 Releasing the button mid-grind comes the player off the rail at once, and the catch keeps refusing them until it is pressed again
- [x] #8 While the button is held a rail within GrindAssist.CatchRadius of the player's feet is caught, so starting a grind does not depend on the game's own catch choosing that frame
- [x] #9 A player at the keyboard, with no harness override, can start a grind by holding the button and is dropped by releasing it
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
Agreed 2026-10-29 with the user after research. A grind starts only while the game's slide button is held, on levels that opt in; releasing it mid-grind does not stop a grind already in progress (the user chose this: the button gates starting and chaining, not staying on).

Research findings. PlayerMovement (dump.cs:328257) exposes public StartRail(Rail), StopRail(), IsGrinding() and CanStartGrind(); Rail (dump.cs:332650) has private FixedUpdate (RVA 0x49B960) with isRailingPlayer/stopRailTime/Cooldown, which is where the game's automatic catch lives. Rewired 1.1.35 is Image 1: ReInput.players.GetPlayer(int) (dump.cs:203156) and Player.GetButton(string) (dump.cs:199754), and a "Slide" string literal exists in stringliteral.json, so the action name is nearly certain but is confirmed at runtime by logging ReInput.mapping.Actions. Il2CppRewired_Core.dll is in MelonLoader/Il2CppAssemblies, so it can be referenced from the mod.

1. Tests first: tests/MegabonkLevels.Tests/grind_gate_tests.cs for the Unity-free decision (blocked without slide on an opted-in custom level, allowed with slide, allowed when not opted in, handoff chains only with slide), and level_file_tests.cs round-trip/absent/inequality for grindRequiresSlide.
2. src/MegabonkLevels.Mod/grind_gate.cs, Unity-free like rail_wall_end.cs: ShouldStart(customLevelActive, optIn, slideHeld) and ShouldChain(customLevelActive, optIn, slideHeld), plus the action name constant.
3. src/MegabonkLevels.Mod/grind_input.cs: the only Rewired touchpoint. GrindInput.IsSlideHeld() reads ReInput.players.GetPlayer(0).GetButton("Slide") inside a try/catch, logs the available action names once if the lookup throws, and honours a harness override so the gate can be driven without OS input.
4. src/MegabonkLevels.Mod/grind_gate_patch.cs, modelled on rail_wall_end_patch.cs: prefix on PlayerMovement.CanStartGrind returning false when gated (the clean path, the catch never calls StartRail), and a prefix on StartRail that skips a gated call as a catch-all if the catch ignores CanStartGrind. The log says which one blocked. RailHandoffPatch's StopRail postfix checks GrindGate.ShouldChain before starting the next rail, so a released button ends the chain at the joint.
5. Level file: LevelFile gains bool GrindRequiresSlide = false (additive, schemaVersion stays 3, camelCase grindRequiresSlide), threaded through LiveEditPatch.SetPendingEdits and the editor save round trip like KillFloorY, passed by LevelLoaderPatch.PrepareRun, and installed in megabonk_levels_mod.cs.
6. Harness: a grind-slide command (on/off/clear) in harness_command.cs and dev_harness.cs that arms the GrindInput override, with run.py and the MCP tool, so the gate's two branches are checkable without a keyboard.
7. scripts/build_thps_level.py emits grindRequiresSlide true and levels/thps.mblevel.json is regenerated; Python tests cover the key.
8. Verify in game: task mod:build, relaunch the THPS level, drop onto a main pipe coping rail with the override off (no grind, log shows the block) and on (grind caught); repeat on the north wall tier; load example-forest with the override off to show a level without the key still auto-grinds. The moving checks (skate up a lip, chain across the west diagonal tip, Forest baseline) need real keyboard input, so they are done with the user driving, as in TASK-021.25.
9. Docs: docs/level-format.md the new key, docs/thps-warehouse-layout.md the grind section and the checked-in-game evidence.

Risks. Whether the catch consults CanStartGrind is unconfirmed from the dump; both hooks are patched and the log names the one that fires. If Rail.FixedUpdate sets isRailingPlayer before calling StartRail, a blocked StartRail could leave the rail thinking it holds the player; if the log shows the StartRail path firing instead of CanStartGrind, the primary hook moves to a Rail.FixedUpdate skip prefix. Reading Rewired from an Il2Cpp mod is new to this repo: if ReInput is not reachable the gate reads held (never blocking) and the log says so, which keeps the game playable while it is sorted.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Gate shape. GrindGate (grind_gate.cs) holds one Unity-free rule, AllowsGrind(customLevelActive, levelOptsIn, slideHeld), asked in the three places grinding can happen: the catch, as Harmony prefixes on PlayerMovement.CanStartGrind (writes false) and PlayerMovement.StartRail (skips the call); the joint, in RailHandoffPatch's StopRail postfix before the next rail is started; and staying on the rail at all, as a postfix on PlayerMovement.RailMovement, the game's per-frame grind step, which calls StopRail the moment the button comes up. The two-hook question the plan left open is settled in game: every blocked line names the StartRail hook, so the game's Rail.FixedUpdate catch calls StartRail without consulting CanStartGrind. CanStartGrind stays patched as the catch-all for any caller that goes through it. The release stop is the game's own StopRail, with no dismount hop and no rail cooldown, so pressing the button again catches the same rail at once.

Decision reversed during play-test. The plan had the button gating starting and chaining only, with a grind already running never interrupted. Skating it on the keyboard on 2026-10-29 reversed that: released, the player has to come off the rail rather than ride on to the next junction, because a grind that keeps running after the release is the auto-grind this task set out to remove, only deferred to the joint. An intermediate attempt that ungated the handoff, so every StopRail re-latched the player to the nearest rail with nothing asking for the button, was reverted: it walked grinding back to the game's own behaviour.

Assist. Because the button now carries the intent, the start was made generous too. GrindAssist (grind_assist.cs) and GrindAssistWatcher (grind_assist_watcher.cs), ticked from the mod's OnUpdate, put a player holding the button and not on a rail onto the nearest rail whose collider comes within GrindAssist.CatchRadius (2 units) of their feet and is not on cooldown, via a radius-parameterised RailHandoff.PickNearest; the bar is refused if it is more than CatchRiseAboveFeet (1 unit) above the feet, which is a rail being passed under, and a catch landed within NearEndFraction (0.15) of either end is started running away from it by RailHandoff.DirectionForFreshCatch so it does not stop at once. A frozen run (MyTime.paused, which covers the editor) and a dead player are skipped, and none of it runs on a level without the key. The game's own catch reaches about the same 2 units (a blocked StartRail was logged from 1.6 units off the coping bar), so what the watcher adds is a check on every frame rather than reach.

Input. GrindInput (grind_input.cs) is the mod's only Rewired touchpoint (Il2CppRewired_Core.dll referenced from MelonLoader/Il2CppAssemblies): ReInput.players.GetPlayer(0).GetButton("Slide"), fail-open with a one-time warning carrying ReInput.mapping.GetActionId("Slide"). Confirmed on the real keyboard: holding the button starts a grind and letting go drops the player off the lip.

Harness. New grind-slide command with an optional boolean held field (absent hands the read back to the real device), returning {held, slideHeld}: run.py grind-slide <on|off|auto> and the MCP grind_slide(held?) tool. Needed because the harness injects editor input only, never Rewired input. An armed override outlives the test that set it, so a run left with the button forced released stops a real keyboard grinding at all, with no error anywhere, until grind-slide auto is sent; that cost one play-test and is now written into docs/development.md.

Level key. LevelFile.GrindRequiresSlide (JSON grindRequiresSlide, additive so schemaVersion stays 3), plumbed like KillFloorY through LevelLoaderPatch.PrepareRun into LiveEditPatch.SetPendingEdits, written back by the editor save and cleared on a vanilla generation. build_thps_level.py emits it and levels/thps.mblevel.json is regenerated.

Tests written first, all green: grind_gate_tests.cs (6 methods on the single AllowsGrind rule, the gate's scope and the fail-open read), grind_assist_tests.cs (9 methods on when the assist runs, the height band, the radius-parameterised pick and the fresh-catch direction), three GrindRequiresSlide cases in level_file_tests.cs, Level_RequiresTheSlideButtonToStartAGrind in thps_level_tests.cs, five grind-slide parse cases in harness_command_tests.cs (1298 C# tests), four cases in tests/test_run.py, three in tests/test_mcp_server.py, one in tests/test_build_thps_level.py. task check passes: 1298 mod tests, 502 python tests, markdownlint and ruff clean, mod build with no warnings.

In-game check, THPS level, spawns off, invulnerable, harness holding the button. Released, the catch is refused and the player stands on the lip: 'GrindGate: slide released, grind start blocked at (176.0, 7.9, 8.6) by the StartRail hook.' on the main pipe north coping, and the same on the north wall tier. Held, a real moving grind: 'GrindGate: slide held, grind started at (176.0, 7.9, 8.6) on the rail at (149.4, 5.4, 8.6).', then at the west diagonal joint 'RailHandoff: moved onto rail at distance 0.00, progress 0.000, direction 1.0.' and 'grind stopped at progress 1.000', ending on the floor at (88.6, 2.4, 0.5). Released mid-run, at once and mid-rail: 'RailHandoff: grind stopped at progress 0.397, atEnd=False.' then 'GrindGate: slide released, the grind ends at (112.2, 5.7, 6.6), progress 0.397.', with momentum carrying the player the rest of the way along the lip while the catch refused them ('... blocked at (102.5, 3.1, 4.1) by the StartRail hook.') until the button went down again half a second later, when that same rail was caught at once ('GrindGate: slide held, grind started at (102.5, 3.1, 4.1) on the rail at (110.0, 3.0, 6.1).'). The assist from a drop 1.6 units off that bar: 'GrindAssist: caught the rail at (149.4, 5.4, 8.6) from 0.00 units at (150.0, 9.4, 10.2), progress 0.510.' (0.00 because the feet point is inside the rail's thick collider).

Keyboard, user driving. Holding slide catches the coping and letting go drops Tony off the lip; with the relaxed start the user's verdict was that grinding initiated as it should. Control and save round trip: the same level with the key stripped (.tools/evidence/thps-no-gate-scratch.mblevel.json) grinds on contact as before, from x 176 the length of the north coping to the floor at (88.6, 2.4, 0.5) with no GrindGate line, and an editor save of the gated level writes grindRequiresSlide back into the file. Evidence under .tools/evidence/ (grind-gate-live-blocked.png, grind-gate-tier-held.png, grind-gate-no-key-control.png).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
What changed. On a level that opts in with the level-file key grindRequiresSlide (levels/thps.mblevel.json, emitted by scripts/build_thps_level.py; additive, so schemaVersion stays 3), the game's slide button is what grinding means, held rather than tapped. GrindGate (grind_gate.cs) holds the Unity-free rule, AllowsGrind(customLevelActive, levelOptsIn, slideHeld), and it is asked in the three places grinding can happen: the catch, as prefixes on PlayerMovement.StartRail and PlayerMovement.CanStartGrind, both refusing while the gate is in force and the button is released; the joint, in RailHandoffPatch's StopRail postfix; and staying on the rail, as a postfix on PlayerMovement.RailMovement that calls the game's StopRail the moment the button comes up, so a released button ends a grind where the player stands instead of leaving them riding to the next junction. That stop carries no dismount hop and no rail cooldown, so pressing again catches the same rail at once. Because the button now carries the intent, GrindAssist and GrindAssistWatcher (grind_assist.cs, grind_assist_watcher.cs) also catch a rail within 2 units of the player's feet on every frame the button is held, where the game's own catch decides for itself when to fire; GrindAssist.WithinBand keeps it off bars above the feet and RailHandoff.DirectionForFreshCatch keeps a catch near an end from stopping at once. GrindInput (grind_input.cs) reads ReInput.players.GetPlayer(0).GetButton("Slide") and reports it held if the read throws, so an unreachable Rewired keeps the game's behaviour. Levels without the key and vanilla runs keep the game's automatic grinding, and the key round-trips through LiveEditPatch and the editor save.

Why. With a coping rail on every half pipe and wall quarter pipe lip, the game's own catch meant any ride over a lip caught the nearest rail at railSpeed, which is what made the Warehouse lips impossible to skate. Gating the start alone was not enough: a grind that kept running after the player let go of the button was the same auto-grind deferred to the next joint, so the button gates the whole grind.

Correction to the record. The plan and the first pass had the button gating starting and chaining only, with a grind in progress never interrupted, on the user's choice at planning time. Play-test reversed it: the user asked for held to keep grinding going through junctions and released to come them off the rail. An intermediate attempt that re-latched the player to the nearest rail on every StopRail, with the handoff ungated, was reverted because it undid the gate.

Verification. Tests first, then implementation: grind_gate_tests.cs (6 methods), grind_assist_tests.cs (9 methods), three GrindRequiresSlide cases in level_file_tests.cs, Level_RequiresTheSlideButtonToStartAGrind in thps_level_tests.cs, five grind-slide parse cases in harness_command_tests.cs, four cases in tests/test_run.py, three in tests/test_mcp_server.py, one in tests/test_build_thps_level.py: 1298 C# and 502 python tests, task check green, mod build with no warnings. In game on the THPS level with spawns off and invulnerable: released, 'GrindGate: slide released, grind start blocked at (176.0, 7.9, 8.6) by the StartRail hook.' with the player standing on the lip; held, 'GrindGate: slide held, grind started at (176.0, 7.9, 8.6) on the rail at (149.4, 5.4, 8.6).' then 'RailHandoff: moved onto rail at distance 0.00, progress 0.000, direction 1.0.' onto the west diagonal and 'grind stopped at progress 1.000' on the floor at (88.6, 2.4, 0.5); released mid-run, 'GrindGate: slide released, the grind ends at (112.2, 5.7, 6.6), progress 0.397.' at once and mid-rail, refused on the way down and re-caught on the same rail half a second later on a fresh press; the assist, 'GrindAssist: caught the rail at (149.4, 5.4, 8.6) from 0.00 units at (150.0, 9.4, 10.2), progress 0.510.' from a drop 1.6 units off the bar. Same level with the key stripped, still grinding on contact with no GrindGate line. On the keyboard, holding slide catches the coping, letting go drops the player, and the relaxed start plays right. Screenshots under .tools/evidence/.

Docs. docs/level-format.md carries the grindRequiresSlide row including the hold semantics and the 2 unit catch; docs/development.md has the 'Grind gate' section with the three hooks, the assist and its constants, and the warning that an armed grind-slide override outlives the test that armed it; docs/thps-warehouse-layout.md has the slide-gated bullet with the log lines above.

Risks and follow-ups. CatchRadius (2 units) and CatchRiseAboveFeet (1 unit) are feel constants with no calibration behind them beyond one play-test; they are the knobs if initiation drifts. The gate reads player 0's Slide action only, so a second local player is out of scope, and a gamepad read was not probed separately. The assist runs on the mod's OnUpdate while the game's own catch runs in FixedUpdate; both call the same StartRail and neither saw a double-start in testing.
<!-- SECTION:FINAL_SUMMARY:END -->
