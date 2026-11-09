---
id: TASK-004.06.01
title: 'Dev harness: controlled nonlethal player damage for low-health testing'
status: Done
assignee:
  - Assistant
created_date: '2026-10-30T03:00:00Z'
updated_date: '2026-11-09 05:26'
labels:
  - dev-harness
  - testing
dependencies: []
references:
  - TASK-024
  - TASK-004.10
documentation:
  - docs/development.md
  - docs/music.md
parent_task_id: TASK-004.06
priority: medium
ordinal: 125000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The harness exposes kill and invulnerability but cannot apply controlled, nonlethal player damage. Testing low-health reactions currently requires waiting for enemies and risks losing the run. During runtime-music testing, the maintainer used a stone golem and confirmed that the audio slows dramatically as expected; danger modulation is working, not an outstanding audio defect. A repeatable damage control would make this and other damage-driven behavior testable without enemy timing. Changing HP alone is insufficient when reactions depend on damage history.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MCP and run.py expose a controlled player-damage command with an explicit requested amount.
- [x] #2 The command is nonlethal by default, preserving at least 1 HP and never silently ending the run.
- [x] #3 Damage exercises the game's normal damage-driven reactions rather than merely overwriting HP or forcing music pitch.
- [x] #4 Results report requested versus actual damage and before/after HP, max HP, shield and overheal; blocked or clamped damage is explicit.
- [x] #5 Invalid amounts and missing/dead players are rejected without unintended state changes; shield, invulnerability and damage-cooldown behavior is documented and tested.
- [x] #6 Pure validation and command parsing tests are written first; CLI/MCP coverage and docs/development.md describe usage and safety limits.
- [x] #7 In-game verification demonstrates controlled nonlethal damage and a low-health danger reaction on the default Wine setup; human audible confirmation is distinguished from source-state checks.
- [x] #8 Damage accepts any integer HP amount from 1 through 99, independently of an explicit nonlethal toggle; nonlethal defaults on and preserves at least 1 HP.
- [x] #9 Every harness damage hit bypasses shield in both nonlethal and lethal modes, leaves shield unchanged, and applies the nonlethal HP floor even while shield is present.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Write failing parser/safety-policy and CLI/MCP tests first for any integer 1–99 and separate default-on nonlethal flag.
2. Call PlayerHealth.DamagePlayerExternal with stock Enemy source, zero knockback, no attacker, and ignoreShield=true for every harness hit (user clarification supersedes original shield absorption). Retain native item checks, cooldown and damage reactions; do not write HP or pitch.
3. Cap final damage in a command-scoped CheckStopDamage postfix after item modifiers, using hp - 1 + floor(overheal), independent of shield. Fail closed if the guard is absent. Return requested/effective/actual damage, snapshots, ignoreShield, callbacks and blocked/clamped status.
4. Verify in default Wine: normal HP damage with full shield unchanged, both nonlethal modes, 1 HP floor, cooldown, missing/dead rejection, and natural low-health music source-state modulation. Distinguish human audible confirmation.
5. Update docs and help, run task check, record results, and commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User clarified all integers 1–99 HP are supported, not presets. Native Win64 inspection: DamagePlayerExternal RVA 0x427FD0 checks CanTakeDamage and constructs DamageContainer; Damage RVA 0x428220 runs CheckStopDamage then Retaliate, subtracts shield without spill or overheal then truncates HP, and invokes A_TakeDamage. CheckStopDamage RVA 0x427C20 can modify damage through Aegis/items, so nonlethal clamp must occur after it returns, before subtraction.

Red phase recorded: C# failed for missing Damage kind/args/policy; Python had 17 expected failures for missing command/builder/tool (526 existing tests passed). After implementation: 25 focused C# tests and all 543 Python tests pass; mod builds clean. First Wine verification: 37 damage applied exactly; 99 at 32 HP clamped to 31 leaving 1; subsequent hit at floor blocked with no damage event. Natural low-health source pitch dropped to 0.861 and currentDangerPitch to 0.76183856 after exiting editor; no heldPitch/heldCutoff. Found source string matters: custom DevHarness source bypasses normal Enemy cooldown/Mirror behavior. Switching to stock Enemy source (scope guard remains command-only) and re-verifying before documenting.

Final verification on default plain Wine, final deployed DLL: real MCP damage(amount=99) reported requested/submitted 99, effective/actual 69, HP 70→1, clamped=true, one actual A_TakeDamage event, cooldown false→true. Repeated frozen hit returned blocked=true, reason=damage-cooldown and identical HP. Advancing gameplay and freezing again allowed another hit. Shield verification: requested 99, actual 10, shield 10→0, HP 2→2, no spill and no safety clamp. Explicit nonlethal=false then reduced HP 3→0 and emitted a damage event; the next MCP call rejected dead player. Fresh relaunch(no_level=true) plus CLI damage 1 rejected absent player. Restored a fresh default example-forest run in editor mode after destructive checks.

Danger check on final build: after 70→1 hit and leaving editor, music-probe status reported sourcePitch=0.858, heldPitch=null, heldCutoff=null, lowpassCutoff=22000. MusicController.currentDangerPitch subsequently read 0.7612614. This verifies natural source-state modulation, not audible perception; no new human listening confirmation is claimed (prior golem listening is in the task description). Overheal/fractional floor behavior covered by native inspection and pure tests; no live overheal setup was manufactured.

task check passed: clean mod build, 1,392 C# tests, 555 Python tests, markdownlint and ruff. Ruff sorted the new test imports. Strict MCP tests first reproduced coercion of 1.0/true/string amounts, then passed with strict schema. git diff --check passed. Commit remains before closure.

Conventional implementation commit: adbe95c (feat(harness): add controlled 1–99 HP damage with nonlethal safety). All acceptance criteria and Definition of Done verified; closed.

Reopened on user request: shield absorption is no longer desired. Scope is harness damage only, not enemy damage elsewhere in the game.

Shield-bypass revision verified: failing test first demonstrated missing IgnoreShield policy. Native DamagePlayerExternal now always receives IgnoreShield=true; the nonlethal clamp no longer considers shield. Results expose ignoreShield=true; CLI/MCP help and development docs updated. task check passed again (1,392 C# tests, 555 Python tests, markdownlint and ruff).

Default Wine, rebuilt DLL relaunched, real MCP integration with full shield: damage 10 (nonlethal=true) reduced HP 70→60 while shield stayed 10; damage 3 (nonlethal=false) reduced HP 60→57 while shield stayed 10; damage 99 (nonlethal=true) clamped to 56, HP 57→1 while shield stayed 10. Every hit emitted one normal damage event and honored cooldown. Game left frozen in editor at 1/70 HP and 10 shield, with spawns off for safe testing.

Shield-bypass revision committed as 069d1d2 (fix(harness): bypass shield for all controlled damage). All criteria and Definition of Done verified again.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CLI/MCP damage accepts any integer 1–99 with an independent default-on nonlethal flag. All harness hits bypass shield and leave it unchanged, including lethal opt-out; ordinary enemy damage is untouched. Native reactions and cooldown are retained, with post-check nonlethal safety and detailed snapshots/results. task check passes (1,392 C#, 555 Python tests). Default Wine verification: full shield stayed 10 while HP changed 70→60 (10 damage), 60→57 (3 damage, nonlethal=false), and 57→1 (99 requested, clamped). Earlier checks verified dead/missing rejection and natural low-health pitch with no override; no human audible confirmation claimed. Shield-bypass correction committed as 069d1d2; initial implementation adbe95c. Game left in editor at 1 HP/10 shield, spawns off.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
