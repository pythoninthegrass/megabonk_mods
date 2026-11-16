---
id: TASK-080.12.03
title: Rebuild the game image with relocated data and callable function pointers
status: To Do
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.02
references:
  - scripts/pcode_lift.py
  - scripts/reloc_probe.py
  - scripts/elf_shim_probe.py
  - TASK-080.08
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 270000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Compiled function objects are not a usable runtime image: vtables, method tables and other data still contain x86 addresses. The measured ELF has 466,320 relative relocations, with code targets at function entries and the rest referring to data; the full file has additional relocation types and one callable PLT target. This task preserves data identity and callable pointers for the arm64 image. Calling bridges and platform shims are provided separately; this task must expose its integration requirements, not assume raw x86 pointer values are callable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An image built from the pinned shipped ELF preserves required read-only, writable and zero-filled data, with an auditable mapping from original addresses to rebuilt data or callable entries.
- [ ] #2 Every relocation required by the selected image is accounted for, including the non-relative kinds and callable linker-stub target; missing or ambiguous mappings fail the build.
- [ ] #3 Execution tests demonstrate a relocated data read/write, vtable or method-table dispatch and function-pointer equality/identity behaviour across the rebuilt image.
- [ ] #4 Tests cover relocation bounds, missing targets and section protection requirements; docs and a machine-readable report describe reproduction and coverage.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
