---
id: TASK-007.03
title: Shader remap for imported assets
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:44'
updated_date: '2026-10-27 05:21'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.02
parent_task_id: TASK-007
priority: low
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context.

An AssetBundle authored in a different Unity project likely bakes in shader references (e.g. Standard/URP shaders) that don't exist or don't match Megabonk's actual shader set (the game uses MK.Toon and Post Processing v2 per earlier research — confirm exact shaders in use). At load time, remap materials coming from loaded packs onto equivalent shaders the game actually ships, using `Shader.Find` against the game's real shader names (identify these concretely — don't assume MK.Toon's shader names without checking), so imported assets render with a visually consistent, in-style appearance rather than pink/missing-shader errors or an obviously out-of-place PBR look.

Verify visually on at least one non-trivial imported model (not just a flat-colored cube) from TASK-007.01's test bundle or a new one, confirming the remapped material looks reasonably in-style, not just "not pink".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Materials on assets loaded from a pack are remapped from their authoring-project shaders onto Megabonk's actual in-game shaders (confirmed exact shader names, e.g. MK.Toon)
- [x] #2 A non-trivial imported model (not a flat-colored primitive) renders without missing-shader (pink) errors after remap
- [x] #3 The remapped appearance is visually assessed as reasonably in-style, not just technically non-broken
- [x] #4 The exact shader names/mapping rules used are documented for future asset authors
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirm shaders: add a harness command that logs Shader.Find hits for candidate names (MK/Toon/Built-in/Standard/Simple, Simple + Outline, Physically Based + Outline, Toon/Lit Tri Planar *, Unlit/*, Standard) and the shader + properties of materials on a few real game prefabs (tree, rock). Candidates from strings on globalgamemanagers/resources.assets; runtime evidence decides.
2. Render the existing Standard-shader test prop unmapped to see whether it survives (pink or not).
3. Extend PackBuilder to build a non-trivial composite model with multiple materials, a texture and a color (no paid third-party assets).
4. Test-first (xunit, Unity-free): ShaderRemapRules maps authoring shader names (Standard, Standard (Specular setup), Legacy, Unlit, missing) to a target game shader plus a property map. Default target MK/Toon/Built-in/Standard/Simple (approved by Lance).
5. Il2Cpp layer pack_shader_remap.cs: after PackPrefabs.LoadBundleInto, walk renderers' sharedMaterials, replace shaders not shipped by the game via Shader.Find(target), copy mapped properties (main texture, color, normal, emission), cache remapped materials, warn once on unknown shaders and fall back to the default.
6. Verify: task check, task mod:build + relaunch, screenshot composite model beside a native prop; judge in-style look.
7. Docs: exact shader names and mapping table in docs/asset-bundles.md; remove the 'Standard shader not rendered' open item.
Approved by Lance: diagnostic harness command OK, composite model OK, MK.Toon Simple as default.

Revision after in-game verification: the default target is MK/Toon/Built-in/Standard/Simple + Outline, not plain Simple. Plain Simple rendered the albedo texture flat white because the build lacks its textured keyword variants; Lance had asked for Simple, the change is flagged to him.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-27: shader-report harness command added (shader_report.cs, run.py shader-report). In the forest level: Shader.Find resolves MK/Toon/Built-in/Standard/Simple, Simple + Outline, Physically Based + Outline, Particles/Simple, Toon/Lit Tri Planar Normal/Noise Blend, Unlit/Texture, Standard, Legacy Shaders/Diffuse and VertexVit; it does NOT resolve Unlit/Color, UnlitVertexColor, Standard (Specular setup). 1362 of the scene's materials use MK/Toon/Built-in/Standard/Simple + Outline (props, terrain use Toon/Lit Tri Planar Normal); Standard has 2 materials, so it survives stripping. Simple + Outline takes _AlbedoMap, _AlbedoColor, _NormalMap, _EmissionMap/_EmissionColor, _AlphaCutoff/_AlphaClipping. Since the game's own props use the Outline variant, the default target will be Simple + Outline (plain Simple is a constant swap); to confirm visually.

2026-10-27: ShaderRemap (shader_remap.cs, 23 tests, written first) and PackShaderRemap (pack_shader_remap.cs, called from PackPrefabs.LoadBundleInto) done; task mod:test passes (931). In game, the Standard-shader TestProp from testpack loads, shader-report shows the MK Simple + Outline material count rise by one (1362 to 1363), and the screenshot shows an orange cube with no pink. PackBuilder.CreateTestModel (textured Standard, Legacy Diffuse and emissive Standard parts) is written but NOT built: Unity 2023.2.22f1 is not installed on this Mac (no /Applications/Unity/Hub/Editor). Blocks AC #2/#3 on a non-trivial model and the docs step needs the final visual verdict. Docs not yet updated; nothing committed.

2026-10-27: Unity 2023.2.22f1 installed; task pack:build produced testprop and testmodel for Windows and Linux. TestModel (textured Standard, Legacy Diffuse, emissive Standard, plain Standard parts) loaded from UserData/LevelPacks/testpack via bundle:testpack/TestModel. Plain Simple showed the brick as flat white: MK.Toon needs _MK_ALBEDO_MAP and the keyword set every textured game material carries (incl. _MK_ARTISTIC_ANIMATION_STUTTER), and only Simple + Outline has those variants in the build. With Simple + Outline plus the base keywords, the model renders the brick texture, cel bands, shadows and level fog, no pink. Verdict: in-style for shading; outlines are not visibly drawn, same as the game's own props at this distance. Not verified: normal map keyword (no game material has a normal map), emission glow beyond the lit beacon, Linux bundle in game (MelonLoader segfaults the native build).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Pack materials are remapped at load time onto the game's toon shader. ShaderRemap (pure, 27 new tests including the harness parse test) picks the target and property copies; PackShaderRemap applies them to each prefab in PackPrefabs.LoadBundleInto. Target is MK/Toon/Built-in/Standard/Simple + Outline with the keyword set every textured game material carries, because plain Simple lacks the textured variants in the build. Standard, Standard (Specular), Legacy, Unlit, URP and HDRP shaders are remapped (albedo, color, normal, emission copied); MK/Toon, Toon, Sprites and UI shaders are kept; missing or unknown shaders fall back to the default with one warning. Added a shader-report harness command (run.py shader-report) that lists resolvable shaders, scene material shaders and MK.Toon keyword sets, and a TestModel composite in PackBuilder. Verified in the Wine-hosted game: TestModel renders with brick texture, cel lighting and fog, no pink. Mapping table and findings in docs/asset-bundles.md.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
