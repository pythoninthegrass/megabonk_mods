---
id: TASK-080.13
title: Measure whether OpenBonk can produce a playable native macOS arm64 build
status: Done
assignee: []
created_date: '2026-11-16T19:42:00Z'
updated_date: '2026-11-16T20:18:00Z'
labels:
  - native-macos
  - arm64
  - openbonk
dependencies: []
references:
  - TASK-080.12
  - TASK-081
  - 'https://github.com/martin2844/OpenBonk'
documentation:
  - docs/development.md
modified_files:
  - docs/development.md
parent_task_id: TASK-080
priority: high
type: spike
ordinal: 282000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The maintainer approved a bounded macOS feasibility build of the existing sibling OpenBonk reconstruction before committing to the full lifted-runtime delivery route. OpenBonk uses reconstructed C# and Unity 2023.2.22f1, not lifted x86 bodies; its Android gameplay evidence does not establish original-game parity or macOS compatibility. Use an isolated local workspace and private game data, preserve both repositories' existing work and all real saves. This experiment does not change the selected delivery route or authorize broad reconstruction work, public distribution, or changes to existing lift tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The existing OpenBonk sources are attempted with the matching Unity editor for native macOS arm64; input identities, prerequisites and the actual compile/build outcome or concrete blocker are recorded.
- [x] #2 If a build is produced, a native-process check and bounded menu/Forest smoke test record graphics, keyboard/mouse input and required-plugin outcomes; untested behaviour is explicitly labelled.
- [x] #3 The experiment preserves source checkouts and real profiles, keeps game-derived outputs local-only and records the reproducible workspace/build procedure.
- [x] #4 Developer notes distinguish reconstructed-game feasibility from shipped-game parity and recommend the next bounded step based on observed evidence.
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
1. Verify installed Unity 2023.2.22f1 and macOS support; privately export the local Windows game with official AssetRipper 2.0.0 mac-arm64 and assemble the sibling OpenBonk overlay with GUID remapping.
2. Prepare only the isolated workspace: normalize managed plugins with the macOS Mono layout, retain the existing offline Steam stub, remove package duplicates with backups, restore package script/shader/skybox references and input axes, and isolate product/company/application identity before Unity startup.
3. Build the macOS IL2CPP/Metal player. Preserve failed outputs; resolve stale exported Windows Addressables conflicts and unused Discord-linker failure. Unity actually emits a universal app: force arch -arm64 for tests and verify the live process with macOS sample, never describe the output as arm64-only.
4. Reuse the existing localization export/rebuild pipeline with only the preserved Windows bundle path and StandaloneOSX target adapted. Run GUID, collection and English/Spanish default-table checks.
5. Enable the existing recovered map-generation coroutine on OSX and reuse existing prepared-scene/tile references. Diagnose the test-profile reload via an exception stack and verify existing Newtonsoft AOT collection coverage fixes it without resetting or bypassing saves. Enable existing standalone UI input modules.
6. Execute bounded native startup/menu/Forest captures and separately attempt focus-guarded OS keyboard/mouse input. Record successes, failures and untested physical-device/audio/full-run/parity properties. Stop after the bounded feasibility result rather than expanding into a production port.
7. Retain private input identities, source adaptations, profile backup, commands/logs and app artifacts outside both source checkouts. Add privacy-safe developer findings, run repository checks, and finalize the spike independently of the lifted-runtime delivery tasks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Created for the explicitly approved bounded OpenBonk experiment. Matching native arm64 Unity 2023.2.22f1 and MacStandaloneSupport are installed under the system Applications directory; -version returns 2023.2.22f1. No compatible exported project or AssetRipper executable was found in initial local discovery. Available storage is about 299 GiB. The existing Linux input contains only GameAssembly.so, but the local Windows game installation is available. OpenBonk has pre-existing untracked AGENTS.md/CLAUDE.md; megabonk_mods has other in-progress native-execution work and untracked backlog records. All are to be preserved.

Private experiment workspace is outside both repositories, named openbonk-macos-spike-20261116. Official AssetRipper mac-arm64 2.0.0 preflight and export succeeded using the local Windows game installation. Overlay assembly succeeded: 895 GUID matches, 69 mappings across 623 files. Existing Unity Mono normalized Rewired_Core/Coffee and generated the existing OpenBonk offline Steam stub (963 P/Invoke methods); known package-duplicate DLLs moved to a private backup. Product/company were isolated before the first Unity import to prevent real-profile reads/writes. First headless OSX import/compile is running, packages resolved (45). Workspace-only sources/scripts and all logs retained privately.

First headless macOS import completed successfully (Exiting batchmode successfully now), with no C# compile errors. Applied existing input-axis, grass-readability, package-script remapping (7,986 references in 1,015 files), skybox and diagnostic-shader preparation to the private workspace. The first arm64 IL2CPP build compiled the player scripts and Metal shaders, then failed on stale exported Addressables catalog/settings conflicting with Unity's newly generated OSX catalog, plus unrepaired exported compute-shader resources. Preserved failed output/catalogs and used OpenBonkRestorePostProcessing to restore 24 raster and 12 compute shader references from the matching local Unity package. Second full build is running. The Windows export has no supported texture-case-collision pair, so that Linux-specific preparation was skipped rather than guessed.

