---
id: TASK-070
title: Translate the shipped GLSL shader programs to Metal and score the failure rate
status: Done
assignee: []
created_date: '2026-11-15 08:49'
updated_date: '2026-11-15 10:12'
labels:
  - research
  - native
  - shaders
dependencies: []
references:
  - docs/development.md
documentation:
  - >-
    https://docs.bepinex.dev/master/articles/user_guide/installation/unity_il2cpp.html
  - 'https://github.com/NeighTools/UnityDoorstop'
modified_files:
  - scripts/shader_metal_pass.py
  - tests/test_shader_metal_pass.py
  - taskfiles/re.yml
  - docs/development.md
priority: medium
ordinal: 71500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The macOS-native route decision picks B: re-host the shipped x86-64 GameAssembly as a macOS dylib against Unity's official macOS player. Its top blocker is the shader container. The native Linux build stores each of the 141 baked shaders as a GLSL source chunk (7,305 programs, 34,969,460 B decompressed) plus a per-program blob with no SPIR-V magic, and macOS players are Metal-only, so nothing can be copied and everything must be translated.

This task runs the cheapest experiment that can still kill B. Drive every GLSL program through glslangValidator, then SPIR-V, then spirv-cross --msl, then the Metal compiler, and report pass/fail per stage with failure reasons grouped. The census scripts from the spike were throwaway temp-dir scripts; this pass belongs in the repo under scripts/ behind a task alias so it can be re-run after each depot push. No Unity install, no licence and no game launch are needed for the core pass.

Two one-off companion checks ride along because they gate the same decision: whether the Unity archive still offers macOS Build Support for 2023.2.22f1, and whether BepInEx's official Unity.IL2CPP-macos-x64 build with doorstop gets as far as generating BepInEx/interop and LogOutput.log against a macOS player under Rosetta. Both fail loudly, which is what makes them cheap to test.

Inputs: the reachable native Linux build (GameAssembly.so 87,741,504 B, Megabonk_Data about 425 MB) sits in a backup directory on the maintainer's Fedora host, reachable over the tailnet. Neither glslang nor spirv-cross is installed there today.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every one of the 7,305 GLSL programs is driven through glslangValidator to SPIR-V, spirv-cross --msl, and xcrun metal -c, with a per-stage pass/fail count and failure reasons grouped by kind.
- [x] #2 The pass lives in the repo under scripts/ behind a task alias, takes the Linux build path as an argument, and prints a machine-readable summary so it can be re-run after a depot push.
- [x] #3 The report states a go/no-go on route B's shader story: scriptable translation versus translation by hand, with the count of programs that need hand edits and the categories they fall into.
- [x] #4 The two companion checks have recorded answers: whether Unity 2023.2.22f1 offers macOS Build Support in the archive, and whether the macOS BepInEx IL2CPP build plus doorstop produces BepInEx/interop and LogOutput.log under Rosetta.
- [x] #5 The outcome is written into the Static recomp section of docs/development.md, correcting the route decision there if the evidence flips it.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

Run all four stages on the authoring Mac: the decisive stage (xcrun -sdk macosx metal -c) exists only on macOS, so a single-host toolchain keeps one run reproducible. The Linux build is rsync'd once from the Fedora player box into gitignored .tools/megabonk-linux-native/ and the Python never shells out to ssh.

## Steps

1. Toolchain: brew install spirv-cross. glslangValidator (SPIR-V gen 11) and the Metal toolchain (probe .metal -> .air) verified present; Rosetta running.
2. Inputs: rsync GameAssembly.so + Megabonk_Data (~425 MB) into .tools/megabonk-linux-native/Megabonk/ behind re:shaders-pull.
3. scripts/shader_metal_pass.py (PEP 723: unitypy, lz4; argparse; positional Linux build path):
   - extract: enumerate Shader objects, read the GLSL platform chunk (per-shader LZ4 blob indexed by platforms[]/compressedLengths[]/decompressedLengths[]/offsets[], u32 directory count + 12-byte entries), write one source per program plus a manifest (shader name, subshader/pass, m_ProgramType, keywords, sizes). Spike reference: spike017/shaderchunks.py + probe.py.
   - glslang: glslangValidator -V -> .spv, stderr captured.
   - spirv-cross: spirv-cross --msl -> .metal.
   - metal: xcrun -sdk macosx metal -c -> .air.
   - flags: --jobs, --stages, --limit, --resume (content-hash cache), --json.
