---
id: TASK-010.04
title: Research player teleport and level-up dismissal in the Il2Cpp build
status: To Do
assignee: []
created_date: '2026-10-22 03:43'
updated_date: '2026-10-22 04:08'
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

It is unconfirmed that REA's Ghidra provider produces usable pseudocode for this PE on macOS arm64 (REA documents Ghidra with PE files only on Windows x64). Your first step is to confirm it on `MyTime.Pause` (VA 0x1803E5B20, RVA 0x3E5B20) and record the outcome, including how long the first analysis took, in the "Using Ghidra through REA" section. If it does not work, say so with the error text, fall back to Binary Ninja or the Ghidra GUI project (`task ghidra:run`), and tell Lance.

Confirm every claim about game behaviour in the running game with a temporary harness command or log line, then remove the temporary code. Start from `uv run scripts/run.py relaunch`.

Deliverable: a new section in docs/development.md for each question with: the class and method names, field types, the RVAs, the exact call sequence that worked, what did not work and why, and side effects. Mark anything unconfirmed as an open question about itself (no task numbers). Also record the exact result fields TASK-010.05 should return (the position actually reached; the upgrade chosen and the dialog state before and after).

If either question cannot be answered, say so with the evidence of what was tried and stop; do not invent a workaround. Report to Lance and leave the question open in the docs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The outcome of opening GameAssembly.dll with REA's Ghidra provider and decompiling MyTime.Pause is recorded in docs/development.md (works or not, first-analysis duration, any error), with a fallback named if it does not work
- [ ] #2 docs/development.md records a teleport method for the player that was confirmed in the running game, with the classes, methods, field types, RVAs, call sequence, failed approaches and side effects on camera, enemies and kill floor
- [ ] #3 docs/development.md records how to detect an open level-up dialog and how to apply an upgrade choice, confirmed in the running game, with the classes, methods, RVAs and call sequence
- [ ] #4 The result fields TASK-010.05 should return for each command are recorded
- [ ] #5 Any temporary harness code or logging added for experiments is removed before finishing
- [ ] #6 A question that could not be answered is recorded as an open question with the evidence of what was tried, and Lance is told
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ghidra via REA, first attempt (Mac, 16 GB, 52 MB GameAssembly.dll, Ghidra 12.1.4): open_binary with provider_id ghidra succeeded and Ghidra's PE loader recognised x86:LE:64:windows, but the first analyze_function (VA 0x1803E5B20, MyTime.Pause) failed with provider_timeout after the default 330000 ms startup deadline, still analysing. The committed .claude/settings.json now sets REA_GHIDRA_STARTUP_TIMEOUT_MS=3600000 and GHIDRA_HEADLESS_MAXMEM=6G (default heap is 2G). Restart Claude Code, open_binary again with provider_id ghidra, and re-run the first query; the outcome and duration still have to be recorded in docs/development.md (acceptance criterion 1). If it still fails or takes impractically long, options are REA_GHIDRA_DISABLED_ANALYZERS, the Ghidra GUI project (task ghidra:run), or Binary Ninja.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
