---
id: TASK-071
title: Bind the Il2Cpp game runtime by symbol from a standalone macOS host
status: Done
assignee: []
created_date: '2026-11-15 18:55'
updated_date: '2026-11-15 23:34'
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
  - taskfiles/re.yml
  - scripts/native_bind_probe.py
  - scripts/native_bind_probe/host.c
  - tests/test_native_bind_probe.py
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
- [x] #1 A standalone macOS x86_64 host dlopens GameAssembly.dylib and calls il2cpp_domain_get and il2cpp_method_get_name by exported symbol with no doorstop, BepInEx or Dobby loaded, printing real values
- [x] #2 One static method chosen from dump.cs is reached by name through the il2cpp C API from that host and its returned value is printed
- [x] #3 One self-authored native trampoline is installed on an exported il2cpp function in that dylib and the patched function still returns correct results afterwards
- [x] #4 Each leg is scored pass or fail with its evidence (log lines or a crash report signature) rather than by inference
- [x] #5 docs/development.md records the outcome next to the loader probe notes and states whether a mod host can skip the chainloader runtime-invoke trigger
- [x] #6 Any reusable spike script lives under scripts/ behind a taskfile alias and runs headless with SIGTERM-only shutdown
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

Spike runs on this macOS box (mini-class, arm64 with Rosetta). The loader-probe bundle is copied off the authoring Mac into gitignored .tools/native-bind/ProbePlayer.app with its BepInEx/ directory excluded, so "no doorstop, BepInEx or Dobby loaded" is true of the inputs as well as the process. Same source builds and runs on the Linux player box for the approved control leg.

## Inputs verified present

- ProbePlayer.app Contents/Frameworks/GameAssembly.dylib: fat x86_64+arm64, adhoc (flags 0x2), links only Foundation/CoreFoundation/Security/libc++/libSystem, no UnityPlayer dependency. 240 exported il2cpp_* symbols including il2cpp_init, il2cpp_set_data_dir, il2cpp_domain_get, il2cpp_domain_get_assemblies, il2cpp_image_get_class(_count), il2cpp_class_from_name, il2cpp_class_get_method_from_name, il2cpp_method_get_name, il2cpp_runtime_invoke, il2cpp_value_box, il2cpp_object_unbox, il2cpp_string_chars. No il2cpp_set_data_paths.
- Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat (2,346,848 B, metadata v29).
- Every exported il2cpp_* symbol is a 16-byte-aligned 10-byte thunk: push rbp; mov rbp,rsp; pop rbp; jmp rel32 -> internal impl. A 14-byte absolute jump therefore fits the slot without touching the neighbouring function.
- dump.cs candidates (image 0 mscorlib.dll): System.Math::Abs(int), System.Int32::Parse(string), System.String::Concat(string,string); UnityEngine.Mathf::Abs(int) in CoreModule.
- Control leg inputs: .tools/megabonk-linux-native/Megabonk/GameAssembly.so (87,741,504 B) and Megabonk_Data/il2cpp_data/Metadata/global-metadata.dat (12,643,320 B).

## Steps

1. Tests first (tests/test_native_bind_probe.py): dump.cs static-candidate extraction, host JSON parsing into leg scores, expected-value matching per return type, loader-cleanliness check over the loaded-image list, patch/trampoline byte encoding, SIGTERM-only shutdown helper.
2. scripts/native_bind_probe/host.c (portable macOS+Linux, -DPLATFORM): dlopen the dylib/so, dlsym by name, set data dir, il2cpp_init, then
   - Leg 1: domain pointer, assembly count, a real il2cpp_method_get_name value, own loaded-library list proving no doorstop/BepInEx/Dobby/CoreCLR, sysctl.proc_translated to prove the x86_64 slice ran under Rosetta.
   - Leg 2: --invoke IMAGE CLASS METHOD ARGC ARGS EXPECTED through class handle -> method lookup -> il2cpp_runtime_invoke, printing the value.
   - Leg 3: read the thunk's jmp rel32 to learn the impl address, mmap an exec page, build a trampoline of the relocated original bytes plus a jump to impl, mprotect the text page, write a 14-byte absolute jump to a counting C hook that tail-calls the trampoline; score = hook fired AND the patched export still returns the correct value; then restore bytes and re-verify. Tries documented exec-memory variants in order (mmap RWX, mmap RW + mprotect RX, MAP_JIT) and reports which step fails.
