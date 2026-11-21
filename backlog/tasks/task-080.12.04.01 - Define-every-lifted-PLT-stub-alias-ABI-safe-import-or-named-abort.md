---
id: TASK-080.12.04.01
title: 'Define every lifted PLT stub: alias, ABI-safe import or named abort'
status: Done
assignee: []
created_date: '2026-11-20T20:42:00Z'
updated_date: '2026-11-21T19:03:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - scripts/lift_link.py
  - scripts/lift_abi.py
  - scripts/lift_runtime.py
  - scripts/elf_shim_probe.py
  - TASK-080.12.06
documentation:
  - docs/development.md
modified_files:
  - scripts/lift_sdk.py
  - scripts/lift_imports.py
  - scripts/lift_abi.py
  - scripts/lift_link.py
  - taskfiles/re.yml
  - tests/test_lift_sdk.py
  - tests/test_lift_imports.py
  - tests/test_lift_imports_exec.py
  - tests/test_lift_abi.py
  - tests/test_lift_link.py
parent_task_id: TASK-080.12.04
priority: high
type: enhancement
ordinal: 293000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The linked lifted image of the pinned Linux GameAssembly.so cannot be loaded: 1,753 `sub_<address>` symbols, the PLT stubs, are undefined, and dlopen stops at the first one that is address-taken. Resolving an import by name is not enough to bind it, because a symbol that resolves on macOS can still disagree with Linux on structure layout (a pthread mutex is 40 bytes on Linux and 64 on macOS), so forwarding on the strength of lookup alone corrupts memory silently. This task closes the loading gap without guessing: only imports whose macOS interface provably passes scalars are bound to the host function, and every other stub fails loudly, naming the import and the reason, so a later run shows which services the runtime actually reaches. Compatibility implementations for the ABI-divergent services stay in the parent task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every undefined `sub_<address>` symbol of the dylib produced by `task re:lift-link` on the pinned image has exactly one definition, and `nm -u` on the result lists only libSystem and compiler-rt names.
- [x] #2 A fresh process can dlopen the resulting dylib with no placeholder stubs supplied by the test, and the dylib is still arm64-only.
- [x] #3 A stub for a function the image itself defines forwards to that lifted body.
- [x] #4 An import is bound to the host function only when its macOS prototype is non-variadic, takes and returns only scalars (integers, floating point, or pointers to non-structure types) and fits six integer-class and eight floating-point-class arguments; every other import, and any import whose prototype cannot be found, resolves to a stub that aborts printing the import name and the reason it was refused.
- [x] #5 Executed arm64 tests cover native forwarding of integer, pointer and double arguments and results, an import refused for a structure-pointer parameter, an import refused for being variadic, a stub forwarding to an image body, and the refusal abort naming the symbol.
- [x] #6 A reproducible report lists the disposition and reason of every PLT stub and every distinct import, and developer docs state the eligibility rule with the measured counts.
- [x] #7 The scorer, its verdict of record and every published baseline are unchanged.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Decide eligibility from the macOS SDK, not from name resolution. `scripts/lift_sdk.py` parses the SDK with `clang -Xclang -ast-dump=json` over umbrella translation units and decides each import by the prototype the SDK declares: non-variadic, scalar parameters and result only, at most six integer-class and eight floating-point-class arguments, each argument mapped to an exact register kind (`i32`, `u64`, `f32`, `f64`, `ptr`).
2. Narrow that further than criterion 4, because a scalar argument can still carry a Linux-only number: a function is bound only when it is declared in a value-only libc header (string, strings, ctype, wctype, wchar, math, stdlib, stdio, malloc) and is not in the short list of functions in those headers that take an OS-defined number (`strerror`, `strsignal`, `mkostemp`, and the like). `long double` and narrow integer parameters are refused. The declaring header is tracked across the dump, since clang prints `file` only when it changes.
3. Give every PLT stub one disposition in `scripts/lift_imports.py`: an alias of the image's own lifted body when the image defines the name (and aborts when the defined address is not a body start), a bound host call when the SDK rule passes, otherwise a stub that prints `lift_import_refused: <name>: <reason>` and aborts. A second stub of one bound import aliases the first.
4. Bind at link time, not per call: `lift_abi.Binding` gains an optional `declared_name`, emitted as an asm label (`__asm__("_<name>")` on Mach-O) so the adapter declares the host function under a unique C name without clashing with the libc prototypes the generated source includes. The `lift_` and `sub_` name guard stays.
5. Wire it into `scripts/lift_link.py`: `import_stubs` builds the host source from `lift_runtime.plt_names`, the image's defined symbols and the lifted body starts; `link-imports.json` is the reproducible per-stub and per-import report; the link exits nonzero while any `sub_<address>` is undefined.
6. Verify: executed arm64 tests run every binary as a subprocess with a timeout; a full-image link of the pinned image must show no undefined `sub_` symbol, only libSystem and compiler-rt names in `nm -u`, an arm64-only dylib, and a clean `dlopen` in a fresh process; record the measured counts and write the eligibility rule into `docs/development.md`.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
State at hand-off: the work is implemented and tested but not committed. It lives in a sibling worktree on branch `TASK-080.12.04.01`; main has none of it. Passing: `tests/test_lift_sdk.py` (34), `tests/test_lift_imports.py` (14), `tests/test_lift_abi.py` (29), `tests/test_lift_imports_exec.py` (7, subprocess with timeouts), `tests/test_lift_link.py` (14). The real-image checks are not done, so no acceptance criterion is checked: a full-image link was started into a fresh output directory and stopped at 22 of 65 shard objects (shard objects are written atomically and keyed by identity, so a rerun resumes). Still unmeasured: how many of the 1,753 stubs bind, alias and abort, what `nm -u` lists after the link, and a fresh-process `dlopen`.

An earlier unattended agent run of this task was stopped after three hangs. Its partial work was reviewed and mostly rewritten. Two findings are worth keeping: the thunk and dispatcher machinery it added to `lift_abi.py` is outside this task and was wrong (the thunk overwrote the register-file pointer in `x0`, then looped through the dispatcher), and its execution test loaded an in-process dylib through ctypes with no timeout, so a hang blocked the whole run. Exec tests for this task run the binary as a subprocess with a timeout. The agent had also loosened the `lift_` name guard in `Binding` and the stack-balance check in the export wrapper; both are restored.

Decisions: eligibility is stricter than criterion 4's necessary condition, because a plain integer argument can carry a Linux-only constant (`LC_ALL` is 6 on Linux and 0 on macOS, `CLOCK_MONOTONIC` is 1 and 6, `_SC_NPROCESSORS_ONLN` is 84 and 58), and `long double` is x87 on Linux and a plain double on arm64. macOS declares the printf family in a split header (`_printf.h`), so `printf` is refused as outside the value-only headers while `sprintf` is refused as variadic; both abort when reached. Linux-only names the SDK does not declare, such as `__ctype_b_loc` and `__errno_location`, abort naming the absence; they are likely blockers for the runtime-initialization task and show up in `link-imports.json`.

Remaining: finish the full-image link (`task re:lift-link`), record the measured counts and the eligibility rule in `docs/development.md`, run the full test suite and markdownlint, then commit with a conventional message and no attribution.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every PLT stub of the linked image is now defined as an image alias, an SDK-cleared host call or a named abort. On the pinned image: 1,756 stubs, 1,462 aliases, 76 host calls, 218 aborts. nm -u lists only libSystem and compiler-rt names, the arm64-only dylib loads in a fresh process, and link-imports.json reports every stub and import. The eligibility rule and measured counts are in docs/development.md.
<!-- SECTION:FINAL_SUMMARY:END -->
