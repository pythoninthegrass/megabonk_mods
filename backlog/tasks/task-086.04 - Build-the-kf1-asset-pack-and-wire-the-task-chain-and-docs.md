---
id: TASK-086.04
title: Build the kf1 asset pack and wire the task chain and docs
status: In Progress
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-28 01:48'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.02
  - TASK-086.03.01
documentation:
  - docs/kf1-mountain-pass.md
  - taskfiles/conker.yml
  - taskfiles/pack.yml
parent_task_id: TASK-086
priority: medium
ordinal: 303000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add `unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs` (reusing `PackBuilder.cs`), `unity/pack-authoring/packs/kf1/manifest.json` (id `kf1`, asset `MountainPass`), and `taskfiles/kf1.yml` with verify, export, convert, pack and install, included from `Taskfile.yml` beside the Conker and THPS includes. The export stage reproduces the UCC and umodel steps recorded in docs/kf1-mountain-pass.md from a Killing Floor 1 install. Keep docs/kf1-mountain-pass.md current and add it to the wiki allowlist only if it should be public. Then verify in the running game: relaunch with the new level, enter editor mode, and screenshot the spawn, shop spots, map edges and a drop past the edge so walls and the kill floor are exercised. Confirm the log has no `pack 'kf1' is not installed` line.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The chain runs on the box that builds: the prepare and verify-pack verbs, then task kf1:pack and task kf1:install. The UCC and umodel export runs on the box holding the Killing Floor 1 install, and its .tools/kf1 outputs are carried to the build box
- [x] #2 The level loads in game with no pack-missing placeholder
- [ ] #3 Screenshots show the player, shrines, chests and boss spawner on the ground
- [ ] #4 A drop past the map edge is stopped by walls or the kill floor
- [x] #5 docs/kf1-mountain-pass.md documents the full chain
- [x] #6 The generated level carries the packs entry and the bundle:kf1/MountainPass placement, so .tools/kf1/bsp-preview.mblevel.json is no longer a separate file to carry
- [ ] #7 Every car and truck (not the helicopter, bus or ambulance) renders 1.2 times larger with the rest of the map at the existing scale, the pack rebuilt, and tests pinned to it (maintainer-confirmed in game)
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. In-game verification first (AC #3, #4), no code: clear_console_log, relaunch with .tools/kf1/bsp-preview.mblevel.json, wait for editor and killFloorArmed, spawns off; confirm the log shows pack 'kf1' loaded; teleport to spawn, boss spawner, shrines and chests and screenshot into .tools/evidence/; teleport past the map edge at high y and record whether walls or the kill floor stop the player. Tick AC #3/#4 only on evidence.
2. AC #6 (TDD): write failing tests in tests/test_kf1_mountain_pass.py that the generated level carries the packs entry and the bundle:kf1/MountainPass placement; confirm they fail; move the two preview_level() additions into the main generation; remove the preview-level verb (approved) and the bsp-preview file pin; update AGENTS.md, docs/kf1-mountain-pass.md and taskfiles/kf1.yml references; run task scripts:test.
3. Close: notes, task check, conventional commit with no attribution; .serena changes in a separate commit; leave the maintainer's task-062.01 and task-086.05 edits out.
4. Pending scope decision: maintainer reports Tony looks too tall relative to vehicles (likely a map-wide scale issue). Needs a decision on AC vs follow-up task before any change.

Scale (approved as AC #7): measure vehicle mesh heights in the umodel export against Tony's capsule height, choose a SCALE factor, change SCALE in scripts/kf1_mountain_pass.py test-first, run prepare, task kf1:pack and task kf1:install, then run the AC #3/#4 in-game verification once at the new scale.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
State of play at handoff: the pack builds and plays, no code work is outstanding. Kf1MountainPassPack.cs builds kf1 for windows and linux from .tools/kf1/mesh.json, taskfiles/kf1.yml carries pack and install, unity/pack-authoring/packs/kf1/manifest.json is the manifest, and the windows bundle is installed in the game. Verified in game from the locally built bundle: the log reads Packs: loaded pack 'kf1' with 1 prefab(s) then LiveEdit: spawned 'bundle:kf1/MountainPass' (prefab 'MountainPass'), and the fixed editor camera matches the hand-built original at a mean luma delta of 0.43 of 255 with 0.024 per cent of pixels above 15. prepare and verify-pack also run on the build box and produce byte-identical mesh.json and level files to the other box, so the converter is deterministic across the two Macs.

To reproduce from cold: MEGABONK_DEV=true in .env; Unity 2023.2.22f1 with the windows-mono, linux-mono and linux-il2cpp modules (UNITY_EDITOR in .env overrides the Hub path); then uv run scripts/kf1_mountain_pass.py prepare, uv run scripts/kf1_mountain_pass.py verify-pack, task kf1:pack, task kf1:install. Then through the megabonk MCP: clear_console_log, relaunch with .tools/kf1/bsp-preview.mblevel.json, then state until editor and killFloorArmed are true. Judge a build by the windows bundle; linux is a byproduct of the same run.

AC #3 is the remaining verification, not code. Use teleport to put the player on each anchor and screenshot into .tools/evidence/. The converter prints the spawn and boss spawner positions as it runs (spawn [-65.80, 37.83, 46.53], boss spawner [142.91, -8.50, -224.22]) and logs each anchor it skips for having no floor, so an ungrounded prop is reported rather than silently floating; the KFRandomItemSpawn skips are that class of problem. ExtraShrines reports how many spawned of how many planned. What exists so far is top-down editor screenshots of terrain and brushes, none of these placements, so AC #3 has no evidence yet.

AC #4 is unverified and is the real open question. killFloorY is -72 at runtime and 0.1 per cent of the terrain (min -137) sits below it, so a drop can land on terrain instead of the kill floor. Teleport outside the map bounds at a high y and watch the player's y in state until it settles, then record whether walls or the floor stopped them. The stock Forest backdrop (960 by 960 Mesh at the origin, Water planes at y=-129 and y=6) sits underneath and is not part of the map.

AC #6 retires the preview file. .tools/kf1/bsp-preview.mblevel.json comes from the preview-level verb, and the generated kf1-mountain-pass.mblevel.json has no packs entry, so previewing with the generated file silently loads the stock Forest map while still placing its chests. preview_level() in scripts/kf1_mountain_pass.py holds the two additions and tests/test_kf1_mountain_pass.py pins the file byte for byte. Folding them into the generated level makes that the file which loads, so both files' pinned expectations change together.

Pack id gotcha: the id is baked into saved levels, because the packs map keys on it and each placement payload carries bundle:kf1/MountainPass. Two placeholder shapes, both spawning prefab Missing:bundle:kf1/MountainPass: with no pack directory the log says pack 'kf1' is not installed, and with the manifest installed but no bundle it says loaded pack 'kf1' with 0 prefab(s) then manifest of 'kf1' lists 'MountainPass' but its bundle does not hold it, which is what a transfer that copied only the manifest looks like.

Do not compare bundles by hash: the builder recreates Assets/Kf1MountainPass/ and Unity re-imports with fresh GUIDs, so two builds of unchanged inputs always differ. Compare in game at the fixed camera and keep the no-bundle frame as the control (mean 52.94 of 255 across 72 per cent of pixels), so a near-zero diff cannot mean two renders of nothing. The first screenshot after a load can be the black title fade, so query state before judging a frame and read BepInEx/LogOutput.log to confirm the pack loaded.

Harness gotchas: a level load turns enemy spawns back on, so send spawns off after it, and entering the editor late into an unattended run has left the player dead. The console replays its persisted history, so call clear_console_log before relaunch whenever a console verb's output changed.

Definition of Done is left unticked deliberately: those gates describe the state at close, and whoever closes this re-runs task check and the suite against their own changes. Tests for the pack work were written first and the doc is current, so #2 and #3 already hold for the shipped code.

Dependency reality: this task depends on TASK-086.03.01, which is In Progress with AC #3 open on the five all-black six-face solids whose surviving collision is unknown (the 17 portal sheets are identified). That plus TASK-086.03.04, HIGH, terrain layer blending, gates what the map actually looks like. The doc's TODO list and these criteria are kept in step.

Housekeeping: 29 unpushed commits include this work and nothing here has been pushed. Two backlog files, task-062.01 and task-086.05, carry the maintainer's own uncommitted edits and are not part of this task. Whether docs/kf1-mountain-pass.md joins the public wiki allowlist is the maintainer's call and it is not on it now.

AC #6 done: make_level writes the packs entry and the bundle:kf1/MountainPass placement (first in edits); preview-level verb, bsp-preview file and PREVIEW_* names removed; AGENTS.md and docs/kf1-mountain-pass.md updated. Tests written first and failed before the change; task scripts:test and task check pass. In-game verification for AC #3/#4 is paused pending a scale decision: the maintainer reports Tony is too tall relative to vehicles, and SCALE (3.85/100 in scripts/kf1_mountain_pass.py) moves every coordinate, so evidence taken now would be redone.

Scale decision: measured Tony against a police car at equal depth (.tools/evidence/scale-tony-vs-police-car-3.png): Tony renders about 3.2 units, the car about 4.39, so a global SCALE increase is not supported. Maintainer instead asked for every car and truck 20 percent larger, helicopter excluded, map scale unchanged. Implemented as enlarge_vehicles() in scripts/kf1_mountain_pass.py (VEHICLE_SCALE 1.2) over police car, Lancia, cab, ArmyTruck and GUP-Lorry1; the lorry's cab and cargo doors move out from their nearest lorry so they stay attached. Bus, ambulance, camper trailer and the helicopter are untouched; add them to VEHICLE_MESHES if wanted. AC #7 reworded to match; the ACs previously checked (#1, #2, #5, #6) are unchanged.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
