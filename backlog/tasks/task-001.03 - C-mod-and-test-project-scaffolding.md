---
id: TASK-001.03
title: C# mod and test project scaffolding
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:39'
updated_date: '2026-10-06 22:55'
labels:
  - level-editor
  - tooling
dependencies: []
parent_task_id: TASK-001
priority: high
type: chore
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-001 first for full context.

Scaffold the C# project structure, modeled directly on `~/git/xeno_mods/src/x2_load_profiler/` and `~/git/xeno_mods/tests/x2_load_profiler.tests/` (read both directly — `Directory.Build.props`, `.csproj`, `manifest.json`):

1. **`Directory.Build.props`** (repo-root or per-project, matching whatever xeno_mods actually does — check if it's root-level or per-mod-folder in that repo) defining MSBuild properties: `BottleFolder` (CrossOver bottle path), `GameFolder` (Megabonk's managed-assemblies-equivalent — for MelonLoader this is likely `MelonLoader/Il2CppAssemblies` rather than `_Data/Managed`, since this is IL2CPP not Mono; confirm the correct folder MelonLoader generates Il2CppInterop assemblies into once TASK-002 proves the loader works), `ModInstanceFolder` (the game's `Mods/` directory for MelonLoader, not a per-user AppData mods folder — confirm against MelonLoader's actual mod-loading convention), each with an `<Import Project="Directory.Build.local.props" Condition="Exists(...)" />` override hook. Add `Directory.Build.local.props` to `.gitignore`.

