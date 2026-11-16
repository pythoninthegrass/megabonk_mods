---
id: TASK-080.06
title: Census of hole kinds on larger samples with new seeds
status: Done
assignee: []
created_date: '2026-11-16T02:09:00Z'
updated_date: '2026-11-16T07:06:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/lift_probe.py
  - taskfiles/re.yml
modified_files:
  - scripts/lift_probe.py
  - tests/test_lift_probe.py
  - docs/development.md
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
- [x] #1 At least two new seeds are run with a per-class count of 5,000 or more each, using separate output directories, and the seeds and counts are recorded.
- [x] #2 A table in the "Lifting the shipped code to arm64" section of docs/development.md compares the seed-80 result with the new seeds: bodies per stage, no-hole percentage per size class, and body counts per hole kind.
- [x] #3 Every hole kind that did not appear in the seed-80 sample is listed with one example body start address and its size.
- [x] #4 Any run failure (Ghidra timeout, out of memory, verifier or llc crash) is recorded with the body address that caused it, and the driver is not left in a state that silently drops such bodies from the totals; a test covers any driver change.
- [x] #5 `task check` passes.
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
1. Prereqs (verified): GameAssembly.so present at .tools/megabonk-linux-native/Megabonk/ (sha256 a86fd434...5ba1), Ghidra 12.1.4 at /opt/homebrew/Cellar/ghidra, keg-only LLVM at /opt/homebrew/opt/llvm/bin, 64 GB / 16 cores. Baseline is the canonical seed-80 run in .tools/lift-probe/summary.json: 3,000 bodies, clean 2,978 (tiny 986, small 992, large 1,000), holes BRANCHIND 21 bodies + JUMPTABLE_TARGET 1 (0x4dd8a20, 312 B). The 98.5% in the task text is the stale pre-CALLOTHER figure in .tools/lift-probe/run.log (2,956); the docs' 2,978 is the number to compare against.
2. Driver hardening first, tests first (AC #4). Today scripts/lift_probe.py can silently shrink its own totals: dump_pcode only fails when pcode.jsonl is absent, so a Ghidra script that dies on one body leaves a short file and every count is computed over fewer bodies with no sign; an exception out of score_body aborts the whole 30-minute run through pool.map before any output is written; opt/llc have no timeout so one pathological body can hang forever. Changes in scripts/lift_probe.py: (a) reconcile(sample, rows) pairs the requested sample with the dump rows in sample order and synthesises a row with an error string and all stages false for any body the dump never emitted; (b) score_body catches exceptions and subprocess timeouts and records them as an error on that body's row with its start address instead of raising; (c) run_tool takes a timeout, --tool-timeout default 120 s on the opt and llc legs; (d) bodies.jsonl is streamed as futures complete so a killed run leaves what it scored; (e) summary gains requested, scored, missing_pcode and a failures list of {start, hex, size, class, error} with tally_failures grouping by kind, and main exits non-zero when a requested body was dropped. Tests in tests/test_lift_probe.py cover (a), (b), (c) and (e).
3. Two new seeds, 5,000 per class, r2 leg off, separate output dirs: LIFT_SEED=81 LIFT_PER_CLASS=5000 LIFT_OUT=.tools/lift-probe-81 LIFT_EXTRA="--r2-per-class 0", same for seed 82. Launched in background in parallel, GHIDRA_HEADLESS_MAXMEM=8G; ~35 min per run plus Ghidra import.
4. Census: for each run read summary.json plus bodies.jsonl, diff hole kinds against seed 80, take one example body (start address + size) per new kind, and record any failure rows.
5. Docs: a comparison table in the "Lifting the shipped code to arm64" section of docs/development.md - seeds and per-class counts, bodies per stage, no-hole percentage per size class, body counts per hole kind, plus the new hole kinds with their example addresses. No task ids, no fix attempted (out of scope).
6. Run uv run pytest tests/test_lift_probe.py, then task check; commit conventional with no attribution; finalise per the finalization guide.
Risk: the large class is 19,373 bodies, so 5,000 per seed draws a third of it - seeds 81 and 82 overlap heavily there by construction; that is expected sampling, not a bug, and the table records the population sizes. Risk: a Ghidra OOM at 15,000 bodies; the reconcile path turns that into recorded per-body failures instead of a silent short sample, and the run can be retried at a smaller per-class count.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Driver hardening, test-first (tests/test_lift_probe.py now 31 tests; full suite 2120 passed, 1 skipped; ruff clean; task check green).

scripts/lift_probe.py: reconcile() pairs the requested sample with the rows Ghidra emitted, so a body the dump never reached becomes a recorded row (missing_dump, every stage false) instead of silently shrinking every count; score_tool turns an opt or llc hang, crash or exec failure into an error naming the tool while an ordinary exit-1 rejection stays a measurement; score_row records anything else that escapes the scorer; new --tool-timeout (default 120 s) bounds one opt or llc run and --ghidra-timeout (default 3600 s) the whole dump; a Ghidra run that times out or exits non-zero keeps the rows it wrote and leaves its console output in <out>/ghidra-stdout.txt; bodies.jsonl is streamed as bodies finish; summary.json gains sample.requested, failures, failed_bodies (start, hex, size, class, error) and unsampled_rows, and main returns 1 when a requested body never reached the scorer. --extra appends arguments to every opt and llc call.

Verified live: a 6-body real-Ghidra run with --extra=--mcpu=neoverse-n1 scores 6 of 6 with no failures; the same run with --tool-timeout 0 records all 6 as "opt timed out after 0s" in failures and failed_bodies with their addresses while keeping them in the totals, and exits 0 because they reached the scorer.

Census runs, both exit 0, same binary sha256 a86fd434...5ba1 as the seed-80 baseline:
- seed 81, .tools/lift-probe-81: requested 15,000, scored 15,000, failures {}, unsampled_rows []; no hole 14,838 (98.92%) - tiny 4,899, small 4,954, large 4,985; holes BRANCHIND 152, JUMPTABLE_TARGET 2, CALLOTHER:movmskps 7, CALLOTHER:pshuflw 1.
- seed 82, .tools/lift-probe-82: requested 15,000, scored 15,000, failures {}, unsampled_rows []; no hole 14,850 (99.00%) - tiny 4,926, small 4,946, large 4,978; holes BRANCHIND 144, JUMPTABLE_TARGET 3, CALLOTHER:movmskps 2, CALLOTHER:pshuflw 1.
Launched as GHIDRA_HEADLESS_MAXMEM=8G task re:lift-probe with LIFT_PER_CLASS=5000 LIFT_SEED=<s> LIFT_OUT=.tools/lift-probe-<s> LIFT_EXTRA="--r2-per-class 0 --tool-timeout 600", the two seeds in parallel.

Seed 80 baseline (.tools/lift-probe/summary.json): 3,000 bodies, no hole 2,978 (99.27%), tiny 986 / small 992 / large 1,000, holes BRANCHIND 21 and JUMPTABLE_TARGET 1 (0x4dd8a20, 312 B). The 98.5% in the task text is the stale pre-CALLOTHER figure kept in .tools/lift-probe/run.log (2,956).

Three samples cover 30,503 distinct bodies (15.6% of the section). Unchanged across runs: every body decodes, verifies and compiles for arm64; no unmapped constant reference; tail-call bodies 193 / 981 / 1,032; indirect-call bodies 906 / 4,516 / 4,592; arm64 object bytes per x86 byte 9.12 / 9.12 / 9.26.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-16T06:16:00Z

---

Starting with the driver hardening AC #4 asks for: reconcile + per-body error capture + tool timeouts, test-first, then the two 5,000-per-class seed runs.

---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Two 15,000-body samples (seeds 81 and 82, 5,000 per class, separate output directories) plus the seed-80 baseline are tabulated in the "Lifting the shipped code to arm64" section of docs/development.md: bodies per stage, no-hole share per size class, and body counts per hole kind. Decoding, the LLVM verifier and the arm64 compile stay unanimous across 33,000 body scores; the hole-free figure holds between 98.92% and 99.27%; the large class, thinly sampled at 1,000 before, carries 15 and 22 holes at 5,000.

Two hole kinds seed 80 never showed, both SSE and both unfixed by design: CALLOTHER:movmskps, smallest carrier 0x4906740 at 43 B and largest 0x48da5c0 at 45,834 B (drawn by both seeds), and CALLOTHER:pshuflw at 0x3ab7dc0 and 0x42f4cb0, both 513 B. Each is recorded with its userop name and its body still verifies and compiles.

The probe no longer loses bodies: the driver pairs the sample it asked for with what Ghidra emitted and records the gap with addresses, and names an opt or llc that hangs or crashes instead of aborting the run or calling a rejection a failure. Committed as c31c918.
<!-- SECTION:FINAL_SUMMARY:END -->
