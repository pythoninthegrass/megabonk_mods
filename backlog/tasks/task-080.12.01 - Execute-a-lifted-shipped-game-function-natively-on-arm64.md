---
id: TASK-080.12.01
title: Execute a lifted shipped game function natively on arm64
status: Done
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T19:15:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.11
references:
  - scripts/pcode_lift.py
  - scripts/lift_probe.py
  - scripts/native_bind_probe.py
  - TASK-080.11
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 268000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Sampled code verifies and compiles, but the current differential tests exercise synthetic C rather than the shipped game. This is the first execution gate for the native build: prove a real shipped method returns correctly on Apple silicon before constructing the whole runtime. InventoryUtility.GetWeaponMaxLevel returning 40 is a candidate already measured through the shipped Linux runtime; resolve its Linux identity from that runtime rather than reusing Windows RVAs. No Unity window, mod loader or full-game boot is required. Preserve binary identity and raw comparison evidence locally.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A bounded, repeatable command executes at least one identified shipped game body rebuilt for arm64 and reports its result and original binary identity.
- [x] #2 The same method's result is captured from the frozen shipped Linux game runtime and compared automatically; the comparison fails on an intentionally wrong candidate result.
- [x] #3 The report proves native arm64 execution without translation, names the exact method/body and distinguishes shipped-game evidence from probe-player evidence.
- [x] #4 Tests cover comparison/report failure cases, and developer docs describe reproduction, limits and the next execution gate.
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
1. Identity: extend scripts/native_bind_probe/host.c leg2 evidence to record the resolved method's methodPointer and the runtime base (dladdr), so the Linux control reports the shipped body's RVA in GameAssembly.so (sha256 a86fd434...5ba1) instead of reusing Windows RVAs. Run it on the Linux player box against InventoryUtility.GetWeaponMaxLevel and keep the raw JSON under .tools/.
2. Lift: dump pcode for that one body through scripts/lift_probe/LiftDump.java, lift with scripts/pcode_lift.py, verify with opt, compile with llc for arm64 (Homebrew LLVM). Inspect the body first; if it has callees or data refs (MethodInfo, static-init check), record exactly what is stubbed so the report names it.
3. Execute: a small C harness (scripts/native_arm64_exec/) links the lifted object, calls the body natively on arm64, prints the result. Report records the binary SHA-256, method, RVA, body size, and proof of no translation (arm64 Mach-O, sysctl.proc_translated == 0).
4. Compare: new scripts/native_exec_probe.py (tests first, tests/test_native_exec_probe.py) with pure functions to parse the Linux control JSON, compare against the arm64 result, and build a report separating shipped-game evidence from probe-player evidence. Comparison must fail on a wrong candidate (--candidate-override for the negative check) and on missing or mismatched identity.
5. Wire a task (task re:native-exec), document reproduction, limits and the next gate (TASK-080.12.02, native/lifted call interop) in docs/development.md, run task check, commit with a conventional message and no attribution.
Risks: the body may not be a pure leaf (static-init guard, MethodInfo arg); the Linux box must be reachable and the game not mid-session (headless probe only, SIGTERM stop).
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `task re:native-exec` (scripts/native_exec_probe.py, scripts/native_exec_probe/harness.c). It resolves InventoryUtility.GetWeaponMaxLevel on the shipped Linux runtime (host.c now records method_pointer/method_rva; RVA 0x225b7d0 in GameAssembly.so sha256 a86fd434...5ba1), lifts the 11 B wrapper and its 237 B callee from that ELF, compiles them for arm64, runs them natively and compares the result (40) with the value il2cpp_runtime_invoke returned on Linux.

Evidence: the run passes six checks (result, body identity, binary digest, native arm64 with sysctl.proc_translated 0 and lipo archs arm64, no stub reached, modelled state equals state observed on Linux). `--candidate-override 7` exits 1; clearing the modelled init guard makes the lifted code reach stub sub_20563d0, showing real control flow executes. Full `task check` passes (2211 passed, 1 skipped); tests in tests/test_native_exec_probe.py cover parsing, each failing check, override, body selection and stubs.

Limits (documented in docs/development.md): the 40 is the null-singleton path, state is modelled for three words the Linux control also observes, and the non-null path (callee 0x2280400) is not exercised. Next gate: native/lifted call interop (080.12.02).
<!-- SECTION:FINAL_SUMMARY:END -->
