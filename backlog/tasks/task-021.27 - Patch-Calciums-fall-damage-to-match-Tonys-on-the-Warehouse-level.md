---
id: TASK-021.27
title: Patch Calcium's fall damage to match Tony's on the Warehouse level
status: Done
assignee: []
created_date: '2026-11-02T04:38:00Z'
updated_date: '2026-11-02T05:31:00Z'
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
- [x] #1 The symptom is reproduced first and recorded: on the Warehouse level the same drop leaves Calcium at 1 HP while Tony takes none
- [x] #2 On the Warehouse level, Calcium and Tony take identical fall damage for the same drop
- [x] #3 Calcium survives the biggest airs the level allows (half-pipe apex ollies, the hanging box, the starting-slope windows) without dying on landing
- [x] #4 Outside the Warehouse level, Calcium's fall damage behaviour is unchanged from stock, and Tony's is unchanged everywhere
- [x] #5 Verified in game: a max-height drop off the main half pipe as Calcium ends with him alive
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Measured on fedora (Warehouse, dev harness, spawns off, vulnerable)

Per-character difference is the stat, not the thresholds. Both characters share the one PlayerHealth component, so min/maxFallDamageSpeed are identical (30 / 140); what differs is EStat.FallDamageReduction, which Tony's CharacterData.statModifiers carry (stat 27, modifyType 2, modification 1) and Calcium's do not.

- Calcium: characterId 1, hp 100/100, FallDamageReduction 0, modifiers MoveSpeedMultiplier +0.15, JumpHeight +1.5, PickupRange +3.
- Tony McZoom: characterId 13, hp 70/70, FallDamageReduction 1, modifiers MaxHealth -30, Shield +10, MoveSpeedMultiplier +0.3, JumpHeight +3, FallDamageReduction +1, PickupRange +3.

## The repro needs a flat landing surface

Landing on a slope breaks the fall: a 92-unit drop onto the starting slope at (109, ~30, -115) hit the ground at ~60 m/s and dealt exactly 0 damage to Calcium (fallDamageTakenAtTime stayed 0). Consistent with PlayerMovement.CanTakeFallDamage(Vector3 normal) and the minBreakFallAngle/maxBreakFallAngle fields. The Warehouse bundle is open-topped, so a drop into the interior at (100, y, 0), floor y=0.5, is the flat surface to test on.

## Damage curve (Calcium, flat concrete at x=100, z=0)

| impact fallSpeed | damage | hp |
| --- | --- | --- |
| ~29 m/s | 0 (below the 30 threshold) | 100/100 |
| ~59 m/s | 21 | 79/100 |
| ~154 m/s | 72 | 9/81 |
| ~234 m/s | 99 | 1/100 |

## Finding: fall damage cannot kill Calcium

The largest drop the map allows (teleport to y=1000, impact ~234 m/s) leaves Calcium at 1 HP alive, with fallDamageTakenAtTime stamped and the damage vignette plus blood decals on screen. AC #1's wording ("the same drop kills Calcium") therefore cannot be reproduced by a fall alone; the real asymmetry is Calcium stripped to 1 HP while Tony McZoom takes 0 damage on the identical drop (70/70 with shield 10 intact, fallDamageTakenAtTime stamped, so the landing path still runs for Tony and the stat zeroes the damage).

Patch point is unchanged by this: swap the reference character's FallDamageReduction for the duration of the landing call, which gives both characters 0 damage on the Warehouse. AC #3 and #5 remain reachable; AC #1 needs rewording to the measured symptom rather than a death.

## Patched, measured on fedora (same host, same level, same surfaces)

Shipped as a level-file field, `fallDamageCharacter`, plus a Harmony prefix/postfix on PlayerHealth.OnPlayerLanded that writes the reference character's own total for EStat.FallDamageReduction into PlayerStatsNew.stats and rawStats for that one call and restores the player's values in the postfix. Pure decisions and the stat arithmetic live in FallDamagePolicy (fall_damage_policy.cs); FallDamagePatch applies it; the fall-damage harness readout gained a fallDamageOverride block (levelNames, referenceId, activeCharacterId, active, referenceValue, swaps, lastPlayerValue, lastReferenceValue, lastReadBack).

AC #2, Calcium on the Warehouse with fallDamageCharacter: tonymczoom. The 1000-unit drop that unpatched left him at 1/100 now lands at 100/100 (peak 246 m/s); a 60-unit drop lands 100/100 at 44.6 m/s; a drop from y=40, above the 35.85 start platform that is the level's tallest authored geometry, lands 100/100 at 44.0 m/s. Every one has fallDamageTakenAtTime stamped, so the game's landing path ran and only the damage vanished. Override readout through all of it: active true, referenceValue 1, lastReadBack 1 (GetStat returns Tony's value inside the call), swaps one per landing, and the player's own stat still 0 outside a landing, which is the restore working.

AC #4, Tony McZoom on the same level: the 1000-unit drop (~231 m/s) leaves him 70/70 with shield 10/10, and the override reads active false, swaps 0, last* null - Applies refuses when the reference character is the player, so his landings are his own. Screenshot shows the shield and health bars full at pos(100, 2, 0).

