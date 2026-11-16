---
id: TASK-076
title: >-
  Spike: load and shim the shipped Linux ELF runtime on macOS, or record that
  Route B fails
status: Done
assignee: []
created_date: '2026-11-15 23:53'
updated_date: '2026-11-16 00:11'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## What was built

- `scripts/elf_shim_probe.py`: stdlib-only ELF64 reader plus four scored legs, no external dependency and no launch.
- `scripts/native_bind_probe/symprobe.c`: the macOS loader oracle. Every `RTLD_DEFAULT` lookup runs before any `dlopen`, so "a library must be opened first" is provable rather than asserted.
- `task re:elf-shim`: scores both Apple targets (`x86_64` and `arm64`) into `.tools/elf-shim-<arch>/summary.json`.
- `tests/test_elf_shim_probe.py`: 71 tests covering the ELF rejections, the loader-probe contract, the curated tables (they may not disagree about a symbol), each leg's pass/fail logic, and the shipped binary's measured shape.

## Measured result

`elf-load-and-shim=feasible`, four legs passing on both targets. The clause that made Route C the fallback did not fire.

| Leg | Result |
| --- | --- |
| imports | 303 unique undefined, all reachable; 221 free, 8 alias, 17 locale-alias, 12 compat, 29 ABI-divergent, 10 weak-noop, 6 loader-owned, 0 unclassified |
| ABI nodes | 12 distinct nodes; 291 live imports bind to one; none stranded |
| relocations | 470,466 in 5 types (466,320 RELATIVE); 0 COPY; 0 IRELATIVE |
| strategy | self-relocate 4 PT_LOAD segments; 51,319,793 B of code; 16 B TLS; 21 init hooks; 240 il2cpp_* exports |

## Findings that corrected the notes

- Version binding is real (291 live imports, 258 to GLIBC_2.2.5) and harmless for a different reason than recorded: the contract is with the Linux loader, and Mach-O has no versioning to satisfy.
- TLS is one DTPMOD64 over a 16-byte PT_TLS, not the TLSDESC cluster assumed.
- The two classic dlopen blockers, COPY and IRELATIVE, are absent outright.
- dlsym accepts the unadorned ELF name; 0 of 247 resolvable imports needed the underscored spelling, and `_malloc` itself fails. A hand-written nlist resolver would not get that courtesy.
- iconv_open/iconv_close exist only in /usr/lib/libiconv.2.dylib; the gettext family has no macOS counterpart at all.

## Not proven, deliberately

Nothing launched, so no claim that the runtime boots, that the 29 ABI-divergent shims behave, that a gettext passthrough is safe, or anything about performance. The 66 shim symbols are a work estimate, not a shim. A `--skip-dyld-probe` run reports `not-scored` rather than `feasible`, because the import legs need the live loader.

## Also in the commit

The probe player's provenance is documented, its import count corrected to 303, and the record made explicit that a universal binary only ever executes its native slice, so an arm64 leg must be scored on Apple silicon. TASK-079 now carries the driver's missing n/a leg status.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
<!-- DOD:END -->
