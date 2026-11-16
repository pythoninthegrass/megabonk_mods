---
id: TASK-080.06
title: Census of hole kinds on larger samples with new seeds
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
  - taskfiles/re.yml
parent_task_id: TASK-080
priority: high
type: task
ordinal: 261000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The no-hole figure (98.5%) and the list of hole kinds come from one sample: 3,000 bodies with seed 80. A rare construct that happens not to appear in that sample would be invisible, and one seed gives no idea how stable the percentages are. The 196,137 bodies in the il2cpp section are 75,845 tiny, 100,919 small and 19,373 large, so the large class in particular is sampled thinly. More samples with other seeds find the holes nobody has seen yet.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/lift_probe.py and taskfiles/re.yml (`re:lift-probe`, variables LIFT_PER_CLASS, LIFT_SEED, LIFT_OUT, LIFT_EXTRA). A 3,000-body run takes about 7 minutes, so a larger run takes proportionally longer; run it in the background. It needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin (not on PATH); pass `LIFT_EXTRA="--r2-per-class 0"` to skip the radare2 leg. Use a separate LIFT_OUT directory per seed so runs do not overwrite each other. Run the Python tests with `uv run pytest tests/test_lift_probe.py`.

Repo rules that apply: write the failing test first for any code change; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: fixing any hole found. List each new kind with an example body address so a separate task can pick it up.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 At least two new seeds are run with a per-class count of 5,000 or more each, using separate output directories, and the seeds and counts are recorded.
- [ ] #2 A table in the "Lifting the shipped code to arm64" section of docs/development.md compares the seed-80 result with the new seeds: bodies per stage, no-hole percentage per size class, and body counts per hole kind.
- [ ] #3 Every hole kind that did not appear in the seed-80 sample is listed with one example body start address and its size.
- [ ] #4 Any run failure (Ghidra timeout, out of memory, verifier or llc crash) is recorded with the body address that caused it, and the driver is not left in a state that silently drops such bodies from the totals; a test covers any driver change.
- [ ] #5 `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