Build 04 succeeded with zero build errors; codesign --verify --deep passed. App executable, UnityPlayer and GameAssembly include arm64 and x86_64 slices. Launched via arch -arm64; sample records Code Type ARM64, and the game logs OSXPlayer/Metal on Apple M4 Max with the isolated profile. Initial smoke reached MainMenu but localized warning/menu strings had InvalidKeyException; frame-1.png captures the blocked UI. App exited via the bounded smoke component. Adapted the existing localization exporter to the original Windows bundle backup and the rebuilder to StandaloneOSX. Exported 17 locales, 867 tables, 19,157 entries; repaired 51 collection GUIDs in 919 files. Both localization builds, collection restoration, LocalizationGuidPortCheck and default item-description checks succeeded. Build 05 is underway, with optional script-driven warning/menu/map navigation and screenshots; no claim of hardware input or playable Forest yet.

Build 05 succeeded with zero build errors. Native smoke 02 rendered localized character/map UI and invoked the normal Forest start path, but an isolated-profile reload failed and map generation never ran because its Awake body is Android-only. Build 06 enabled only the existing GenerateMap coroutine on OSX (no substitute arena) and reused the existing prepared-scene copies/tile references. Unity reports BuildResult.Succeeded with 13 logged preparation errors, so this is not a clean-build claim. Smoke 03 confirms that recovered map startup now executes; the failed profile load leaves missing progression/stat entries and prevents completion. Added exception-only logging pinpoints Newtonsoft.Json JsonArrayContract.CreateWrapper -> LateBoundReflectionDelegateFactory.CreateParameterizedConstructor with a null MethodBase. Build 07 is testing explicit existing Newtonsoft AotHelper coverage for the save collections and enabling existing standalone UI input modules. This preserves data semantics rather than resetting or bypassing the profile error. These are private-workspace-only portability changes. All automated navigation remains script-driven; real keyboard/mouse/controller operation is unverified.

Build 07 succeeds with three reported errors (not a clean-production-build claim). Existing AotHelper coverage removes the prior progression reload exception without any profile reset; smoke 04 reloads that same profile, renders real recovered Forest terrain with Fox/HUD/timer/minimap, reaches 15 kills and level one, and has no gameplay exception in the log. Live native-process evidence: player-04-sample.txt Code Type ARM64. Focus-guarded OS-injected W/Space smoke 05 renders a moved viewpoint with combat, 14 kills and a level-up; no gameplay exception was logged. The first mouse attempt selected a small app-owned auxiliary window rather than the game window, so no successful upgrade click is claimed; a corrected largest-game-window attempt is running. All apps auto-exit after their bounded smoke and real profiles remain untouched. task check passed: 2,211 Python tests passed, 1 skipped, plus build, mod/installer tests and repository/site lint. Log: private repository-check.log. Only developer notes/backlog will be committed here; OpenBonk's source checkout still has exactly its pre-existing untracked AGENTS.md/CLAUDE.md.

Final input run (same build 07) used focus-guarded macOS CGEvents for W, Space, mouse and Enter; smoke-05/06 show changed gameplay views, combat and level-one offers. Upgrade selection remains blocked after both the corrected largest-game-window click and Enter; no claim of a completed upgrade or fully playable run. Both logs have no gameplay exception and end MAC_RESEARCH_COMPLETE; drivers record player_exit=0 and no research player remains. Physical controllers, audible output, a full run, visual fidelity and shipped-game parity are untested. Existing test-profile reload succeeds across launches, with no reset/bypass. Native/codesign evidence is retained privately. Developer docs now describe the measured result and recommend desktop UI/upgrade-selection work as the next bounded step, without changing any lifted-runtime task. Final markdownlint and git diff --check pass after the result update. No production logic was added to this repo: private integration changes were tested against the actual failing localization/profile/startup runs first and rerun after each adaptation; the existing repo regression suite remains green. Conventional documentation/backlog commits remain pending.

Developer findings committed as a7a5264 (docs: record native macOS OpenBonk feasibility results). All acceptance criteria describe a measured attempt with explicit limitations, not full gameplay parity; the bounded experiment is complete. Final artifact is a private universal app with measured native arm64 execution. The remaining desktop upgrade-selection blocker is recorded, not silently bypassed or turned into unapproved follow-up scope.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built and ran a private OpenBonk macOS IL2CPP/Metal prototype on the M4 Max. Official AssetRipper exported the local Windows game; the existing reconstructed-source overlay compiled with Unity 2023.2.22f1. Native ARM64 execution is confirmed by macOS sample, and codesign verification passes. Workspace-only integration adaptations repaired Addressables/package resources/localization, enabled the existing recovered map startup on OSX, and supplied Newtonsoft AOT collection coverage to fix the reproduced test-profile reload failure without resetting data. Forest renders with Fox/HUD/minimap/timer, combat and level-one offers (15 kills in one capture); focused OS keyboard runs exercise movement/jump. Mouse/Enter upgrade selection remains blocked, so this is not a fully playable or parity-verified port. No gameplay exceptions in the final smoke logs; three reported build errors remain despite BuildResult.Succeeded. Physical controllers, audio, full runs, visual fidelity and original-game parity remain untested. Existing sources and real profiles were preserved; game-derived apps/exports/scripts/logs stay private outside the repositories. Docs commit a7a5264. task check passed: 2,211 Python tests, one skipped, plus build/tests/lint. Next bounded step: desktop upgrade UI input/selection, not a rewrite of gameplay or cancellation of the lift route.
<!-- SECTION:FINAL_SUMMARY:END -->
