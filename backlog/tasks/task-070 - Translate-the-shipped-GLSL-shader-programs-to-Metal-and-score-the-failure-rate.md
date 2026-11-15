---
id: TASK-070
title: Translate the shipped GLSL shader programs to Metal and score the failure rate
status: To Do
assignee: []
created_date: '2026-11-15 08:49'
updated_date: '2026-11-15 08:50'
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
- [ ] #1 Every one of the 7,305 GLSL programs is driven through glslangValidator to SPIR-V, spirv-cross --msl, and xcrun metal -c, with a per-stage pass/fail count and failure reasons grouped by kind.
- [ ] #2 The pass lives in the repo under scripts/ behind a task alias, takes the Linux build path as an argument, and prints a machine-readable summary so it can be re-run after a depot push.
- [ ] #3 The report states a go/no-go on route B's shader story: scriptable translation versus translation by hand, with the count of programs that need hand edits and the categories they fall into.
- [ ] #4 The two companion checks have recorded answers: whether Unity 2023.2.22f1 offers macOS Build Support in the archive, and whether the macOS BepInEx IL2CPP build plus doorstop produces BepInEx/interop and LogOutput.log under Rosetta.
- [ ] #5 The outcome is written into the Static recomp section of docs/development.md, correcting the route decision there if the evidence flips it.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