4. Failure taxonomy: per-stage categories plus the first raw diagnostic, grouped counts. glslang: version-directive, unsupported-extension, unity-identifier, builtin-texture-sampling, precision, output-variable, other-parse. spirv-cross: exception, unsupported-operand, empty-output. metal: address-space, stage-in-out, resource-limit, implicit-vector-convert, function-not-found, other.
5. Report: per-stage pass/fail by shader stage, category histogram, hand-edit list with categories, verdict. Threshold: >=95% first-pass end to end = scriptable; 60-95% = scriptable with a hand-edit tail; <60% = flip to route C.
6. Tests first (tests/test_shader_metal_pass.py) over the pure logic: directory-entry parsing, manifest building, diagnostic classification, summary aggregation.
7. taskfiles/re.yml: re:shaders-metal (translation, takes the Linux build path, JSON summary on stdout) and re:shaders-pull (rsync).
8. Companion checks: HTTP probe of the Unity download archive for 2023.2.22f1 macOS Build Support; fetch and inspect the official BepInEx Unity.IL2CPP-macos-x64 release (existence, doorstop artifacts, interop assemblies) and record the macOS-player/licence blocker loudly rather than silently skipping.
9. docs/development.md Static recomp: measured pass/fail, categories, go/no-go; correct the B-over-C decision if the evidence flips it.

## Risks

- unitypy's ShaderProgram path may not parse the Linux chunk; fall back to the raw 12-byte directory walk.
- glslang may reject Unity's GLSL dialect wholesale (#version 110 plus fixed-function builtins). That is itself the answer, but confirm with --limit 40 before the full 7,305-program run.
- The Metal stage dominates runtime (~1 s/program); parallelize with --jobs and make reruns cheap via --resume.
- The 6 built-in shaders carry six platform chunks; must filter by platform id rather than taking chunk 0.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Measured result (all 7,305 programs, native Linux build, glslang 11:16.6.0 / spirv-cross 2026-09-16 / metal 32023.883)

Raw pass (shipped source, default tool flags): glslang 7,276, spirv-cross 7,273, metal 6,689 -> 91.57% end to end.
With the three mechanical fixes that are now the script's defaults: glslang 7,305, spirv-cross 7,305, metal 7,256 -> 99.33%, verdict `scriptable` (>=0.95 threshold). 6,123 programs came back with bindings renumbered, 29 with glslang's own suggested #extension lines added.

