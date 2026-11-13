---
id: TASK-067.03
title: Import Squeaker into Unity and build a squeaker asset bundle
status: Done
assignee: []
created_date: '2026-11-12T22:18:00Z'
updated_date: '2026-11-13T04:45:00Z'
labels:
  - character
  - assets
dependencies:
  - TASK-067.02
references:
  - unity/pack-authoring/Assets/Editor/PackBuilder.cs
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - taskfiles/pack.yml
  - taskfiles/thps.yml
  - src/MegabonkLevels.Mod/pack_prefabs.cs
documentation:
  - docs/asset-bundles.md
  - docs/characters.md
parent_task_id: TASK-067
type: feature
ordinal: 229000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Blender exports from TASK-067.02 need to become a Squeaker character prefab and a stale cookie projectile prefab inside an asset bundle the mod can load at runtime. Existing bundles carry only level props and audio, built from unity/pack-authoring through Editor scripts and the pack taskfiles, so a character bundle has to follow the same build, install and shader-remap path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Unity prefab for Squeaker and a prefab for the stale cookie exist in unity/pack-authoring and meet the prefab requirements in docs/characters.md
- [x] #2 An editor build method produces a squeaker bundle for both Windows and Linux
- [x] #3 Tasks to build and install the squeaker bundle exist, mirroring the existing pack and thps tasks
- [x] #4 The built bundle installs into the game's UserData and its prefabs resolve through the mod's pack loader with the toon shader remap applied
- [x] #5 A pytest checks the built prefab and skips, rather than fails, when the generated bundle is absent
- [x] #6 The import and build steps are documented in docs/characters.md
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
1. Test first: tests/test_squeaker_pack.py reads the generated Assets/Squeaker/Squeaker.prefab and StaleCookie.prefab (YAML) and the committed packs/squeaker/manifest.json; skips when the generated prefabs are absent (add Assets/Squeaker prefabs to GENERATED_ARTIFACTS). Checks: Animator, SkinnedMeshRenderer, transforms named hips and torso, cookie MeshRenderer, manifest assets match prefabs.
2. Editor script Assets/Editor/SqueakerPack.cs: configure the FBX importers (Generic rig, clips Idle/Run/Jump/Falling/Grind with loop flags), instantiate and fully unpack each FBX into Squeaker.prefab / StaleCookie.prefab with an Animator and a controller holding the five clips, assign both to the squeaker bundle, build Windows and Linux via the same Build path as ThpsPack/PackBuilder.
3. Taskfile: squeaker:pack (build) and squeaker:install (pack:install PACK=squeaker), mirroring thps.yml; committed manifest unity/pack-authoring/packs/squeaker/manifest.json.
4. Verify: run the Unity build for both platforms, install, check the pack loads and prefabs resolve with the toon remap through the megabonk harness.
5. Docs in docs/characters.md; gitignore the generated prefabs/controller; task check; conventional commit with no attribution.
Open risk: Animator parameter names are unconfirmed (TASK-067.02 notes); they need the PlayerRenderer.Update decompile. I will check the il2cpp dump and Ghidra before wiring parameters into the controller.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-11-12 (commit 00f71fe): SqueakerPack.Build produces Squeaker.prefab, StaleCookie.prefab and Squeaker.controller, and the squeaker bundle for Windows and Linux (task squeaker:pack, squeaker:install). task check passes (1556 passed). Installed on the authoring box and relaunched: the log shows `loaded pack 'squeaker' with 2 prefab(s)` with no shader or load warnings. AC4 left unchecked: neither prefab has been placed in the editor, so the toon remap on Squeaker's materials has not been seen. The controller has the five clips as unconnected states; Animator parameter names are still unread (needs the PlayerRenderer.Update decompile). ThpsPack now calls the shared PackBuilder.BuildNamedBundle; the thps bundle was not rebuilt to confirm it is byte-identical.

Ghidra decompile of PlayerRenderer.Update (VA 0x1803492F0) done: it calls Animator.SetBool four ways, with string-literal slots resolved through .tools/il2cpp_dump/stringliteral.json to `moving`, `grounded`, `jumping`, `grinding`. The controller now declares those bools and connects the clips with transitions. What `jumping` tracks (player state field 0x164 below 4) was not traced, so the Jump/Falling conditions are a guess; the transitions have not been seen in game.

Remap check 2026-11-12: a scratch level placed bundle:squeaker/Squeaker and bundle:squeaker/StaleCookie in a Forest level; both spawned as placements and rendered with the toon shader (all five Squeaker slots coloured, cel bands, fog; cookie dough and chips). Screenshot at .tools/evidence/067-03-squeaker-in-game.png. The animation transitions and the model scale against colliderHeight remain untested (TASK-067.04 territory, once the character is selectable).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added SqueakerPack.Build (unity/pack-authoring/Assets/Editor/SqueakerPack.cs), which sets the FBX importers, builds Squeaker.controller with the moving/grounded/jumping/grinding bools recovered from the PlayerRenderer.Update decompile, saves unpacked Squeaker and StaleCookie prefabs and builds the squeaker bundle for Windows and Linux. ThpsPack now shares PackBuilder.BuildNamedBundle. Added squeaker:pack, squeaker:install and squeaker tasks, the pack manifest, tests/test_squeaker_pack.py (skips when the generated prefabs are absent) and the build documentation in docs/characters.md. Verified in the running game: the pack loads with both prefabs and both render with the toon remap (.tools/evidence/067-03-squeaker-in-game.png). task check passes. Commits 00f71fe, d0643ef, 59dd8b3. Not verified: controller transitions in play, what the jumping parameter tracks, model scale against colliderHeight, and a rebuilt thps bundle after the PackBuilder refactor.
<!-- SECTION:FINAL_SUMMARY:END -->