3. scripts/native_bind_probe.py (PEP 723, same shape as shader_metal_pass.py): builds the host with clang -arch x86_64 (plus an arm64 control), runs each leg and each candidate in its own child so a crash costs one candidate, records exit status/signal and a redacted crash signature, writes JSON to .tools/native-bind/, prints a machine-readable summary. Any player launched goes headless (-batchmode -nographics -logFile) and is stopped with SIGTERM only.
4. taskfiles/re.yml: re:native-bind with NATIVE_BIND_APP / NATIVE_BIND_OUT / NATIVE_BIND_ARCH; the bundle path comes from the gitignored .env so no host paths land in tracked files. Linux control leg behind the same script's --platform linux path plus a taskfile task.
5. Control run: the same host built arm64 native, to separate "macOS refuses self-patching" from "Rosetta refuses self-patching".
6. docs/development.md: score each leg next to the loader probe notes with its evidence, and state whether a mod host can skip the chainloader's il2cpp_runtime_invoke trigger.
7. task check, conventional commit, no attribution.

## Risks

- il2cpp_init outside a Unity player is the main unknown; only il2cpp_set_data_dir is exported, so metadata discovery may need the sibling _Data symlink trick. Candidate data dirs are tried one per child process; if init cannot be made to work that is the Leg 1 verdict with the exact abort line.
- IL2CPP pruning may have stripped the mscorlib/CoreModule candidates from a player whose only managed code is Debug.Log. Fallback: rebuild the probe player from proj/ with one authored static mirroring a dump.cs signature, and record which form satisfied Leg 2.
- Exec-memory allocation and text writes under Rosetta can fail several distinct ways (mmap PROT_EXEC, mprotect, code-signing page-in kill, stale translated block). Each is a result, not a blocker; the host reports the first failing step.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All three legs pass on macOS x86_64 under Rosetta, and legs 1 and 2 pass on the shipped Linux game build as a control.

Leg 1: a standalone C host (scripts/native_bind_probe/host.c) dlopens GameAssembly and resolves the exported il2cpp C API by symbol. Evidence: 343 loaded images with 0 naming a mod loader or second runtime, 11 of the counted exports resolved, il2cpp_init then a non-null domain, corlib reads back "mscorlib.dll", System.Math class name "Math", object size 16, method name "Abs"; proc_translated=1 records the x86_64 slice actually ran translated.

Leg 2: a candidate ladder reaches managed static methods by name through the C API and prints returned values. On the shipped Linux build all 10 candidates pass, including game-shipped assemblies: UnityEngine.Mathf.Abs(-5)=5 (UnityEngine.CoreModule.dll), Rewired.Utils.MathTools.Abs(-42)=42 (Rewired_Core.dll), and game-authored Assembly-CSharp methods InventoryUtility.GetWeaponMaxLevel()=40, ExplorerUtility.IsLinux()=true, MapController.GetStageIndex()=0. On the macOS probe player the 5 mscorlib candidates pass (the probe project has no Rewired or game code).

Leg 3: a self-authored 14-byte absolute jump on exported il2cpp functions, with the original prologue relocated into a trampoline page allocated read-write then made read-execute. Scored hook_calls=1 with baseline, patched and restored results equal: 7/7/7 for il2cpp_runtime_invoke and Abs/Abs/Abs for il2cpp_method_get_name. arm64 records "leg3 needs x86_64 absolute-jump patching" by design.

Conclusion recorded in docs/development.md: a mod host can skip BepInEx's chainloader il2cpp_runtime_invoke trigger. That trigger is the chainloader gating plugin load on its own detour firing; a native host reaches managed code through the exported symbol and diverts the same export with a jump it wrote itself, so no Dobby or funchook provider is needed for binding. Also measured: both binaries export exactly 240 il2cpp_* symbols and zero managed-body symbols, so managed methods are reachable only through the C API, not by dlsym.

Caveat kept honest: Megabonk ships no macOS build, so the macOS legs run against a locally built Unity 2023.2.22f1 IL2CPP universal player with its own 2.3 MB metadata; the shipped binary is exercised on Linux.

Artifacts: scripts/native_bind_probe.py with 161 tests in tests/test_native_bind_probe.py, task re:native-bind, summary.json under .tools/native-bind and .tools/native-bind-linux with machine identifiers redacted.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
- [x] #5 Probe players are stopped with SIGTERM only and none are left running after the spike
- [x] #6 No hostname, username or home path appears in tracked files from the spike evidence
<!-- DOD:END -->