Failure categories (raw): 583x `'buffer' attribute parameter is out of bounds: must be between 0 and 30` (glslang --auto-map-bindings spends one binding per array element, so indices hit 56 for at most 38 distinct resources; dense renumbering fixes 535 of them); 29x `required extension not requested` for gl_Layer/num_views in the Hidden/* VR built-ins; 3x `Multisampled array textures are supported from 2.1` (spirv-cross defaults to MSL 1.2, pass --msl-version 20100); 1x `unknown type name 'unknown'` in the single geometry program (spirv-cross MSL backend has no geometry entry-point type; --msl-capture-output and --stage geom do not help).

Hand-edit tail: 49 programs in 5 shaders (0.67%). 48 exceed Metal's 31 distinct per-stage resource slots outright and need their loose uniforms packed into named uniform blocks: IL3DN/WaterOptimized x32, TextMeshPro/Mobile/Distance Field x8, TextMeshPro/Distance Field x4, TextMeshPro/Distance Field Overlay x4. spirv-cross --msl-argument-buffers (MSL 2.0/3.0, tier 0/1) is not a way out: its emitted code does not compile ('const constant float4 *const constant' is not a structure or union). Automatic block packing was prototyped and rejected here: glslang refuses anonymous blocks and --uniform-buffer is unsupported.

glslang target env decides everything: --glslang-target-env vulkan1.0 keeps only 179/7,305 (2.4%), 7,124 on `'non-opaque uniforms outside a block' : not allowed when using GLSL for Vulkan`. Unity's baked GLSL is legal GL and illegal Vulkan. Everything that survives glslang under Vulkan also passes spirv-cross and Metal, so nothing downstream is a risk on that path.

Granularity: the platform-15 chunk of each Shader object is one GLSL unit holding one #ifdef <STAGE>-guarded program per entry -> 7,305 programs over 138 shaders (141 objects, 3 without a GLSL chunk), 32,527,272 B; #version 150 x4,302, 330 x2,854, 420 x146, 410 x3; 3,652 vert + 3,652 frag + 1 geom. Only mechanical preprocessing: #version raised to 450 core, 11,830 #extension lines dropped. --no-normalize scores shipped source verbatim.

## Companion checks

Unity 2023.2.22f1 macOS Build Support is still in the archive (hash 6b19bf4f8115): UnitySetup-Mac-Mono-Support 554,499,901 B and UnitySetup-Mac-IL2CPP-Support 539,183,293 B, both HTTP 200, plus matching MacEditorInstaller (4,186,416,450 B) and MacEditorInstallerArm64 (4,181,442,624 B) editors.

BepInEx Unity.IL2CPP-macos-x64 is published on both channels, including the bleeding-edge channel this repo uses on Windows: 6.0.0-be.793 (2026-11-05, 32,735,133 B) at builds.bepinex.dev/projects/bepinex_be (the download URL is the href path, not /downloads/...), and the last tagged v6.0.0-pre.2 (2024-08-27, 32,523,182 B). be.793 ships libdoorstop.dylib universal (x86_64 arm64 arm64e, doorstop 4.6.0) so the injector does not need Rosetta, but dotnet/libcoreclr.dylib, libclrjit.dylib and BepInEx/core/libdobby.dylib are x86_64-only, so the managed host does. The interop chain is all present (Il2CppInterop.Generator.dll, Cpp2IL.Core.dll, LibCpp2IL.dll, 0Harmony.dll, BepInEx.Unity.IL2CPP.dll). Rosetta 2 is installed on the authoring Mac and executes x86_64.

The loader check was run rather than deferred, using a minimal IL2CPP player built with the already-installed editor at the pinned 2023.2.22f1 (global-metadata.dat version 29, matching the shipped game). Both build targets succeed and the player and GameAssembly.dylib come out universal x86_64+arm64, i.e. SetArchitecture(Standalone, 0) does not restrict. Launched translated (arch -x86_64 on the launcher script itself: a universal binary follows its parent's slice and pre.2's script ends in a bare exec, so ARCHPREFERENCE is ignored) and headless (-batchmode -nographics -logFile), be.793 injects, writes BepInEx/LogOutput.log, logs Running under Unity 2023.2.22f1, downloads unity.bepinex.dev/libraries/2023.2.22.zip, runs Cpp2IL on the Mach-O (metadata version 29.1, Universal Mach-O File, 15,955 method definitions) and generates 80 interop assemblies (16 MB: Assembly-CSharp.dll, UnityEngine.CoreModule.dll 2.7 MB, Il2Cppmscorlib.dll 4.3 MB) with assembly-hash.txt, then Chainloader initialized. So the AC#4 signal is yes: interop and LogOutput.log are produced under Rosetta.

Root cause of every failure is the app-bundle layout, announced by the loader's own line System platform: Linux 64-bit. Paths.SetExecutablePath never takes its macOS branch, so GameRootPath is the executable's own directory and the data probe looks for <exe dir>/<Proc>_Data then <exe dir>/Data, while a .app keeps data at Contents/Resources/Data; UnityPreloaderRunner hardcodes gameDataRelativeToManaged=false, so DOORSTOP_MANAGED_FOLDER_DIR cannot redirect it. Two symlinks in Contents/MacOS/ are the whole workaround (<Proc>_Data -> ../Resources/Data, GameAssembly.so -> ../Frameworks/GameAssembly.dylib, the .so suffix following the misdetected platform). The two bundles fail at different depths from that one cause: be.793 throws ArgumentNullException(gameDataPath) at UnityInfo.Initialize, while pre.2 keeps a wrong-but-non-null path, so UnityInfo.DetermineVersion (which reads the version string out of <GameDataPath>/globalgamemanagers at a fixed offset and defaults when it is missing) leaves the version at 0.0.0 and dies deeper as Il2CppInterop UnityVersionHandler "No handler" despite that bundle shipping a 2023.2.0 handler.

One gap remains after interop: Chainloader initialized then Fatal "Could not locate Il2Cpp game assembly (GameAssembly.dll, UserAssembly.dll or libil2cpp.so)" - a by-name NativeLibrary.TryLoad with no macOS candidate. Upstream PR 1407 adds exactly these bundle fallbacks plus a resolved-path fallback for that load and was closed unmerged, which is why be.793 still fails; 1096 is the open macOS-Intel no-logs report, and the arm64 detour fix merged as 1405 (2026-11-05) pending a doorstop release exporting doorstop_jit_memcpy. Verdict for the route decision is unchanged: GO on route B, and the loader blocker is now three named layout gaps with an upstream patch rather than an unmeasured unknown.

## Notes for review

- `task check` is green here (1,622 passed, 6 skipped) once the two gitignored worktree inputs are present: unity/pack-authoring/Assets/Thps (1,438 entries, copied rather than symlinked because .gitignore:326 "unity/*/Assets/Thps/" has a trailing slash and does not match a symlink) and the tools/ost symlink (the ripped OST the preservation baseline fingerprints). Both were verified byte-identical to the main checkout. They are gitignored, so the worktree stays clean.
- `task re:shaders-metal` namespaces its knobs as SHADERS_BUILD/SHADERS_PLATFORM/SHADERS_STAGES/SHADERS_JOBS/SHADERS_OUT/SHADERS_EXTRA: a bare OUT collides with taskfiles/installer.yml's root var, which leaks into the shared Task environment.
- `task re:shaders-pull` reads the rsync source from MEGABONK_LINUX_BUILD_RSYNC in the gitignored .env, so the player box's hostname stays out of tracked files.
- Probing the loader is cheap (about a minute a run) but must stay off the display: -batchmode -nographics, and SIGTERM not SIGKILL, because killing a windowed player leaves a WindowServer "not responding" sheet on the desktop. BepInEx writes an unhandled preloader exception to preloader_<timestamp>.log beside the executable inside Contents/MacOS/, not to BepInEx/LogOutput.log, so a missing LogOutput.log is not by itself a failed injection.

