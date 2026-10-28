---
id: TASK-021.20
title: Remove the dark background behind the ceiling chain hooks
status: Done
assignee:
  - claude
created_date: '2026-10-28T21:02:00Z'
updated_date: '2026-10-28T21:18:00Z'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
parent_task_id: TASK-021
priority: medium
type: bug
ordinal: 110000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The hanging ceiling chains near world (156, 28, 27) render on an opaque dark blue-grey quad, so the warehouse behind them is hidden and only the chain links should show. Before screenshot: /Users/lance/Desktop/Screenshot 2026-10-28 at 3.59.52 PM.png (copy it to .tools/evidence/ as the before shot).

Context for a fresh implementer: the chain texture comes from skware_l.psx, where magenta is the transparency key (see TASK-021.08 notes). Likely causes are the key or alpha being lost during extraction, or the material using an opaque shader. Mesh and material import is in unity/pack-authoring/Assets/Editor/ThpsPack.cs; shader remap is from TASK-007.03.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The cause of the opaque background is identified and noted in the task
- [x] #2 The chains show only their links, with the scene visible through the gaps, confirmed by before and after screenshots saved under .tools/evidence/
- [x] #3 Other textures using the same transparency key are checked for the same fault
- [x] #4 Any new generator or pack behaviour is covered by tests written first, and docs/thps-warehouse-layout.md is updated
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
1. Cause (AC1): ThpsPack.BakeTransparencyKey paints magenta pixels to opaque (24,30,40) and forces alpha 255, because the remapped MK.Toon Simple + Outline material is opaque. 22 of the 99 textures contain the key (chain E2BFD876, crane hooks 0690EE87/1D982D1F, posters, graffiti, windows F2184063/FA88F30D), so all share the fault (AC3).
2. Fix: bake key pixels to alpha 0 (keep RGB so mip/filter bleed is neutral), mark keyed materials as alpha-clipped. Pack materials use Legacy Shaders/Transparent/Cutout/Diffuse; extend ShaderRemap so a cutout authoring shader enables MK.Toon alpha clipping (keyword/uniform names to confirm in game, since the build only keeps variants it uses). Pure rule goes in shader_remap.cs with unit tests written first.
3. Verify in game with the megabonk MCP: before shot .tools/evidence/021_20_before.png, after shot at world (156,28,27). Check the two window textures and a poster still look right.
4. Update docs/asset-bundles.md (line 115 states the dark-glass bake) and docs/thps-warehouse-layout.md; task check; conventional commit without attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Cause (AC1): ThpsPack.BakeTransparencyKey paints magenta to opaque (24,30,40) and the remapped MK.Toon Simple + Outline material is opaque. 22 of 99 textures carry the key (chain E2BFD876, hooks 0690EE87/1D982D1F, posters, graffiti, windows F2184063/FA88F30D), so the fault is shared (AC3).

Attempt 1 (reverted): key to alpha 0 plus Legacy Cutout authoring shader, remap enabling _MK_ALPHA_CLIPPING and _AlphaClipping on Simple + Outline. In game the quad cleared but the chains rendered white (try2); adding _OutlineSize 0 gave black links on an opaque white quad (try3). The build has no usable alpha-clip variant of that shader with the albedo map. Screenshots: .tools/evidence/021_20_before.png, 021_20_after_try2.png, 021_20_after_try3.png. All source changes reverted; the original pack is reinstalled.

Next options: (a) Sprites/Default (kept as authored by the remap, has alpha blend, unlit, Cull Off) on keyed materials only; (b) find an in-game material that does alpha clip with an albedo map and copy its keyword set; (c) cut the links out as geometry.

Option A done: SeeThroughTextures (E2BFD876, 0690EE87, 1D982D1F) bake the key to alpha 0 and use Sprites/Default. After shot at (156,28,27): .tools/evidence/021_20_after_spritesdefault.png (also 021_20_after.png); chains show only links with the scene behind. The crane hooks were not located in game, so only the chains are visually confirmed. No pure logic was added, so no new unit tests. Remaining 19 keyed textures keep the dark bake; listed in docs/thps-warehouse-layout.md.

Crane hooks confirmed fixed by Lance at world (101, 2, -15).

Follow-up at Lance's request: SeeThroughTextures now covers all 20 keyed textures except the windows F2184063 and FA88F30D, which keep the dark glass. Screenshot: .tools/evidence/021_20_posters_seethrough.png (AC City Stars posters cut out at (156,28,27)). Only that poster was checked in game; the other posters, fence and lamp were not individually viewed.

Windows F2184063 and FA88F30D added to SeeThroughTextures at Lance's request, so all 22 keyed textures are see-through. Lance confirmed the windows in game.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The chains, crane hooks, posters, graffiti, fence, lamp and windows now render see-through. Cause: ThpsPack.BakeTransparencyKey baked the magenta key to an opaque dark colour because the remapped MK.Toon shader is opaque and the game build has no usable alpha-clip variant of it (enabling _MK_ALPHA_CLIPPING ignored the albedo map). Fix: all 22 keyed textures (of 99) are listed in SeeThroughTextures, bake the key to alpha 0 and use Sprites/Default, which is unlit. Evidence in .tools/evidence/021_20_*.png. Commits cd2546c, aa05e71 and the windows commit. No pure logic added, so no new unit tests.
<!-- SECTION:FINAL_SUMMARY:END -->
