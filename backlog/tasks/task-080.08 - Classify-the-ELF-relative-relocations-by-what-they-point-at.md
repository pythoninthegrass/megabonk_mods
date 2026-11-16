---
id: TASK-080.08
title: Classify the ELF relative relocations by what they point at
status: To Do
assignee: []
created_date: '2026-11-16T02:09:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/elf_shim_probe.py
  - scripts/lift_probe.py
parent_task_id: TASK-080
priority: medium
type: spike
ordinal: 263000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Pointers stored in data (vtables, method tables, string literal tables) hold x86 addresses. To rebuild the game code for arm64 those pointers must become references to the lifted functions and to the rebuilt data sections. The shipped GameAssembly.so has 466,320 base-relative relocations that identify exactly these pointers, but nobody has classified them: how many point at a function entry (rewritable to a lifted function symbol), into the middle of a function (harder), at read-only data, writable data or bss, or at nothing known. That split says how mechanical the data rewrite can be.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, and the "Loading and shimming the Linux ELF runtime" section, which already counts the relocations. scripts/elf_shim_probe.py has a stdlib ELF reader and a relocation parser that can be reused. scripts/lift_probe.py shows how function entries are derived from the .eh_frame records (`llvm-dwarfdump --eh-frame` from the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, not on PATH). The binary is .tools/megabonk-linux-native/Megabonk/GameAssembly.so. Run the Python tests with `uv run pytest tests/`.

Repo rules that apply: write the failing test first for any helper code; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: rewriting any relocation or emitting any data, and changing the emitter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reproducible command (a task in taskfiles/re.yml or a documented script invocation) classifies every base-relative relocation by the kind of address it points at: exact function entry, inside a function, read-only data, writable data, bss, other loaded memory, outside every section.
- [ ] #2 The same report breaks the relocations down by the section that holds the pointer (for example the relocation-protected data section, the data section, the GOT).
- [ ] #3 The relocation total printed by the report equals the figure already documented, and a test written first on a hand-built fixture covers the classifier.
- [ ] #4 The counts are recorded in docs/development.md in the "Lifting the shipped code to arm64" section, with one sentence on what the split implies for rewriting data pointers, and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
