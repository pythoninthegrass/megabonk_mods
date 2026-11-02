---
id: TASK-021.27
title: Patch Calcium's fall damage to match Tony's on the Warehouse level
status: In Progress
assignee: []
created_date: '2026-11-02T04:38:00Z'
updated_date: '2026-11-02T04:52:00Z'
labels: []
dependencies: []
parent_task_id: TASK-021
priority: medium
type: bug
ordinal: 140000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Big airs are the point of the Warehouse (ollies off the half pipes, grinds off the apex edges), but the game's fall-damage rules can kill Calcium on landing from drops Tony walks away from — the skate-park fantasy ends in a death screen, which makes the level less fun. The difference is character data, not level design: fall damage lives in PlayerHealth (CanTakeFallDamage / OnPlayerLanded with minFallDamageSpeed / maxFallDamageSpeed, and an EStat.FallDamageReduction stat), so Calcium presumably lacks stat or threshold treatment Tony gets. Patch the mod so that on the Warehouse level Calcium takes fall damage like Tony. The worker confirms the actual per-character difference (stat vs thresholds vs hardcoded) in the dump and at runtime before choosing the patch point.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The symptom is reproduced first and recorded: on the Warehouse level the same drop kills Calcium while Tony survives
- [ ] #2 On the Warehouse level, Calcium and Tony take identical fall damage for the same drop
- [ ] #3 Calcium survives the biggest airs the level allows (half-pipe apex ollies, the hanging box, the starting-slope windows) without dying on landing
- [ ] #4 Outside the Warehouse level, Calcium's fall damage behaviour is unchanged from stock, and Tony's is unchanged everywhere
- [ ] #5 Verified in game: a max-height drop off the main half pipe as Calcium ends with him alive
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Where this runs

Verification host is `fedora` (tailscale only, `ssh fedora`): Fedora 42 GNOME Wayland, Windows Megabonk (depot 3405342) under Proton Experimental, game at `~/.local/share/Steam/steamapps/common/Megabonk`, prefix `~/.local/share/Steam/steamapps/compatdata/3405340/pfx`. MelonLoader 0.7.3 + `version.dll` + `Mods/MegabonkLevels.Mod.dll` and the `thps` pack + `thps.mblevel.json` are already installed there. Authoring stays on `mbp`: build the DLL, rsync the tracked-file set to fedora, scp the DLL into `Mods/`, relaunch through Steam. Docs: `docs/gamepadui.md` (session, prefix, portal screenshots, `run.py menu`), `docs/development.md` (harness).

## Findings from the dump so far

- Fall damage inputs live in `PlayerHealth` (`.ctor(PlayerStatsNew)`): private `minFallDamageSpeed`/`maxFallDamageSpeed`, private `OnPlayerLanded(float speed)`, `fallDamageSource = "fallDamage"`, `DamagePlayerExternal(damage, knockback, dir, ignoreShield, damageSource, ...)`.
- The landing trigger is in `PlayerMovement`: `CheckLanding(point, normal)`, `CanTakeFallDamage(Vector3 normal)`, `CheckFallDamageBug()`, `fallSpeed`, `public static Action<float> A_Landed`.
- Per-character data is `CharacterData` (`DataManager.GetCharacterData(ECharacter)`): `List<StatModifier> statModifiers`, `PassiveData passive`, `GameObject prefab`, `WeaponData weapon`. `EStat.FallDamageReduction = 27`, `ECharacter.Calcium = 1`, `ECharacter.TonyMcZoom = 13`.
- `PlayerInventory` (public fields) reaches everything the patch needs at run time: `playerStats`, `characterData`, `playerHealth`. `PlayerStatsNew` has public `Dictionary<EStat,float> stats`/`rawStats`, `GetStat(EStat)`, `ForceUpdateStats()`.
- Consequence: the mod can read the live numbers for both characters without native disassembly. Decide the patch point from measured values, not from the ctor's native body.

## Steps

1. **Instrument first (needed for AC #1/#2/#5 anyway).** Add a dev-harness readout that reports, for the current run: `eCharacter`, `hp`/`maxHp`/`shield`, `minFallDamageSpeed`/`maxFallDamageSpeed`, `fallDamageTakenAtTime`, `stats[FallDamageReduction]`, `stats[MaxHealth]`, `stats[DamageReductionMultiplier]`, the character's own `statModifiers`, plus `PlayerMovement.grounded`/`fallSpeed`. Private fields through `AccessTools`. Wire it as a `fall-damage` command in `dev_harness.cs` + `run.py` + `scripts/mcp_server.py`, following the `grind-slide` command's shape.
2. **Reproduce (AC #1).** On fedora: harness enabled, `MEGABONK_DEV=true`, load `levels/thps.mblevel.json`, spawns off, vulnerable. For each of calcium and tony: `freeze` -> `teleport` to the main half-pipe apex height -> `resume` -> read hp at impact. Record both numbers in the task. If Calcium does not actually die, that is a finding, not a blocker - report it and re-scope with Lance before patching.
3. **Decide the patch point from the measured delta** (stat only / thresholds only / both), then implement in the established shape:
   - `fall_damage_policy.cs`: pure, unit-testable - decides whether the override applies (custom run + level opted in + current character != reference) and which values the landing call should see.
   - `fall_damage_patch.cs`: Harmony prefix/postfix on `PlayerHealth.OnPlayerLanded` that puts the reference character's fall-damage inputs in place for the duration of that one call and restores them after, so nothing else in the run (shop UI, stat UI, other damage) sees the swap.
   - Level-file field `fallDamageCharacter` (string, one of calcium/tony/tonymczoom): `LevelFile` record, `LevelSettings.Fields` + `Validate` + `CopyTo`, `LiveEditPatch` pending/settings plumbing next to `_grindRequiresSlide`, editor save writes it back.
   - `scripts/build_thps_level.py` sets `fallDamageCharacter: "tony"` for the Warehouse; regenerate `levels/thps.mblevel.json` and re-run the preservation check.
4. **Tests before the implementation of the pure logic** (`tests/MegabonkLevels.Tests/fall_damage_policy_tests.cs` via `task mod:test`), plus the Python level-build test for the new field.
5. **Verify in game (AC #2/#3/#4/#5)** on fedora: identical damage for the same drop as Calcium vs Tony; the biggest airs (half-pipe apex ollie, hanging box, starting-slope windows) survivable as Calcium; a stock non-Warehouse run as Calcium unchanged; Tony unchanged everywhere. Screenshot evidence per docs.
6. **Docs** (`docs/level-format.md` field row, `docs/development.md` harness command + the measured per-character numbers) and a conventional commit with no attribution.

## Risks / open questions

- The difference may be HP rather than damage: Calcium may simply have less health, in which case "identical fall damage" (AC #2) can be satisfied while "survives the biggest airs" (AC #3) still fails. That is a scope question for Lance, not something to silently widen.
- Whether `OnPlayerLanded` reads `FallDamageReduction` through `PlayerStatsNew.GetStat` (likely) or caches it; the measured values plus a one-line in-call probe settle it before the patch is written.
- Enabling the file-based dev harness on fedora is a documented dev workflow (`run.py enable`), not the player-package path; it is left enabled only for this work.
<!-- SECTION:PLAN:END -->
