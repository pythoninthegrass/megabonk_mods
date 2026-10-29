---
id: TASK-021.23
title: Start a grind on demand with the slide button instead of automatically
status: Done
assignee: []
created_date: '2026-10-29 03:41'
updated_date: '2026-10-29T22:38:00Z'
labels:
  - thps
  - mod
dependencies:
  - TASK-021.21
documentation:
  - docs/development.md
  - docs/thps-warehouse-layout.md
  - src/MegabonkLevels.Mod/rail_handoff_patch.cs
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
Gate shape. GrindGate (grind_gate.cs) holds the Unity-free decision, GrindGatePatch (grind_gate_patch.cs) prefixes both PlayerMovement.CanStartGrind (writes false) and PlayerMovement.StartRail (skips the call), both early-allowing while IsGrinding() so a grind in progress is never interrupted. RailHandoffPatch's StopRail postfix asks GrindGate.AllowsStart before starting the next rail, so a released button ends the chain at the joint. The two-hook question the plan left open is settled in game: every blocked line names the StartRail hook, so the game's Rail.FixedUpdate catch calls StartRail without consulting CanStartGrind. CanStartGrind stays patched as the catch-all for any caller that goes through it.

Input. GrindInput (grind_input.cs) is the mod's only Rewired touchpoint (Il2CppRewired_Core.dll referenced from MelonLoader/Il2CppAssemblies): ReInput.players.GetPlayer(0).GetButton("Slide"), fail-open with a one-time warning carrying ReInput.mapping.GetActionId("Slide"). Confirmed in game: grind-slide auto returns slideHeld false with no warning, so the action name resolves and a real device read works.

Harness. New grind-slide command with an optional boolean held field (absent hands the read back to the real device), returning {held, slideHeld}: run.py grind-slide <on|off|auto> and the MCP grind_slide(held?) tool. Needed because the harness injects editor input only, never Rewired input.

Level key. LevelFile.GrindRequiresSlide (JSON grindRequiresSlide, additive so schemaVersion stays 3), plumbed like KillFloorY through LevelLoaderPatch.PrepareRun into LiveEditPatch.SetPendingEdits, written back by the editor save and cleared on a vanilla generation. build_thps_level.py emits it and levels/thps.mblevel.json is regenerated.

