---
id: TASK-071
title: Bind the Il2Cpp game runtime by symbol from a standalone macOS host
status: To Do
assignee: []
created_date: '2026-11-15 18:55'
labels:
  - research
  - native
dependencies: []
references:
  - docs/development.md
documentation:
  - 'https://github.com/BepInEx/BepInEx/pull/1407'
  - 'https://github.com/BepInEx/BepInEx/pull/1405'
  - 'https://github.com/NeighTools/UnityDoorstop/pull/114'
modified_files:
  - docs/development.md
priority: medium
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Route B re-hosts the shipped x86-64 Il2Cpp game code on macOS, and both of its shapes need the same primitive: a native host that binds the game runtime by symbol rather than through a mod loader. The loader probe measured the loader half and stopped at a native-hook crash, so this spike takes the loader out of the picture.

Leg 1, the cheap one. Build a standalone macOS x86_64 command-line host that dlopen()s the macOS player's GameAssembly.dylib and calls the exported il2cpp C API by symbol (il2cpp_domain_get, il2cpp_method_get_name at minimum) with no doorstop, no BepInEx and no Dobby in the process. That alone shows the exported surface is usable in-process on this platform and gives a harness that cannot be confused with loader behaviour.

Leg 2, the actual question. Pick a hello-world-able static method from .tools/il2cpp_dump/dump.cs whose result prints, reach it by name from that host through the C API (class handle, method lookup, runtime invoke), and print the value. This is the "can a recomp bind the game runtime by symbol" check that the static-recomp notes list as a prerequisite, and it is the same call path a translated dylib would have to satisfy.

Leg 3, the gate that the loader probe left open. BepInEx's chainloader gates plugin execution on a native detour of il2cpp_runtime_invoke, and on this platform that detour segfaults inside DobbyPrepare, so no plugin loads. Prove or disprove the alternative the same way: install one trampoline of the host's own (mmap or mprotect plus a jump) on an exported il2cpp function in that dylib, then show the patched function still runs correctly afterwards. If a self-authored patch works, a macOS-native mod host does not need BepInEx's detour provider at all; if it fails the same way, hooking is the platform blocker for both routes and the notes should say so.

Report which legs pass into the static-recomp notes with the log and crash evidence, keeping machine identifiers out of tracked files. A player-side spike script belongs under scripts/ behind a taskfile alias so it can be re-run after a depot push, and probe players must stay headless (-batchmode -nographics -logFile) and be stopped with SIGTERM only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A standalone macOS x86_64 host dlopens GameAssembly.dylib and calls il2cpp_domain_get and il2cpp_method_get_name by exported symbol with no doorstop, BepInEx or Dobby loaded, printing real values
- [ ] #2 One static method chosen from dump.cs is reached by name through the il2cpp C API from that host and its returned value is printed
- [ ] #3 One self-authored native trampoline is installed on an exported il2cpp function in that dylib and the patched function still returns correct results afterwards
- [ ] #4 Each leg is scored pass or fail with its evidence (log lines or a crash report signature) rather than by inference
- [ ] #5 docs/development.md records the outcome next to the loader probe notes and states whether a mod host can skip the chainloader runtime-invoke trigger
- [ ] #6 Any reusable spike script lives under scripts/ behind a taskfile alias and runs headless with SIGTERM-only shutdown
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 Probe players are stopped with SIGTERM only and none are left running after the spike
- [ ] #6 No hostname, username or home path appears in tracked files from the spike evidence
<!-- DOD:END -->
