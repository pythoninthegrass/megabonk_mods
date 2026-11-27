---
id: TASK-086
title: Import the Killing Floor 1 Mountain Pass map as a third level
status: To Do
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 23:50'
labels:
  - level
  - kf1
dependencies: []
references:
  - 'https://store.steampowered.com/app/1250/Killing_Floor/'
documentation:
  - docs/kf1-mountain-pass.md
  - docs/conker-colors.md
  - docs/level-format.md
  - docs/asset-bundles.md
  - taskfiles/conker.yml
priority: medium
ordinal: 299000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build a playable Megabonk level from KF-MountainPass, the Killing Floor 1 map by Kevin Butt that ships in the Killing Floor 1 base game (Steam app 1250, `Maps/KF-MountainPass.rom`, Unreal Engine 2). It follows the Conker pipeline (extract, convert, pack, install) and borrows from THPS only where Conker has no equivalent. A first attempt on the Killing Floor 2 workshop rework (item 857015700, Unreal Engine 3) was abandoned: the package is brewed or protected, umodel cannot read its static meshes, and the KF2 editor needs a 95 GB install. The KF1 data is exported with the Killing Floor SDK's UCC tool (level actors as T3D text, the terrain heightmap as a 16-bit BMP) and umodel (meshes and textures). Ripped content stays in gitignored `.tools/`; nothing from the map is committed. Open decision: whether the generated level JSON is tracked (THPS-style) or local only (Conker-style, the default).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The level loads in game, spawns the player on the ground and plays through a run without the pack-missing placeholder
- [ ] #2 Shrines, chests and the boss spawner sit on the ground
- [ ] #3 Walls or the kill floor keep the player inside the map
- [ ] #4 A task chain regenerates the level from a Killing Floor 1 install, and a doc describes it
- [ ] #5 No extracted map content is committed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
State of play: the map loads and renders in game from a pack built locally by the committed builder. Start at TASK-086.04 for the pack chain, the verification recipe and what remains there; TASK-086.03.01 and .02 hold the BSP state. Done so far: the export (086.01), the converter (086.02), the terrain layer inventory (086.03.03) and the Killing Floor 2 reference frames (086.05).

Highest-value next step is TASK-086.03.04, the terrain layer blend. The terrain is one flat untinted surface until the alpha maps drive the layers, which is the difference between a recognizable Mountain Pass and a patch of gray land. TASK-086.03.01 has AC #3 open on the five all-black six-face solids whose surviving collision is unknown.

Windows is the priority: the windows AssetBundle is the deliverable and the one verified in game, and the linux bundle is a byproduct of the same build run. Both Macs have Unity 2023.2.22f1 and each builds from its own gitignored .tools/kf1, so there is no designated build host and no remote build leg.

On AC #5: verified by inspection on 2026-11-27, not by a test. Nothing under .tools is tracked, the generated unity/pack-authoring/Assets/Kf1MountainPass/ directory is ignored by the rule at .gitignore:326, and the only kf1 files in the index are the builder and its .meta, the converter, both test files, the taskfile, the manifest, this doc and the task files. No test enforces that boundary yet, unlike the Thunderstore release gate, so a careless git add -f of a converted texture would go in unnoticed; TASK-048.02 owns closing that gap.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
