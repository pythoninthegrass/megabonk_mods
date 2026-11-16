---
id: TASK-080.09
title: Compare LLVM optimisation pipelines on lifted code size
status: Done
assignee: []
created_date: '2026-11-16T02:09:00Z'
updated_date: '2026-11-16T16:14:00Z'
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
- [x] #1 The driver gains an option that selects the optimisation pipeline run on each body before `llc`, with the current behaviour (no `opt` pass beyond verify) remaining the default, and a test written first covers the option.
- [x] #2 A table in the "Lifting the shipped code to arm64" section of docs/development.md reports, for at least four pipelines including the current one, the arm64 object bytes per x86 byte and the wall-clock time over the seed-80, 1,000-per-class sample.
- [x] #3 Every pipeline in the table keeps the verifier and arm64 stages at 3,000 of 3,000; any pipeline that breaks a body is reported with the body address.
- [x] #4 The differential test is rerun with the best pipeline applied and still matches native arm64.
- [x] #5 The doc's size statement is updated to the measured best ratio, and `task check` passes.
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
## Completed implementation and verification

1. Resume and preserve the existing lift-080-09-opt-pipelines worktree; inspect the inherited draft and handoff before editing. Keep published baseline directories and proprietary artifacts out of the changes.
2. Keep verify-only/llc-O2 as the default. Add selectable opt pipelines, explicit post-pass verification, raw object-byte accounting, diagnostics, stage timings and full/successful-body denominators. Preserve the emitter unchanged.
3. Validate the exact-sample pcode cache against binary SHA256, ordered addresses/sizes, script fingerprint and Ghidra version. Rebuild partial/stale/malformed samples in one invocation and persist atomically. Remove chunked filling and unrelated radare2 refactoring. Add failing-first regressions for discovered defects.
4. Reuse the validated shared dump for sequential fresh baseline/O1/O2/O3 3,000-body reruns. Retain rejected custom and Os experiments separately; reproduce each original custom failure with actual LLVM stderr.
5. Run both real native-arm64 differential oracles using the production optimisation helper with explicit verification, then provision missing ignored THPS inputs only from preservation-hash-matching local files and run the entire task check gate with isolated deployment.
6. Document four successful pipelines with raw byte totals, corrected denominator, scoring and whole-run timing; preserve the main-branch pcode reuse guidance and explicitly label the unrecorded original cold-dump time. Update the best-size projection to about 275 MB.
7. Review and commit locally with a conventional message; no integration, merge or push without review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Honest handoff assessment (2026-11-16)

The bounded unattended attempt ended without a DONE/BAILED marker and without a commit. It exited early twice; the original four-hour deadline has now passed and no further attempt was launched. The worktree had incorrectly set status Done and checked every AC/DoD despite explicitly admitting that task check was not run. That completion claim is withdrawn. All boxes remain unchecked pending completion/review; this is conservative, not a claim that no implementation exists.

### Independently checked

- `uv run pytest tests/test_lift_probe.py tests/test_lift_probe_review.py -q` in the worktree: **64 passed in 3.39 s**. The run had claimed 66; do not repeat that count without fresh evidence.
- Inspected summary.json and independently summed object bytes in bodies.jsonl. Five final runs share binary SHA256 `a86fd434619dafb328ec741b6bc285992ee1f52e69533b2db8f35185c2ed5ba1`, cache key `5830cb03f777559cbc989102`, 3,000 cache hits, 30 sections, seed 80, 1,000/class, requested = scored = 3,000.
- none: 14,014,640 object bytes, ratio 9.12, scoring 41.0 s, verifier/arm64 3,000/3,000.
- `default<O2>`: 9,351,080 bytes, ratio 6.08, 66.0 s, verifier/arm64 3,000/3,000.
- `default<O3>`: 9,351,112 bytes, ratio 6.08, 181.5 s, verifier/arm64 3,000/3,000.
- sroa,mem2reg,newgvn,instcombine,dce: 9,550,712 successful-object bytes, reported ratio 6.23, 76.2 s, arm64 2,995. Rejected bodies: 0x35f49a0 (960 B), 0x38ceb00 (893 B), 0x477d970 (116 B), 0x47815d0 (84 B), 0x4987580 (1,459 B).
- function(sroa,mem2reg,instcombine,dce): 9,683,472 successful-object bytes, reported ratio 6.34, 203.5 s, arm64 2,995. Rejected bodies: 0x35f49a0 (960 B), 0x38c0ac0 (590 B), 0x38ceb00 (893 B), 0x38d44d0 (520 B), 0x3c265d0 (7,564 B).
- Thus O2 is the best measured fully successful configuration: about 33.3% smaller than verify-only. The byte sums are corroborated by saved rows, not by an independent rerun of all object generation. The custom runs' verifier counts alone must not obscure their failed optimisation/arm64 stages.

### Reported by the run, not independently revalidated

- Added O2 differential test passed with bad=0, preserved lifted symbols and a smaller object.
- Python suite: 2,144 passed and two THPS preservation failures attributed to missing gitignored artifacts; claimed same failures on baseline.
- Ruff, markdownlint and site lint passed.
- Published baseline directories remained untouched.
- None of these claims substitutes for an actual successful task check.

### AC assessment

