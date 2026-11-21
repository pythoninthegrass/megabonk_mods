---
id: TASK-080.12.03
title: Rebuild the game image with relocated data and callable function pointers
status: Done
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-21T19:35:00Z'
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
- [x] #1 An image built from the pinned shipped ELF preserves required read-only, writable and zero-filled data, with an auditable mapping from original addresses to rebuilt data or callable entries.
- [x] #2 Every relocation required by the selected image is accounted for, including the non-relative kinds and callable linker-stub target; missing or ambiguous mappings fail the build.
- [x] #3 Execution tests demonstrate a relocated data read/write, vtable or method-table dispatch and function-pointer equality/identity behaviour across the rebuilt image.
- [x] #4 Tests cover relocation bounds, missing targets and section protection requirements; docs and a machine-readable report describe reproduction and coverage.
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
Starting state (measured on the pinned image): lift_reloc.plan_image plans 470,155 patches (249,964 callable) and the link emits them, but 309 unbound words (294 JUMP_SLOT in .got.plt, 10 GLOB_DAT in .got incl. data imports stderr/environ/__libc_stack_end, 5 R_X86_64_64 in .data) and 2 rejected words (PLT target 0x50d7278, DTPMOD64 0x50d7398) are only recorded, never fail the build. Every section is emitted as a writable global, and there is no address mapping report.

Steps (tests first, each step red then green):
1. Segment protection: read PT_LOAD/PT_GNU_RELRO flags per section (R, RW, RX; RELRO ends read-only after relocation); record in the section list and report; emit read-only, non-RELRO-written sections as `constant`. Tests: protection derivation from segments, RELRO split, a section with no covering segment fails.
2. Account for every word: bind or explain each unbound word (function import -> its PLT stub alias/host call from lift_imports; data import -> named host data symbol or explicit unbound-by-design with reason), map the PLT-target word to the defined stub entry, map DTPMOD64 to the lifted TLS module id. Anything left unaccounted raises and fails the link (missing and ambiguous included).
3. Audit report: link-relocations.json with, per relocation kind and section, counts plus a per-site mapping (original address -> data section+offset, lifted body or stub entry, or named host binding) and the protection table; keep large per-site detail in a sibling file and summary counts in link-summary.json.
4. Execution tests on a small synthetic ELF-shaped image linked into a dylib: relocated data read/write, vtable/method-table dispatch through patched words, function-pointer equality across two words naming one body, and a read-only section that is genuinely constant.
5. Docs in docs/development.md (reproduction, coverage numbers re-measured with task re:lift-link, integration requirements for bridges/shims), then task check.

Open question to confirm with Lance if it changes scope: how data imports (stderr, environ) should be bound, since the stub work only covers functions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decision (confirmed with Lance): data imports bind to named host variables lift_data_<name> set at load (stderr, environ, __libc_stack_end); weak unprovided imports are null; a strong function import with no stub gets an abort entry lift_import_<name>; a strong data import nothing defines is rejected.

Findings: a PLT stub that aliases an image body is a forwarding function with its own address, so a slot resolved against an image-defined symbol is patched to the body directly (identity preserved) and only a real import resolves to a stub. Ghidra pseudo-sections _tbss (PT_TLS) and EXTERNAL needed explicit classification. The strict gate surfaced __gcc_personality_v0, a function import with no stub, which the earlier plan did not cover.

Verification: real link of the pinned image to .tools/lift-link-data exited 0 with 470,466/470,466 relocations patched, 0 rejected; dylib loads with RTLD_NOW; 4,000 random and all 4,146 non-relative mapped words matched the symbols and sections they name. task check passes (2852 passed, 1 skipped, 1 xfailed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The rebuilt image now accounts for every relocation and keeps section protection. lift_reloc derives protection from the ELF segments (ro, relro, rx, rw, plus tls and external for Ghidra pseudo-sections) and read-only and RELRO sections are emitted as LLVM constants. The new lift_bind binds each word naming an import or PLT entry (lowest same-name stub, named host variable, weak null, or named abort entry), and the TLS module word is the literal 1. link_image refuses a plan with a rejected, unbound or PLT-naming word before compiling anything. task re:lift-link writes link-relocations.json (totals by kind, per-section protection, zero-fill and SHA-256, bound imports) and link-relocation-map.jsonl (original site to rebuilt target for every word). On the pinned image all 470,466 relocations are patched and none rejected; the dylib loads and a sample plus every non-relative word matched. New tests: test_lift_bind.py (unit) and test_lift_image_data_exec.py (vtable dispatch through relocated words, lifted store into a relocated section, zero-filled section, pointer equality, stub and host-variable words, TLS word, write fault in a read-only section). Docs: docs/development.md, Relocated data and callable words. Risks and follow-ups: __libc_stack_end and environ are host-defined and only set at load, real semantics belong to platform services; only sections a body or patch references are defined in the dylib; function-pointer identity between a stub and its aliased body differs by design (forwarding wrapper).
<!-- SECTION:FINAL_SUMMARY:END -->