2. **`src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj`**: target framework matching MelonLoader's bundled runtime (MelonLoader 0.7.x bundles .NET 6 — confirm and use `net6.0`). References to `MelonLoader.dll`, `0Harmony.dll`, and the Il2Cpp-interop-generated `Il2Cppmscorlib.dll`/`Il2CppAssembly-CSharp.dll`/etc. (exact assembly names TBD once TASK-002 generates them) via `<HintPath>$(GameFolder)/X.dll</HintPath><Private>False</Private>` — never vendor these. A `manifest.json` or MelonLoader's `MelonInfo` attribute-based metadata (MelonLoader uses assembly attributes, not a manifest.json like the xeno_mods game's own loader — confirm and use whichever MelonLoader actually expects). An `AfterTargets="Build"` target copying the built DLL + PDB into `$(ModInstanceFolder)`.

3. **`tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj`**: xUnit (match xeno_mods's package versions as a starting point, but prefer latest stable compatible with net10.0), targeting `net10.0` per `.tool-versions`'s dotnet pin, with `<Using Include="Xunit" />`. This project must NOT reference the Mod project or any Unity/game/MelonLoader DLL — it compile-links only pure-logic `.cs` files via `<Compile Include="../../src/MegabonkLevels.Mod/foo.cs" Link="foo.cs" />`, exactly like xeno_mods's test project does.

4. Establish the file-naming convention from day one: pure logic files (e.g. `edit_stack.cs`) are kept separate from Unity/Harmony-dependent "patch" files (e.g. `generation_patch.cs`), so future tasks (TASK-003 onward) know where new logic/patch code goes and what's testable.

This task has no real logic to write yet — just enough skeleton (e.g. a placeholder `MelonMod` subclass with an `OnInitializeMelon` log line, and one placeholder class + one placeholder xUnit test proving the link-compile wiring works end to end) to prove the build, deploy, and test wiring all function.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Directory.Build.props defines BottleFolder/GameFolder/ModInstanceFolder with a gitignored Directory.Build.local.props override hook, matching the xeno_mods pattern
- [x] #2 src/MegabonkLevels.Mod builds against net6.0 (or whatever MelonLoader 0.7.x actually targets, confirmed not assumed) referencing MelonLoader/Harmony/Il2Cpp-interop assemblies via HintPath+Private=false with none vendored into the repo
- [x] #3 A placeholder MelonMod subclass builds and its AfterTargets="Build" deploy step copies the DLL+PDB into the resolved Mods folder
- [x] #4 tests/MegabonkLevels.Tests targets net10.0, uses xUnit, references zero Unity/game/MelonLoader assemblies, and compile-links at least one placeholder logic file from the Mod project via a passing test
- [x] #5 File naming convention (logic vs *_patch.cs files) is documented (in docs/modding-setup.md or a CONTRIBUTING note) for later tasks to follow
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Follow parent TASK-001's plan. src/MegabonkLevels.Mod/ with per-project Directory.Build.props (BottleFolder/GameFolder/ModInstanceFolder, gitignored Directory.Build.local.props hook), .csproj targeting net6.0 (MelonLoader 0.7.x's target), HintPath+Private=false references to MelonLoader.dll/0Harmony.dll from $(GameFolder)/MelonLoader's net6 dir (exact Il2Cpp-interop game-assembly references deferred to TASK-002 per parent plan, since those DLLs don't exist until MelonLoader has run once against the real game - this task's placeholder MelonMod only needs MelonLoader.dll + 0Harmony.dll to compile). Placeholder MelonMod subclass with MelonInfo/MelonGame attributes + OnInitializeMelon log line, no manifest.json. AfterTargets=Build copies DLL+PDB to $(ModInstanceFolder). tests/MegabonkLevels.Tests on net10.0, xUnit (Microsoft.NET.Test.Sdk/xunit/xunit.runner.visualstudio matching xeno_mods versions), zero game/Unity/MelonLoader refs, one placeholder pure-logic .cs compile-linked from the Mod project + one passing test. Document the logic-vs-*_patch.cs naming convention in docs/modding-setup.md (created here as a stub, fleshed out by .04).

Risk: MelonLoader.dll/0Harmony.dll don't exist on this machine yet (MelonLoader isn't installed - that's gated behind the live-action checkpoint). `dotnet build` will fail to resolve those HintPath references until then. This is expected and acceptable for scaffolding-only scope; will verify via `dotnet build` once MelonLoader is actually installed post-checkpoint, and in the meantime verify the project at least parses/restores and that the test project (which has no such references) builds and passes standalone.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Wrote src/MegabonkLevels.Mod/ (Directory.Build.props, MegabonkLevels.Mod.csproj targeting net6.0, placeholder_logic.cs, megabonk_levels_mod.cs with MelonInfo/MelonGame attrs + OnInitializeMelon) and tests/MegabonkLevels.Tests/ (net10.0 xUnit project compile-linking placeholder_logic.cs, one passing test).

Verified: `dotnet test tests/MegabonkLevels.Tests` passes (1/1) with zero game/Unity/MelonLoader references. `dotnet build src/MegabonkLevels.Mod` restores cleanly but fails to compile with CS0246 on MelonLoader/MelonMod/MelonInfo/MelonGame types, because MelonLoader.dll/0Harmony.dll don't exist at the HintPath yet (MelonLoader isn't installed on this machine - gated behind the parent task's live-action checkpoint). This is the expected, documented state for scaffolding-only scope; AC#2/#3 (mod builds, deploy copies into Mods) will be verified once MelonLoader is installed post-checkpoint.

Also extended .gitignore with bin/, obj/, Directory.Build.local.props, .env, .task/ now (rather than waiting for TASK-001.04) since dotnet build already produces bin/obj locally and leaving them untracked-but-ignored keeps git status clean while .04 is still pending - no scope change, just earlier timing of one .04 acceptance item.

Live-verified against the real install: `task mod:build` compiles cleanly (0 warnings, 0 errors) now that MelonLoader.dll/0Harmony.dll exist at MelonLoader/net6/ (confirmed: MelonLoader 0.7.3 does ship net6, matching the Directory.Build.props assumption). The AfterTargets=Build deploy step copied MegabonkLevels.Mod.dll + .pdb into the game's Mods/ folder - confirmed by listing it directly. AC#2 and #3 checked. `task check` (build+test+tools:test+lint) now passes cleanly end to end.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Scaffolded src/MegabonkLevels.Mod/ (Directory.Build.props with BottleFolder/GameFolder/MelonLoaderFolder/Il2CppAssembliesFolder/ModInstanceFolder + gitignored Directory.Build.local.props hook, .csproj targeting net6.0, placeholder_logic.cs, megabonk_levels_mod.cs with a MelonMod subclass + MelonInfo/MelonGame attributes) and tests/MegabonkLevels.Tests/ (net10.0 xUnit, compile-links placeholder_logic.cs, zero game/Unity/MelonLoader references).

Live-verified in this session once MelonLoader was installed (TASK-001.02): `task mod:build` compiles with 0 warnings/0 errors against the real MelonLoader.dll/0Harmony.dll, and the AfterTargets=Build deploy step copies MegabonkLevels.Mod.dll + .pdb into the game's real Mods/ folder (confirmed by listing it). `dotnet test` passes 1/1 standalone.

File-naming convention (plain-logic snake_case vs *_patch.cs for Unity/Harmony-dependent files) documented in docs/modding-setup.md.

DoD: task check passes, docs updated. "Tests written first" honestly unchecked (scaffolding mirrors an established convention; test and placeholder written together, not strict red-green TDD). Commit pending user confirmation, combined with the other TASK-001 subtasks.
<!-- SECTION:FINAL_SUMMARY:END -->
