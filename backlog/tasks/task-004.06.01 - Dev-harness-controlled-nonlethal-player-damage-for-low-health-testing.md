---
id: TASK-004.06.01
title: 'Dev harness: controlled nonlethal player damage for low-health testing'
status: In Progress
assignee:
  - Assistant
created_date: '2026-10-30T03:00:00Z'
updated_date: '2026-10-30T16:09:00Z'
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
type: enhancement
ordinal: 125000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The harness exposes kill and invulnerability but cannot apply controlled, nonlethal player damage. Testing low-health reactions currently requires waiting for enemies and risks losing the run. During runtime-music testing, Lance used a stone golem and confirmed that the audio slows dramatically as expected; danger modulation is working, not an outstanding audio defect. A repeatable damage control would make this and other damage-driven behavior testable without enemy timing. Changing HP alone is insufficient when reactions depend on damage history.
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
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Write failing C# parser/safety-policy tests and Python CLI/MCP tests first for amounts 1–99 and separate default-on nonlethal flag.
2. Add damage command to wire parser, run.py and MCP. Call PlayerHealth.DamagePlayerExternal with normal shield/item/cooldown behavior, no HP writes or pitch overrides. Native inspection confirms shield absorbs the entire hit without spill; overheal spills into integer HP. A command-scoped CheckStopDamage postfix will cap final damage after item modifiers, preserving 1 HP before native subtraction.
3. Return before/after hp/maxHp/shield/overheal, requested/submitted/actual damage and explicit blocked/clamped outcomes. Reject missing/dead players and invalid input without mutation.
4. Build/deploy, relaunch default Wine setup, verify ordinary damage, nonlethal floor, blocked invulnerability/cooldown, invalid/dead cases, and low-health music source state. Distinguish source-state checks from human audible confirmation.
5. Document command and native safety semantics; run task check and record evidence/remaining limitations before finalization.

Final runtime refinement: use the stock Enemy source so native cooldowns and danger history are retained. Mirror still does not stop this attacker-less external hit; verified and documented rather than bypassing or modifying invulnerability. The nonlethal guard fails closed when its Harmony postfix is missing. MCP uses strict integer/boolean validation to reject coercion before command files are sent.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User clarified all integers 1–99 HP are supported, not presets. Native Win64 inspection: DamagePlayerExternal RVA 0x427FD0 checks CanTakeDamage and constructs DamageContainer; Damage RVA 0x428220 runs CheckStopDamage then Retaliate, subtracts shield without spill or overheal then truncates HP, and invokes A_TakeDamage. CheckStopDamage RVA 0x427C20 can modify damage through Aegis/items, so nonlethal clamp must occur after it returns, before subtraction.

Red phase recorded: C# failed for missing Damage kind/args/policy; Python had 17 expected failures for missing command/builder/tool (526 existing tests passed). After implementation: 25 focused C# tests and all 543 Python tests pass; mod builds clean. First Wine verification: 37 damage applied exactly; 99 at 32 HP clamped to 31 leaving 1; subsequent hit at floor blocked with no damage event. Natural low-health source pitch dropped to 0.861 and currentDangerPitch to 0.76183856 after exiting editor; no heldPitch/heldCutoff. Found source string matters: custom DevHarness source bypasses normal Enemy cooldown/Mirror behavior. Switching to stock Enemy source (scope guard remains command-only) and re-verifying before documenting.

Final verification on default plain Wine, final deployed DLL: real MCP damage(amount=99) reported requested/submitted 99, effective/actual 69, HP 70→1, clamped=true, one actual A_TakeDamage event, cooldown false→true. Repeated frozen hit returned blocked=true, reason=damage-cooldown and identical HP. Advancing gameplay and freezing again allowed another hit. Shield verification: requested 99, actual 10, shield 10→0, HP 2→2, no spill and no safety clamp. Explicit nonlethal=false then reduced HP 3→0 and emitted a damage event; the next MCP call rejected dead player. Fresh relaunch(no_level=true) plus CLI damage 1 rejected absent player. Restored a fresh default example-forest run in editor mode after destructive checks.

Danger check on final build: after 70→1 hit and leaving editor, music-probe status reported sourcePitch=0.858, heldPitch=null, heldCutoff=null, lowpassCutoff=22000. MusicController.currentDangerPitch subsequently read 0.7612614. This verifies natural source-state modulation, not audible perception; no new human listening confirmation is claimed (prior golem listening is in the task description). Overheal/fractional floor behavior covered by native inspection and pure tests; no live overheal setup was manufactured.

task check passed: clean mod build, 1,392 C# tests, 555 Python tests, markdownlint and ruff. Ruff sorted the new test imports. Strict MCP tests first reproduced coercion of 1.0/true/string amounts, then passed with strict schema. git diff --check passed. Commit remains before closure.
<!-- SECTION:NOTES:END -->