Tests written first, all green: grind_gate_tests.cs (6), three GrindRequiresSlide cases in level_file_tests.cs, Level_RequiresTheSlideButtonToStartAGrind in thps_level_tests.cs, five grind-slide parse cases in harness_command_tests.cs (1277 C# tests), four cases in tests/test_run.py, three in tests/test_mcp_server.py, one in tests/test_build_thps_level.py. task check passes: mod build clean, 1277 mod tests, 502 python tests, markdownlint and ruff clean.

In-game check, THPS level, spawns off, invulnerable, harness holding the button. Released: 'GrindGate: slide released, grind start blocked at (140.0, 7.9, 8.6) by the StartRail hook.' on the main pipe north coping and '... at (160.0, 11.1, -27.1) ...' on the north wall tier, with the player standing on the lip normally (.tools/evidence/grind-gate-live-blocked.png). Held: 'GrindGate: slide held, grind started at (140.0, 7.9, 8.6) on the rail at (149.4, 5.4, 8.6).' with the player travelling to x 121, and '... at (160.0, 10.6, -27.1) on the rail at (159.2, 8.3, -27.1).' on the tier covering x 160 to 118.9 (grind-gate-tier-held.png). Chaining: held gives 'RailHandoff: moved onto rail at distance 0.00, progress 0.000, direction 1.0.' onto the west diagonal; released before the joint gives 'RailHandoff: slide released at progress 0.000, the grind is not carried onto the next rail.', the player dropped to (104.4, 1.24, 8.57) and the running grind left alone.

Control and save round trip. The same level with the key stripped (.tools/evidence/thps-no-gate-scratch.mblevel.json) grinds on contact as before: dropped at x 176 with the button on the real device the player rode the whole north coping to the floor at (88.6, 2.4, 0.5) with no GrindGate line (grind-gate-no-key-control.png). An editor save of the gated level (save-level) writes grindRequiresSlide back into the file.

Follow-up for a hand on the keyboard: an ollie off a lip, a grind from a run up a pipe, and chaining the west diagonal at real speed, none of which the harness can inject.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
What changed. On a level that opts in with the new level-file key grindRequiresSlide (levels/thps.mblevel.json, emitted by scripts/build_thps_level.py; additive, so schemaVersion stays 3), a rail touch starts a grind only while the game's slide button is held. GrindGate (grind_gate.cs) holds the Unity-free decision; GrindGatePatch (grind_gate_patch.cs) prefixes PlayerMovement.StartRail and PlayerMovement.CanStartGrind and refuses the start when the gate is in force and the button is released; GrindInput (grind_input.cs) reads ReInput.players.GetPlayer(0).GetButton("Slide") and reports it held if the read throws, so an unreachable Rewired keeps the game's behaviour instead of making grinding impossible. Both prefixes allow everything while IsGrinding() is true, so releasing the button mid-grind does not stop the grind in progress (the choice taken from the user: the button gates starting and chaining, not staying on). RailHandoffPatch's StopRail postfix asks the same question, so a released button ends a handoff chain at the joint. Levels without the key and vanilla runs keep the game's automatic grinding; the key round-trips through LiveEditPatch and the editor save.

Why. With a coping rail on every half pipe and wall quarter pipe lip, the game's own catch meant any ride over a lip caught the nearest rail at railSpeed, which is what made the Warehouse lips impossible to skate.

Verification. Tests first, then implementation: grind_gate_tests.cs (6), three GrindRequiresSlide cases in level_file_tests.cs, Level_RequiresTheSlideButtonToStartAGrind in thps_level_tests.cs, five grind-slide parse cases in harness_command_tests.cs (1277 C# tests passing), tests/test_run.py (4), tests/test_mcp_server.py (3), tests/test_build_thps_level.py (1). task check green: mod build clean, 1277 mod tests, 502 python tests, markdownlint and ruff clean. In game on the THPS level with spawns off and the harness holding the button: released, 'GrindGate: slide released, grind start blocked at (140.0, 7.9, 8.6) by the StartRail hook.' on the main pipe north coping and '... at (160.0, 11.1, -27.1) ...' on the north wall tier, with the skater standing on the lip normally; held, 'GrindGate: slide held, grind started at (140.0, 7.9, 8.6) on the rail at (149.4, 5.4, 8.6).' running to x 121, and the tier equivalent covering x 160 to 118.9, both with sparks; held across a joint, 'RailHandoff: moved onto rail at distance 0.00, progress 0.000, direction 1.0.' onto the west diagonal; released before the joint, 'RailHandoff: slide released at progress 0.000, the grind is not carried onto the next rail.', with the running grind left alone. Screenshots and the no-key control under .tools/evidence/ (grind-gate-live-blocked.png, grind-gate-tier-held.png, grind-gate-no-key-control.png): the same level with the key stripped still catches the coping on contact with no GrindGate line, from x 176 the length of the north coping to the floor. An editor save of the gated level writes grindRequiresSlide back. Every blocked line named the StartRail hook, which settles what the dump could not: the catch calls StartRail without consulting CanStartGrind, so that prefix is the catch-all rather than the working path.

Docs. docs/level-format.md gains the grindRequiresSlide row, docs/development.md a 'Grind gate' section plus the grind-slide command and MCP tool, docs/thps-warehouse-layout.md the opt-in in the level contents and a slide-gated bullet with the checked evidence (and the stale 'rail grinding is unconfirmed' risk corrected).

Risks and follow-ups. The harness cannot inject gameplay input, so three things still need a hand on the keyboard: an ollie off a lip, a grind from a run up a pipe, and chaining the west diagonal at real speed. The gate reads player 0's Slide action only; a second local player is out of scope. The keyboard read is confirmed (grind-slide auto returns the real device state with no warning); a gamepad read was not probed separately.
<!-- SECTION:FINAL_SUMMARY:END -->