Committed as 1e36f98 (pass, tests, task aliases) and a88a099 (these companion-check findings) on research/task-070-shader-metal-translation.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Scored route B's two open blockers by measurement instead of argument.

Shader translation (the deciding blocker): scripts/shader_metal_pass.py drives all 7,305 GLSL programs from the native Linux build through glslangValidator -> spirv-cross --msl -> xcrun metal -c, behind task re:shaders-metal (with re:shaders-pull for the build input), and prints a JSON summary with per-stage counts and a grouped failure taxonomy. Raw end-to-end 91.57%; with the three mechanical fixes that are now defaults, 7,305 / 7,305 / 7,256 = 99.33%, verdict scriptable. The hand-edit tail is 49 programs in 5 shaders, all one kind of work (uniforms that must move into named blocks). Go: the shader story is scripted translation, and the route decision in docs/development.md stands rather than flipping.

Companion checks: the Unity archive still serves macOS Mono and IL2CPP Build Support for the shipping version 2023.2.22f1, and BepInEx Unity.IL2CPP-macos-x64 is published and current on both channels. The loader was then actually run against a self-built 2023.2.22f1 macOS player under Rosetta: it injects, writes BepInEx/LogOutput.log and generates 80 interop assemblies (16 MB), reaching Chainloader initialized. All failures traced to the app-bundle layout behind a "System platform: Linux 64-bit" misdetection, with the two symlinks that work around it documented and the one remaining by-name game-assembly lookup named (upstream PR 1407, unmerged).

Route B stands, with the shader blocker closed as scriptable work and the loader blocker reduced from an unmeasured unknown to three named layout gaps plus an existing upstream patch.

Tests: 70 in tests/test_shader_metal_pass.py, written before the implementation, over the pure logic (directory parsing, manifest building, diagnostic classification, summary aggregation, verdict thresholds). task check green (1,622 passed, 6 skipped), task mod:test 2,836, task lint clean. Docs: "Shader translation pass" and "Companion checks" under "Static recomp" in docs/development.md.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
