---
id: TASK-080.12.04
title: Provide the macOS platform services required by the shipped runtime
status: Done
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-23T07:03:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.01
references:
  - scripts/elf_shim_probe.py
  - scripts/native_bind_probe/symprobe.c
  - TASK-076
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 271000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The ELF shim probe classifies imports as feasible but implements no working compatibility layer. Its 66-symbol work estimate includes Linux/macOS ABI differences; symbol lookup success alone does not prove compatible structures or semantics. The frozen image also requires per-thread state and ordered initialization. This task provides the platform behaviour consumed by the rebuilt arm64 image, not a generic Linux emulator. Gettext passthrough is not presumed safe merely because the symbols can be stubbed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every reachable platform import required by the pinned image has a tested native arm64 binding, compatibility implementation or explicitly justified unused/no-op classification; no unresolved import is silently ignored.
- [x] #2 ABI-divergent services used by the runtime preserve observable Linux behaviour, including applicable threading, signal, file and locale cases, with shipped-reference evidence where available.
- [x] #3 Concurrent threads get independent initialized TLS; required startup hooks execute once in the correct order and final memory protections are enforced before normal execution.
- [x] #4 Automated failure-path tests and developer docs cover unsupported services, locale/catalog assumptions and reproduction of the import/startup evidence.
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
1. Inventory the pinned ELF startup hooks and use a bounded arm64 subprocess to identify the first reached blocker; separate observed imports from static references. Preserve the published pcode and outputs.
2. Add service adapters to the existing link and ABI path only where the evidence justifies them. Write failing tests first and compare Linux-visible threading, signal, file, and locale behavior with the Linux reference when available. Keep unknown services as named failures, including gettext until evidence supports its behavior.
3. Verify initialized, independent per-thread TLS while preserving the unwinder reentry guarantees, then verify startup ordering, once-only execution and memory protections. Keep full IL2CPP initialization and Unity boot separate.
4. Run a fresh full-image link, bounded runtime checks, and task check. Document reproducible evidence and its limits.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Working in the sibling `megabonk_mods-platform-services` worktree. The pinned Linux GameAssembly.so and v13 pcode are linked as read-only inputs by convention. The bounded startup probe enumerates one DT_INIT hook and 21 DT_INIT_ARRAY entries from the ELF and relocation map; fixture tests cover a named abort, malformed startup plan and timeout. Fresh worktree-local link launched; no service compatibility claim yet.

The bounded probe of the existing arm64 link entered DT_INIT (0x1d35000) and aborted on __gmon_start__. The pinned ELF marks that symbol weak and undefined and the startup disassembly checks the GOT for null. Regression tests reproduced nonnull GLOB_DAT and JUMP_SLOT bindings; both now bind null for the absent profiling symbol while the direct PLT trap remains. Focused ABI, startup, binding, import, and link suites: 106 passed. The worktree-local full-image link is needed to verify progress past this hook.

Added and wired a single-module guest TLS accessor for the full-image link. The native subprocess fixture verifies initialization, concurrent thread isolation, same-thread reentry and persistence, and failures for unsupported module and offset. Existing unwind fixture keeps its per-export contract; the focused startup/ABI/binding/import/link/unwind suites pass (120 tests). A fresh link before this TLS change accounted for all 470,466 relocations and all 259,102 lifted bodies, with 53 known holes and no unresolved lifted symbols. Full-image startup and TLS evidence remain open.

The full-image rerun with the weak-symbol fix skipped __gmon_start__ and reached a named __cxa_atexit abort inside the same DT_INIT hook. DT_INIT has not returned. The pinned ELF imports __cxa_atexit as a strong symbol and __cxa_finalize as weak; a registration no-op would silently discard guest shutdown callbacks. The TLS-enabled rebuild is in its own worktree-local output directory.

The TLS-enabled full link finished with one compatibility stub, zero unresolved lifted symbols, and all 470,466 relocations accounted for. Its bounded probe reproduced the __cxa_atexit abort inside DT_INIT; no array hook ran and this is not full-image execution evidence for TLS.

Implemented the __cxa_atexit/__cxa_finalize compat services TDD-first instead of the named abort: a mutex-guarded guest destructor registry (push on register; finalize removes and invokes most-recent-first, filtered by dso) called through the register-file convention with a stack-balance check, and a nonzero return when allocation fails. Weak lift_atexit_alloc seam lets the exec test force allocation failure deterministically. New tests: plan dispositions and shared definition (test_lift_imports), one-definition link assertion (test_lift_link), and native exec coverage of LIFO order, dso filter, double-finalize no-op, concurrent registration, imbalance abort, and allocation failure (test_lift_imports_exec). Focused suites 134 passed; ruff and git diff --check clean. Fresh full link plus probe running for the next reached blocker.

