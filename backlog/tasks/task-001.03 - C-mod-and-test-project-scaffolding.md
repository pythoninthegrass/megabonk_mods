---
id: TASK-001.03
title: C# mod and test project scaffolding
status: To Do
assignee: []
created_date: '2026-10-06 21:39'
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
- [ ] #1 Directory.Build.props defines BottleFolder/GameFolder/ModInstanceFolder with a gitignored Directory.Build.local.props override hook, matching the xeno_mods pattern
- [ ] #2 src/MegabonkLevels.Mod builds against net6.0 (or whatever MelonLoader 0.7.x actually targets, confirmed not assumed) referencing MelonLoader/Harmony/Il2Cpp-interop assemblies via HintPath+Private=false with none vendored into the repo
- [ ] #3 A placeholder MelonMod subclass builds and its AfterTargets="Build" deploy step copies the DLL+PDB into the resolved Mods folder
- [ ] #4 tests/MegabonkLevels.Tests targets net10.0, uses xUnit, references zero Unity/game/MelonLoader assemblies, and compile-links at least one placeholder logic file from the Mod project via a passing test
- [ ] #5 File naming convention (logic vs *_patch.cs files) is documented (in docs/modding-setup.md or a CONTRIBUTING note) for later tasks to follow
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
