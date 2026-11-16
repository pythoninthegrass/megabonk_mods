---
id: TASK-080.12.02
title: Make native and lifted code calls interoperate on arm64
status: Done
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T22:12:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.01
references:
  - scripts/pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - scripts/native_bind_probe/host.c
  - scripts/lift_abi.py
  - scripts/native_call_probe.py
  - tests/test_lift_abi.py
  - tests/test_native_call_probe.py
  - tests/fixtures/lift/calls.c
documentation:
  - docs/development.md
modified_files:
  - scripts/lift_abi.py
  - scripts/native_call_probe.py
  - scripts/native_bind_probe/host.c
  - scripts/pcode_lift.py
  - tests/test_lift_abi.py
  - tests/test_native_call_probe.py
  - tests/fixtures/lift/calls.c
  - taskfiles/re.yml
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 269000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lifted functions currently share a register-state pointer, while Unity, IL2CPP and native imports use native calling conventions. A single successful constant-return method does not establish calls with arguments, nested calls or callbacks. This task delivers the calling-interface contract needed by the rebuilt runtime; image/data relocation and exception unwinding are separate sibling tasks. The shipped Linux runtime remains the reference, and unsupported signatures must be visible rather than silently accepted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Bidirectional native-to-lifted and lifted-to-native calls preserve arguments and results for the signature classes required by the chosen runtime integration, including integer, pointer, floating-point, vector and stack-passed cases.
- [x] #2 Nested calls, indirect dispatch and a native callback into lifted code execute correctly with register/stack state preserved on return.
- [x] #3 Supported aggregate and variadic behaviour is explicitly verified where required; unsupported cases are diagnosed before execution rather than invoked with a guessed signature.
- [x] #4 Automated native arm64 execution tests include shipped-code comparisons, and developer docs record the supported calling contract and remaining exclusions.
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
1. Define the boundary contract before implementation: retain void sub_<address>(register_state*) internally; generate explicitly typed native entry/export and import adapters from a validated signature manifest. Use the compiler's Apple arm64 ABI lowering rather than manually assigning arm64 registers. Present this architecture for approval before coding. Source arguments/results still follow Linux x86-64 SysV layout, including stack slots and the return-address slot. Do not infer a callable signature from a raw address.
2. Write failing unit tests for signature validation and SysV argument/result placement (independent integer/SSE banks, spill ordering and alignment, pointers, float/double, 128-bit vectors). Inventory the runtime integration's actual aggregate/variadic requirements; either implement and execute those signatures explicitly or diagnose them before execution. No guessed aggregate classification or varargs dispatch.
3. Add adapter generation and the minimal lifter call-boundary changes needed for nested direct calls, indirect dispatch and callbacks. Cover guest RSP/return-slot behaviour, caller/callee-saved state and per-invocation callback state. Keep data/image pointer relocation and exception propagation in sibling tasks; indirect tests use explicit registered lifted/native targets, not production image relocation.
4. Extend automated native arm64 execution tests with synthetic x86-64 fixtures compiled/lifted once per test session: both call directions, mixed register banks, integer/SSE spills, nested calls, function-pointer dispatch, and native-to-lifted callback reentry. Require execution and state assertions, not IR-only checks. Reuse validated pcode caches for unchanged shipped bodies.
5. Extend the shipped Linux comparison beyond the constant-return method using identity-resolved methods with nontrivial arguments/results that can run headlessly. Preserve binary digest, method identity, control output, modelled-state exclusions and native execution proof under .tools/. A missing or mismatched control must fail verification, not count as passing synthetic evidence.
6. Document the validated calling contract, signature manifest, rejection behaviour and exclusions in docs/development.md. Run focused tests and task check. Only finalize after behaviour-level evidence meets all acceptance criteria; leave unresolved requirements explicitly open.

