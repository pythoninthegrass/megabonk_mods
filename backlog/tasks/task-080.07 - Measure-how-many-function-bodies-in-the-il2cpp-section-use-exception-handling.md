---
id: TASK-080.07
title: Measure how many function bodies in the il2cpp section use exception handling
status: To Do
assignee: []
created_date: '2026-11-16T02:09:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/lift_probe.py
  - scripts/elf_shim_probe.py
parent_task_id: TASK-080
priority: medium
type: spike
ordinal: 262000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The lift emitter ignores C++ exception unwinding entirely: lifted code cannot catch or run cleanups for exceptions. The shipped GameAssembly.so has a 1.1 MB .gcc_except_table and an .eh_frame CIE that names a personality routine, and IL2CPP raises managed exceptions through the C++ runtime, so unwinding is certainly in use. What is not known is how much: if only a small fraction of bodies have landing pads, the problem is contained, and if most do, exception lifting is the dominant remaining cost. This number decides how urgent that work is.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first. scripts/lift_probe.py already derives the function list from .eh_frame with `llvm-dwarfdump --eh-frame` (the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, not on PATH), but that output does not show each frame's exception-table pointer, so a different way of reading it is needed. scripts/elf_shim_probe.py has a stdlib ELF reader that can be reused. The binary is .tools/megabonk-linux-native/Megabonk/GameAssembly.so; the il2cpp section holds 196,137 bodies (75,845 tiny, 100,919 small, 19,373 large). Run the Python tests with `uv run pytest tests/`.

Repo rules that apply: write the failing test first for any parsing code; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: lifting exceptions, and changing the emitter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reproducible command (a task in taskfiles/re.yml or a documented script invocation) reports, for the 196,137 bodies of the il2cpp section, how many have an exception-table (LSDA) pointer, broken down by tiny, small and large.
- [ ] #2 For the bodies that have one, the report also gives the distribution of landing-pad counts (for example none-through-one, two to four, five or more) taken from the exception table.
- [ ] #3 Any parsing helper has unit tests written first, using a small hand-built byte fixture, and `uv run pytest` passes.
- [ ] #4 The results are recorded in the "Lifting the shipped code to arm64" section of docs/development.md, replacing the unquantified statement about exception handling, and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