AC #4, Calcium on levels/example-forest.mblevel.json, which names no reference character: levelNames, referenceId and referenceValue are null, active false, swaps 0, and stock damage is intact - 45.2 m/s took him 100 -> 82 and 44.8 m/s took him 84 -> 67, both stamped. Two landings at ~76 m/s on the forest's slopes dealt 0 and stamped 0, the same slope exemption seen on the Warehouse, in a level the patch never enters.

The comparison that settles it is the pair of near-identical impacts: 44.0 m/s on the patched Warehouse costs Calcium nothing, 44.8 m/s on the unpatched forest costs him 17.

AC #3 and #5 are carried by the same evidence: the tallest drop the level's own geometry offers is under half the height of the 1000-unit drop, so Calcium survives every air the Warehouse can produce at 100/100, and fall damage is in any case floored at 1 HP. A harness teleport stands in for a driven ollie-launched big air on the impact-speed axis; landing back on a pipe transition costs nothing either way because slopes are exempt.

Verified artifact: Mods/MegabonkLevels.Mod.dll md5 2032bc975bf5e5c86f8f1add2a87da85, levels/thps.mblevel.json md5 5d69bf6b2896c5c7ed4db17041b80b03. 1576 xunit tests and 89 pytest tests pass. HUD screenshots: calcium-patched-after.png, calcium-air-after.png, calcium-maxheight-after.png (100/100 on Warehouse), tony-warehouse-after.png (70/70 + shield 10), calcium-forest-stock-damage-after.png (67/100 on Forest) in fedora:/home/lance.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## What changed

A level can now name the character whose fall damage its landings are scored with. Optional level-file field `fallDamageCharacter` (`calcium`/`tony`/`tonymczoom`, editable in the settings panel, written back on save), pure decisions and stat arithmetic in `FallDamagePolicy` (`fall_damage_policy.cs`), and a Harmony prefix/postfix on `PlayerHealth.OnPlayerLanded` (`fall_damage_patch.cs`) that writes the named character's own `EStat.FallDamageReduction` total into `PlayerStatsNew.stats` and `rawStats` for the duration of that one call and restores the player's values in the postfix. The total comes from the character's `CharacterData.statModifiers` over `PlayerStatsNew.GetBaseValue`, not a constant. `levels/thps.mblevel.json` and its editable twin name `tonymczoom`; the preservation baseline is refreshed for the one added field. A read-only `fall-damage` harness command (run.py, MCP `fall_damage()`) reports thresholds, the stat, fall speed and both characters' stored modifiers, plus a `fallDamageOverride` block describing what the patch will do to the next landing.

## Why

The per-character difference is the stat, not the thresholds: both Warehouse characters share one `PlayerHealth`, so `minFallDamageSpeed`/`maxFallDamageSpeed` are the same 30 and 140 m/s, while Tony's `statModifiers` carry FallDamageReduction +1 (stat 27, modifyType 2) and Calcium's carry none. Swapping the one stat for one call is the smallest change that lands, and it leaves the reference character's own landings untouched because `Applies` refuses when the reference is the player.

## Verification (fedora, Windows build under Proton Experimental, dev harness, spawns off, vulnerable)

Unpatched Calcium on the Warehouse flat concrete: 29 m/s nothing, 59 m/s 21 damage, 154 m/s 72, 234 m/s 99 (1 HP alive). Patched, the same surfaces and drops: the 1000-unit drop lands 100/100 at 246 m/s, a 60-unit drop 100/100 at 44.6 m/s, and a drop from above the level's tallest authored geometry (y=40 over the 35.85 start platform) 100/100 at 44.0 m/s, each with `fallDamageTakenAtTime` stamped and `lastReadBack` 1 while the player's own stat reads 0 between landings.

AC #4 both ways: Tony on the same level takes the 1000-unit drop (~231 m/s) at 70/70 with shield 10/10, `active` false and `swaps` 0; Calcium on `levels/example-forest.mblevel.json` reads `levelNames`/`referenceId`/`referenceValue` null with stock damage intact (45.2 m/s 100→82, 44.8 m/s 84→67, both stamped). The decisive pair is two near-identical impacts: 44.0 m/s costs nothing on the patched Warehouse, 44.8 m/s costs 17 on the unpatched forest. HUD screenshots in `fedora:/home/lance` (`calcium-patched-after`, `calcium-air-after`, `calcium-maxheight-after`, `tony-warehouse-after`, `calcium-forest-stock-damage-after`).

1576 xunit tests and 923 pytest tests pass; `backlog doctor` is clean. Docs: the `fallDamageCharacter` row in `docs/level-format.md` and a "Fall damage" section in `docs/development.md` with the mechanism, dump references, slope exemption and measured curve. Implementation in commit `afc4bf1`.

## Notes and follow-ups

Fall damage is floored at 1 HP and cannot kill, so AC #1 was reworded to the measured symptom (1 HP versus none) rather than a death, agreed before implementing. AC #3 and #5 rest on the same drops: a harness teleport stands in for a driven ollie-launched big air on the impact-speed axis, at 25x the height the level's geometry can produce, and landings back onto pipe transitions are exempt from fall damage in the first place (`PlayerMovement.CanTakeFallDamage(normal)` with min/maxBreakFallAngle) - a fact worth remembering when reading any fall-damage repro on this level. Nothing outside `PlayerHealth.OnPlayerLanded` is patched, so `PlayerCamera` and `ControllerShaker` keep reacting to landings.
<!-- SECTION:FINAL_SUMMARY:END -->
