---
id: TASK-021.23
title: Start a grind on demand with the slide button instead of automatically
status: To Do
assignee: []
created_date: '2026-10-29 03:41'
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
- [ ] #1 With the slide button released, touching a coping rail does not start a grind and the player moves over it
- [ ] #2 With the slide button held on contact, the grind starts as it does today
- [ ] #3 A grind in progress chains to the next rail through RailHandoffPatch while slide is held and ends when it is released
- [ ] #4 Levels that do not opt in keep the game's automatic grinding
- [ ] #5 The gating logic is covered by tests written first, and the behaviour and any level-file key are documented in docs/level-format.md and docs/thps-warehouse-layout.md
- [ ] #6 Checked in game on the main half pipe lips and the north wall tier
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
