---
id: TASK-080.12.04.01
title: 'Define every lifted PLT stub: alias, ABI-safe import or named abort'
status: To Do
assignee: []
created_date: '2026-11-20T20:42:00Z'
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
- [ ] #1 Every undefined `sub_<address>` symbol of the dylib produced by `task re:lift-link` on the pinned image has exactly one definition, and `nm -u` on the result lists only libSystem and compiler-rt names.
- [ ] #2 A fresh process can dlopen the resulting dylib with no placeholder stubs supplied by the test, and the dylib is still arm64-only.
- [ ] #3 A stub for a function the image itself defines forwards to that lifted body.
- [ ] #4 An import is bound to the host function only when its macOS prototype is non-variadic, takes and returns only scalars (integers, floating point, or pointers to non-structure types) and fits six integer-class and eight floating-point-class arguments; every other import, and any import whose prototype cannot be found, resolves to a stub that aborts printing the import name and the reason it was refused.
- [ ] #5 Executed arm64 tests cover native forwarding of integer, pointer and double arguments and results, an import refused for a structure-pointer parameter, an import refused for being variadic, a stub forwarding to an image body, and the refusal abort naming the symbol.
- [ ] #6 A reproducible report lists the disposition and reason of every PLT stub and every distinct import, and developer docs state the eligibility rule with the measured counts.
- [ ] #7 The scorer, its verdict of record and every published baseline are unchanged.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