1. Driver option and regression coverage exist in the draft; targeted tests pass, but final code/test-first review remains.
2. Five-row comparison table exists in draft docs, but needs timing/provenance cleanup and separation of failed experiments.
3. Not met as written: two rows compile only 2,995 bodies, leaving just three fully successful configurations. Failure addresses are recorded.
4. Reported complete by the run, but reviewer has not rerun the actual arm64 differential check.
5. Not met: no full task check; the size statement still foregrounds the obsolete unoptimised extrapolation.
DoD remains unverified overall; there is no conventional implementation commit.

### Recovery artifacts and limits

Branch/worktree: `lift-080-09-opt-pipelines` / sibling `../megabonk_mods-080.09`. Log: sibling `../megabonk_mods-080.09.gnhf.log`. The task plan above is the next-work checklist; do not waste time repeating unrelated pyright experiments from the session log. Inspect current code and actual gate output instead. The primary checkout contains only this handoff update; implementation is still isolated in the worktree. No task implementation was pushed or merged.

Continuation evidence: first full task check succeeded (exit 0, 26.87 s), including 2,858 C# tests and 2,148 Python tests with 9 skips, installer checks and lint. Log/execution status: .tools/lift-probe-check-reviewed/{run.log,execution.json}. Deployment was isolated using the supported ModInstanceFolder environment property; no relaunch. Missing ignored THPS fixture files were copied only after matching preservation-baseline SHA256/size; preservation check passes without refreshing baseline. Additional summary-accounting regression added afterwards, so a final gate rerun is still required.

Both arm64 differential tests passed (exit 0, 7.87 s), using production optimise_body and explicit pre/post verification in the new O2 oracle. Evidence .tools/lift-probe-differential-reviewed/. All ten saved custom-pipeline rejections independently reproduce LLVM 23.1.3 instcombine fixpoint failure after one iteration; stderr retained under .tools/lift-probe-opt-rejection-review/. Os is unsupported by this LLVM and rejected all 3,000 bodies (saved in .tools/lift-probe-opt-os-reviewed/), so O1 is the fourth candidate, not Os. A sequential baseline/O1/O2/O3 rerun is underway under fresh *-verified directories.

New failing-first regressions exposed partial-cache mixing, wrong-size/empty-section cache hits, and discarded LLVM stderr. Fixes now pass targeted tests (67). Whole-sample cache rebuilds are atomic and no longer support chunked analysis. Verified the previous draft's full-sample x86 denominator was wrong: actual sum is 1,537,467 B; lean successful-body denominator 1,533,955 B; func 1,526,940 B. The original cold Ghidra time was not recorded; docs explicitly say so rather than inventing it.

Final verification: task check exit 0 in 18.94 s after all implementation/test/doc edits. .tools/lift-probe-check-final/{run.log,execution.json}: 2,858 C# tests passed; 2,149 Python tests passed with 9 skips; installer checks and all lint passed. Targeted driver/cache suite: 67 passed. Both real arm64 differential tests also passed explicitly; no assertions or gates were weakened. git diff --check passes.

Fresh sequential *-verified runs all request/score/verify/compile 3,000 bodies with 3,000 cache hits, 30 sections, key 5830cb03f777559cbc989102, binary a86fd434619dafb328ec741b6bc285992ee1f52e69533b2db8f35185c2ed5ba1 and x86 denominator 1,537,467 B. none: 14,014,640 object B, 9.12, scoring 45.1 s / whole 52.6 s; O1: 9,495,144 B, 6.18, 61.5 / 69.1 s; O2: 9,351,080 B, 6.08, 61.0 / 68.6 s; O3: 9,351,112 B, 6.08, 60.1 / 67.7 s. Every subprocess exit was 0, with independent byte sums from saved bodies.jsonl. O2 remains smallest (32 B below O3). All samples remain the full seed-80 1,000-per-class draw. Documentation contains only these four fully successful configurations in the main table and separates rejected experiments.

All AC and non-commit DoD items now have evidence. Ready for the conventional local implementation commit; site/node_modules and all ignored proprietary/setup artifacts must remain unstaged. No push or integration performed. Earlier handoff failure assessments are historical and superseded by this final verification.

Conventional implementation commit created locally with subject feat(re): compare LLVM optimisation pipelines on lifted code. All AC and DoD verified; task completed in the existing worktree. Main-branch integration/push remains deliberately pending review.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented selectable post-emission LLVM pipelines with verify-only remaining the default, explicit verification before/after optimisation, raw-byte accounting and diagnostics. Whole-sample pcode caching validates binary/sample/tool identity, redumps invalid samples in one Ghidra invocation and writes atomically.

Four fresh seed-80, 1,000-per-class comparisons all verify and compile 3,000/3,000 bodies. Ratios: baseline 9.12; O1 6.18; O2/O3 6.08. O2 is smallest at 9,351,080 object bytes (33.3% below baseline), projecting roughly 275 MB rather than 410 MB. Docs include raw totals, correct denominators, scoring/whole-run times and separately rejected experiments. The original cold Ghidra wall time was unrecorded and is explicitly not invented.

Validation: 67 targeted tests; both real native-arm64 differential tests; full task check exit 0 (2,858 C# tests; 2,149 Python tests, 9 skips; installer checks and lint). Missing ignored THPS fixtures were supplied only after preservation-hash verification, with no baseline refresh. Published lift baselines and emitter unchanged. Conventional local commit created; no merge or push.
<!-- SECTION:FINAL_SUMMARY:END -->
