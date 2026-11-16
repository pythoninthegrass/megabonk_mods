---
id: TASK-080.09
title: Compare LLVM optimisation pipelines on lifted code size
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
  - scripts/pcode_lift.py
  - taskfiles/re.yml
parent_task_id: TASK-080
priority: medium
type: spike
ordinal: 264000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The arm64 objects produced from lifted code are 9.11 times the size of the x86 input, which would put the game code near 410 MB. The probe currently runs only `llc -O2` on the emitter's IR; no IR-level optimisation pass runs before it. The register file is a byte array passed in by pointer, which limits what LLVM can promote, but nobody has measured how much an `opt` pipeline before `llc` recovers, or which passes matter. That number decides whether code size is a real blocker or an artefact of not optimising.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then `score_body` in scripts/lift_probe.py (it pipes the module through `opt -passes=verify` and `llc -O2 -mtriple=arm64-apple-macosx -filetype=obj`) and scripts/pcode_lift.py. Run the probe with `task re:lift-probe LIFT_PER_CLASS=1000` (needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, which is not on PATH; pass `LIFT_EXTRA="--r2-per-class 0"` to skip the radare2 leg). Run the Python tests with `uv run pytest tests/test_lift_probe.py`.

Repo rules that apply: write the failing test first for any driver change; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: redesigning how the emitter models registers or memory, and any change to the emitted IR. Only the passes run after the emitter change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The driver gains an option that selects the optimisation pipeline run on each body before `llc`, with the current behaviour (no `opt` pass beyond verify) remaining the default, and a test written first covers the option.
- [ ] #2 A table in the "Lifting the shipped code to arm64" section of docs/development.md reports, for at least four pipelines including the current one, the arm64 object bytes per x86 byte and the wall-clock time over the seed-80, 1,000-per-class sample.
- [ ] #3 Every pipeline in the table keeps the verifier and arm64 stages at 3,000 of 3,000; any pipeline that breaks a body is reported with the body address.
- [ ] #4 The differential test is rerun with the best pipeline applied and still matches native arm64.
- [ ] #5 The doc's size statement is updated to the measured best ratio, and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
