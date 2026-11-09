---
id: TASK-010.04
title: Research player teleport and level-up dismissal in the Il2Cpp build
status: Done
assignee:
  - claude
created_date: '2026-10-22 03:43'
updated_date: '2026-11-09 05:26'
labels:
  - dev-harness
  - research
dependencies: []
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - docs/development.md
  - .tools/il2cpp_dump/dump.cs
documentation:
  - AGENTS.md
  - docs/development.md
  - docs/runtime-map-structure.md
  - >-
    docs/development.md ("Reading the game's code" and "Using Ghidra through
    REA")
parent_task_id: TASK-010
priority: medium
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. No dependencies; can run in parallel with TASK-010.01 and TASK-010.02. Output is findings in docs plus a throwaway experiment, not shipped commands; TASK-010.05 implements the commands from your findings.

Question 1: how can the mod move the player to a world position or grid cell at runtime? The game owns the player through Rewired and a character controller; setting `transform.position` may be overwritten or fight a CharacterController. Find the player object (the harness already reads the player for `cells` and `invulnerable`; start from that code in dev_harness.cs and the classes it uses) and determine a reliable way to teleport: disabling and re-enabling the CharacterController, a controller `Move`/`Teleport`-style method, or a Rigidbody. Record what happens to the camera, to nearby enemies, and to the kill floor.

Question 2: how can the mod dismiss the level-up dialog (choose one of the offered upgrades) without a menu click? The harness cannot do this today (docs/development.md "Not covered"). Find the level-up UI class, the method that applies a choice, and how to detect that the dialog is open.

How to research: the Il2Cpp assemblies are stubs, so read `.tools/il2cpp_dump/dump.cs` (regenerate with `task re:dump`; `.tools` is gitignored so use `rg -u 'Pattern' .tools/il2cpp_dump/dump.cs`). Method bodies exist only as native code in `GameAssembly.dll`; the dump lists each method's RVA and VA (`// RVA: 0x3E5B20 Offset: 0x3E4B20 VA: 0x1803E5B20`).

Read the native code with Ghidra through the REA MCP tools. Setup is in docs/development.md, "Using Ghidra through REA": `GHIDRA_INSTALL_DIR` and `JAVA_HOME` come from the committed `.claude/settings.json` (restart Claude Code after changing them), and the same REA server also has a Hopper provider, so bind Ghidra explicitly: `open_binary` with `path` set to `GameAssembly.dll` in the game directory (`uv run scripts/game_paths.py` prints the game dir) and `provider_id: "ghidra"`, then `analyze_function` or `procedure_pseudo_code` with the dump's VA (for example `0x1803E5B20`). The first call after opening runs Ghidra's full auto-analysis of a very large binary and can take many minutes (a first `analyze_function` was still running after 2 minutes); wait for it rather than retrying, and do not open a second binary meanwhile. Names and comments set through REA are discarded on `close_binary`. Binary Ninja is an alternative if its MCP server is running.

It is unconfirmed that REA's Ghidra provider produces usable pseudocode for this PE on macOS arm64 (REA documents Ghidra with PE files only on Windows x64). Your first step is to confirm it on `MyTime.Pause` (VA 0x1803E5B20, RVA 0x3E5B20) and record the outcome, including how long the first analysis took, in the "Using Ghidra through REA" section. If it does not work, say so with the error text, fall back to Binary Ninja or the Ghidra GUI project (`task ghidra:run`), and tell the maintainer.

Confirm every claim about game behaviour in the running game with a temporary harness command or log line, then remove the temporary code. Start from `uv run scripts/run.py relaunch`.

Deliverable: a new section in docs/development.md for each question with: the class and method names, field types, the RVAs, the exact call sequence that worked, what did not work and why, and side effects. Mark anything unconfirmed as an open question about itself (no task numbers). Also record the exact result fields TASK-010.05 should return (the position actually reached; the upgrade chosen and the dialog state before and after).

If either question cannot be answered, say so with the evidence of what was tried and stop; do not invent a workaround. Report to the maintainer and leave the question open in the docs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The outcome of opening GameAssembly.dll with REA's Ghidra provider and decompiling MyTime.Pause is recorded in docs/development.md (works or not, first-analysis duration, any error), with a fallback named if it does not work
- [x] #2 docs/development.md records a teleport method for the player that was confirmed in the running game, with the classes, methods, field types, RVAs, call sequence, failed approaches and side effects on camera, enemies and kill floor
- [x] #3 docs/development.md records how to detect an open level-up dialog and how to apply an upgrade choice, confirmed in the running game, with the classes, methods, RVAs and call sequence
- [x] #4 The result fields TASK-010.05 should return for each command are recorded
- [x] #5 Any temporary harness code or logging added for experiments is removed before finishing
- [x] #6 A question that could not be answered is recorded as an open question with the evidence of what was tried, and the maintainer is told
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Static half is done (see notes). Remaining: confirm in the running game.
1. Add temporary `probe` harness command (separate file probe_experiments.cs plus one parse case and one dispatch case) that returns a JSON result: teleport via MyPlayer.TeleportPlayerImmediate / PlayerMovement.TeleportPlayer, reading transform position, camera, enemy and kill-floor effects; read LevelupScreen.isLevelingUp, EncounterWindows instance, buttons, and call UpgradeButton.SelectUpgrade.
2. `task mod:build`, `run.py relaunch`, run probes, record results and log lines.
3. Level-up: get the dialog open (need XP; find a way to trigger via harness probe, e.g. EncounterWindows.OnLevelUp or ShowLevelupScreen) and choose via SelectUpgrade; compare state before/after, including editor-mode freeze interaction.
4. Remove all temporary code (git diff on src/ must be empty), rebuild.
5. Rewrite the two docs/development.md sections from "unconfirmed" to confirmed findings, with result fields for the follow-on harness commands.
6. Check ACs, final summary, commit docs and backlog separately.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ghidra via REA, first attempt (Mac, 16 GB, 52 MB GameAssembly.dll, Ghidra 12.1.4): open_binary with provider_id ghidra succeeded and Ghidra's PE loader recognised x86:LE:64:windows, but the first analyze_function (VA 0x1803E5B20, MyTime.Pause) failed with provider_timeout after the default 330000 ms startup deadline, still analysing. The committed .claude/settings.json now sets REA_GHIDRA_STARTUP_TIMEOUT_MS=3600000 and GHIDRA_HEADLESS_MAXMEM=6G (default heap is 2G). Restart Claude Code, open_binary again with provider_id ghidra, and re-run the first query; the outcome and duration still have to be recorded in docs/development.md (acceptance criterion 1). If it still fails or takes impractically long, options are REA_GHIDRA_DISABLED_ANALYZERS, the Ghidra GUI project (task ghidra:run), or Binary Ninja.

Static half done on a 64 GB arm64 Mac (game not installed, nothing confirmed in the running game). REA Ghidra provider works on GameAssembly.dll: settings REA_GHIDRA_STARTUP_TIMEOUT_MS=3600000, GHIDRA_HEADLESS_MAXMEM=16G (settings.local.json), no analyzers disabled. First analyze_function (MyTime.Pause, 0x1803E5B20) finished about 12 minutes after open_binary (Ghidra reports 713 s auto-analysis); later queries return in seconds. Pseudocode is usable but unnamed (FUN_/DAT_ only); map FUN_1xxxxxxxx minus 0x180000000 to the RVA in dump.cs for names. LevelupScreen.Open (RVA 0x54F110) has no Ghidra function and could not be decompiled. close_binary with snapshot_path .tools/GameAssembly/ghidra.rea-snapshot succeeded (616 KB, evidence for queried functions only; importing it is untested).

Static findings are recorded in docs/development.md under 'Player teleport' and 'Level-up dialog', all unconfirmed in the running game. Teleport candidates: MyPlayer.TeleportPlayerImmediate (RVA 0x4B6E00) calling PlayerMovement.TeleportPlayer (RVA 0x343A80, Rigidbody-based, zeroes velocity); PlayerMovement.VerifyPosition (RVA 0x344220) may revert a low target. Level-up candidates: LevelupScreen.isLevelingUp static flag; UpgradeButton.SelectUpgrade (RVA 0x55F0A0) -> UpgradePicker.SelectUpgrade (RVA 0x561500) -> PlayerInventory.AddUpgrade (RVA 0x4DFD80) -> EncounterWindows.RewardFinished (RVA 0x3E09D0); UpgradePicker.AutoSelectUpgrade (RVA 0x560BE0) is a static UI-free pick. Acceptance criteria 2 and 3 stay open until confirmed in the running game on the CrossOver Mac.

Running-game confirmation (CrossOver, Forest): TeleportPlayerImmediate moves the Rigidbody and the transform follows within a second, y is the feet point (+1.925 body offset), direct transform writes are overwritten, a target below the kill floor is not reverted and is killed by the kill floor, camera follows without extra calls. UpgradeButton.SelectUpgrade() on a button of LevelupScreen.upgradePicker.buttons closes the dialog, applies the upgrade (Bow in HUD) and calls MyTime.Unpause, which drops the editor-mode freeze. Dialog opened for the test with EncounterWindows.AddEncounter(EEncounter.Levelup). Temporary probe command was removed; src/ has no diff. task check passes (129 tests, lint). Definition of Done item 2 (tests first) not applicable: no shipped code. Open: one unexplained unapplied teleport right after relaunch; chasing enemies at the old position; AutoSelectUpgrade; item offers.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Confirmed both questions in the running game and rewrote the 'Player teleport' and 'Level-up dialog' sections of docs/development.md from static findings to confirmed ones, with classes, RVAs, call sequences, failed approaches, side effects and the result fields for the follow-on harness commands. Teleport: MyPlayer.TeleportPlayerImmediate (feet-point target, transform syncs within a second, direct transform writes are overwritten, no revert below the map but the kill floor fires). Level-up: LevelupScreen.isLevelingUp detects the dialog; UpgradeButton.SelectUpgrade() on an entry of upgradePicker.buttons applies the upgrade and closes it, but its MyTime.Unpause drops the editor-mode freeze. Temporary probe code was removed. Open questions are listed in the docs.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