Execution outcome: retained the internal register-state ABI and generated typed C imports/exports, with checked dispatch opt-in for indirect calls and recognized tail calls. New execution fixtures live in tests/test_lift_abi.py rather than enlarging the existing leaf differential test. Shipped typed-call verification is a separate task re:native-calls command with exact-body validated pcode caching. The initial headless host API inventory requires scalar/pointer signatures; by-value aggregates and variadics are deliberately unsupported and rejected before generation, not claimed as implemented. Existing runtime-init, image relocation and exception gates remain separate.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial research: prerequisite 080.12.01 is Done. Working tree was otherwise clean before this task's status update. scripts/pcode_lift.py emits direct and indirect calls exclusively as void(ptr %reg); CALLIND currently casts the stored pointer directly, so a native target would be invoked with the wrong ABI. scripts/native_exec_probe/harness.c manually seeds one global register file and stack and only exercises an integer-return no-argument shipped wrapper. tests/test_pcode_lift_differential.py manually marshals register arguments and validates synthetic leaf bodies; it does not establish native imports, callbacks or stack-passed call interop. Host reports arm64. Implementation is gated on approval of explicitly typed generated boundary adapters versus introducing a dynamic FFI.

The maintainer approved the explicitly typed, compiler-lowered native/lifted adapter architecture. Proceed with test-first implementation; no dynamic FFI dependency.

Implemented test-first scripts/lift_abi.py with explicit scalar/pointer/128-bit-vector signatures, SysV independent register banks and aligned stack spills, per-entry guest state, compiler-lowered native imports/exports, and fail-closed target dispatch. Added opt-in checked dispatch for CALLIND and recognized loaded indirect tail calls in pcode_lift.py. Synthetic native arm64 execution covers every accepted kind, void imports, stack overflow cases, nested calls, callbacks, guest callee-saved/return-slot/RSP preservation and SIGABRT for unknown targets. Focused suite: 146 passed.

Added scripts/native_call_probe.py and task re:native-calls. Fresh controls from the frozen shipped Linux runtime identify Mathf.Clamp(float,float,float) at RVA 0x4ab58f0 (17 B) and Clamp(int,int,int) at 0x4ab5910 (15 B), GameAssembly.so SHA-256 a86fd434619dafb328ec741b6bc285992ee1f52e69533b2db8f35185c2ed5ba1. All six cases match native arm64 typed exports with no substituted calls or modelled data. --candidate-override 999 fails as intended; retained negative-report.json locally. Automated shipped comparison reuses validated pcode cache and rejects wrong binary/input/signature identity. Initial host API inventory is scalar/pointer based; by-value aggregates and variadics explicitly reject before generation, and unimplemented runtime-wide integration requirements remain documented exclusions.

Verification: task check passed (2,240 Python tests passed / 1 skipped; 2,858 C# tests passed; build, installer checks, Markdown/Ruff and site Deno lint passed). Focused calling/lifter/probe suite passed 146 tests. task re:native-calls passes all six shipped comparisons and native-arm64 proof, reusing two cached pcode bodies. Candidate override 999 exits nonzero with only the altered comparison false. Completion review maps AC1 to every supported signature kind and mixed register/stack native execution; AC2 to nested/indirect/tail/callback and state-sentinel assertions; AC3 to pre-generation rejection tests and documented unsupported aggregate/vararg contract; AC4 to automated shipped comparison and developer calling-contract documentation.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented typed Linux SysV-to-native arm64 call adapters in scripts/lift_abi.py and opt-in checked indirect/tail dispatch in pcode_lift.py. Native execution tests verify every supported scalar/pointer/128-bit-vector kind, register and stack arguments, nested calls, callback reentry, void imports, callee-saved register/return-slot/RSP preservation and rejection of unknown targets. Aggregate/variadic signatures reject before code generation; the bounded guest stack and remaining runtime integration exclusions are documented.

Added task re:native-calls and an automated shipped-code comparison. Both Mathf.Clamp overloads are resolved through the frozen Linux runtime, tied to the same GameAssembly.so digest and run through generated typed arm64 exports: all six comparisons pass with no substituted calls or modelled state. An intentionally wrong result fails. Validated pcode is reused rather than redumped.

Verification: task check passed (2,240 Python tests, 1 skipped; 2,858 C# tests; build/installer/lint checks). Focused suite: 146 passed. Implementation committed as 489e95a (feat: bridge native and lifted arm64 calls with typed adapters). Raw controls, cached pcode and positive/negative reports remain local under .tools/native-calls/. Image relocation, arbitrary function-pointer rewriting, exception unwinding and Unity/runtime boot remain separate work.
<!-- SECTION:FINAL_SUMMARY:END -->