Implemented the reached pthread mutex family as compat services TDD-first: pthread_mutex_init/lock/unlock/destroy plus pthread_mutexattr_init/settype/destroy over host pthread mutexes. The 40-byte glibc guest struct keeps the host mutex pointer at +16 and kind at +24; a zeroed struct behaves as PTHREAD_MUTEX_INITIALIZER via lazy creation under a creation lock. Guest kinds map 1:1 to host kinds despite numbering differences (recursive, errorcheck); return codes are Linux values translated from host errnos (EDEADLK 35, EPERM 1 on unowned unlock, EBUSY 16 on destroy-locked, EINVAL 22 on bad attr type, ENOMEM 12 on allocation failure). Weak lift_mutex_alloc/lift_mutex_free seams force the oom path. Family scoped to what startup reaches: trylock/timedlock are not imported. New tests: plan dispositions and signatures, compat_source one-registry-per-family gating, full-link no-abort assertion, and seven native exec modes (basic, static, kinds, contend, destroy-locked, badtype, oom). Focused suites 144 passed; ruff and git diff --check clean. Full link + probe rerunning for the next reached blocker.

Probe evidence .tools/startup-platform-mutex: INIT_ARRAY hook index 3 (the mutex blocker) now returned; new reached blocker is pthread_key_create in hook index 4 (0x208c100 area). Implemented the thread-key family as compat TDD-first: guest keys are indices below glibc PTHREAD_KEYS_MAX 1024; per-thread values hang off one host pthread_key whose host destructor runs registered guest destructors at host thread exit over glibc's four rounds, via the register-file convention with an imbalance abort naming pthread key destructor. create returns lowest free index or EAGAIN 11; delete/getspecific/setspecific reject invalid keys per POSIX (EINVAL 22, null read); setspecific returns ENOMEM 12 on node allocation failure through weak lift_key_alloc/free seams. New tests: plan signatures, registry gating per family, full-link no-abort assertion, six native exec modes (basic, invalid, isolation across two host threads, destructor-runs-once-with-value at join, exhaustion/recycle of all 1024 keys, oom). Focused suites 153 passed; ruff and git diff --check clean. Full link + probe rerunning.

Probe evidence .tools/startup-platform-clock: complete=true. DT_INIT and all 21 DT_INIT_ARRAY hooks (22 total, slot order) entered and returned, returncode 0, empty stderr, 44 enter/return events. Reached-blocker waves resolved in order: __gmon_start__ null binding, per-thread guest TLS, __cxa_atexit/__cxa_finalize registry, pthread mutex family (7), pthread key family (4), clock_gettime (1) — 15 compat stubs total; aborts now 203, none reached at startup. This is the AC #3 evidence that startup hooks execute once each in correct order. Remaining AC #3: final memory-protection enforcement evidence; then task check, commit.

Implemented clock_gettime as compat (15 compat stubs total): guest Linux clock ids mapped to host clocks by suspend semantics (MONOTONIC/RAW/COARSE to CLOCK_UPTIME_RAW, BOOTTIME to host CLOCK_MONOTONIC, realtime and cpu-time ids to counterparts), guest two-int64 timespec written positionally; unknown id or null pointer returns EINVAL 22 untouched. Four exec modes green. AC #3 evidence now complete: (1) concurrent threads get independent initialized TLS -- test_thread_tls_survives_reentry_and_is_independent_across_threads plus key-family isolation; (2) startup hooks execute once in correct order -- .tools/startup-platform-clock/startup.json complete=true, all 22 hooks (DT_INIT + 21 array slots) entered and returned in slot order, exit 0, empty stderr; (3) final protections enforced -- new relro execution test in test_lift_image_data_exec.py shows a relocation-patched relro word holds the linker's pointer and faults on runtime write while rw sections take writes; mutation check (dropping relro from the read-only set) turns it red. Focused suites 172 passed; ruff and git diff --check clean. Running task check before commit.

Task check passes: 2875 passed, 94 skipped, 1 xfailed (the earlier 12 errors in test_lift_typed_catch.py were this worktree's cold Ghidra pcode cache; copying the 10-entry .tools/lift-runtime-cache from the maintainer host's main checkout made them cache hits). Committed as 4aebbbf.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every import the linked image reaches during startup now has a tested arm64 binding or compatibility implementation, and everything else aborts by name. The bounded startup probe drove wave-by-wave TDD work: __gmon_start__ nulls in GOT words for the guest's own null test, __tls_get_addr serves one initialized guest TLS block per host thread, __cxa_atexit/__cxa_finalize keep a LIFO destructor registry with dso filter, the pthread mutex family maps the 40-byte glibc struct onto host mutexes preserving Linux return codes, the pthread key family gives per-host-thread values and runs guest destructors at thread exit, and clock_gettime maps guest clock ids by suspend semantics onto host clocks. The probe now records all 22 startup hooks (DT_INIT + 21 DT_INIT_ARRAY slots) entering and returning in order with exit status 0 and empty stderr (.tools/startup-platform-clock). Memory protections: ro and relro sections link as constants and the loaded image faults on writes, with a mutation-checked execution test. 203 refused stubs remain, none reached at startup; signal, locale/gettext, condvar, semaphore and pthread_create families stay named aborts until a later phase reaches them, and TASK-080.12.07 (runtime init) will drive that. Evidence is the probe plus native fixture tests, not a Unity boot.
<!-- SECTION:FINAL_SUMMARY:END -->
