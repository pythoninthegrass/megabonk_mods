---
id: TASK-076
title: >-
  Spike: load and shim the shipped Linux ELF runtime on macOS, or record that
  Route B fails
status: To Do
assignee: []
created_date: '2026-11-15 23:53'
updated_date: '2026-11-16 00:10'
labels: []
dependencies: []
references:
  - docs/development.md
  - scripts/native_bind_probe.py
  - .tools/megabonk-linux-native/Megabonk/GameAssembly.so
modified_files:
  - scripts/
  - taskfiles/re.yml
  - tests/
  - docs/development.md
priority: medium
ordinal: 249000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Route B is chosen over Route C in docs/development.md, and that choice rests on one clause: Route C is the fallback if and only if B's ELF-load-and-shim step turns out not to work. That step is the only Route B input never measured. The shader translation pass is scored (7256 of 7305 programs), the runtime bridge is scored (240 il2cpp_* exports bind and invoke with no mod loader), and the OS layer is counted (304 unique undefined symbols and 4498 text relocations against a 64 KB load bias) but nothing has tried to make the shipped x86-64 ELF load on macOS. Lineage: the loader-free binding result closed in backlog/completed.

Score it the way the shader pass scored its blocker: symbol and relocation level, no launch, a JSON artifact with a pass/fail conclusion, behind a re: taskfile alias. Two facts make this non-trivial and both belong in the answer. Rosetta executes Mach-O and not ELF, so translating the .so into a dylib is real work rather than a relink. And the by-symbol result says exactly what the translated artifact must preserve: the 240 exported il2cpp_* entry points and their 16-byte aligned stub layout.

Deliberately out of scope: lifting the 87741 native bodies (that is Route A), and launching the game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Classify every one of the 303 unique undefined symbols in the shipped Linux GameAssembly.so as free, alias, locale-alias, compat-required, ABI-divergent, weak-noop, loader-owned or unclassified
- [ ] #2 Cross-reference each import against the relocations that name it, so an unreachable import is not counted as shim work
- [ ] #3 Score the glibc ABI nodes separately from ordinary symbols, reporting which live imports actually bind to one (measured: 291) and whether any is stranded
- [ ] #4 Verify a compat recipe that names a library by dlopening it, and look up the default scope before any dlopen so a free symbol cannot be mistaken for a recipe
- [ ] #5 Census every relocation by type with a named handling strategy, and treat COPY and IRELATIVE as blockers
- [ ] #6 Decide and justify the load strategy from the segments themselves, scored per target architecture because Apple silicon's 16 KB pages change what can be mapped
- [ ] #7 Report per-node status plus a single conclusion line, scored without launching the runtime
- [ ] #8 Refuse to report feasible when the loader was never consulted
- [ ] #9 Findings recorded in docs/development.md and reproducible through a taskfile alias
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
<!-- DOD:END -->
