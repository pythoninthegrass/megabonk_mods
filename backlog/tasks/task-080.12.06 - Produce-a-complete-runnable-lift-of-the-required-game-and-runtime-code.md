---
id: TASK-080.12.06
title: Produce a complete runnable lift of the required game and runtime code
status: In Progress
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-18T09:42:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.01
references:
  - scripts/lift_probe.py
  - scripts/lift_holes.py
  - scripts/lift_tail_calls.py
  - scripts/pcode_lift.py
  - TASK-080.01
  - TASK-080.02
  - TASK-080.06
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 273000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The seed-81/82 samples now contain only named control-flow holes, but cover only part of the image and say nothing conclusive about runtime code outside the il2cpp section. A full native build must account for executable code reached by initialization and gameplay, including unrecovered computed jumps and body-boundary cases. This task closes build coverage, not only verifier acceptance. Do not add speculative instruction semantics for unseen operations or guess an unresolved jump is a tail call.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reproducible complete-image report accounts for the pinned game's required executable regions, including runtime code outside il2cpp, and identifies every decoded, lifted, rejected or intentionally excluded body.
- [ ] #2 Every body included in the runnable image has no unresolved semantic/control-flow hole, verifies and compiles for arm64; unhandled bodies block a runnable-build success verdict.
- [x] #3 Recovered indirect control flow and cross-boundary targets have execution tests against the shipped reference, with unresolved and intentionally malformed cases failing safely.
- [x] #4 The build is resumable with validated input/cache identities, preserves published baselines, and docs report actual full-build counts, output size and limitations rather than sample extrapolations.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Measured starting point (pinned Linux GameAssembly.so): executable sections .init (36 B), .fini (14 B), .text (4.38 MB, 62,964 FDE bodies, 458 KB gaps), il2cpp (46.9 MB, 196,137 bodies, 1.65 MB gaps), .plt (28 KB, no FDEs). 259,101 FDEs total, none outside an executable section. Gaps are mostly multi-byte nop padding but must be proven by decoding, not by a byte-set guess (the first-pass byte-set check misclassified 66 2e 0f 1f nops).

Steps:
1. Coverage accounting (AC1): new scripts/lift_image.py with a pure function that, for each executable section, lists FDE bodies and classifies every gap byte range as padding (decoded to nop-only), linker stub (.plt/.init/.fini, named), or unaccounted code. Report JSON keyed on the binary sha256. Tests first in tests/test_lift_image.py using synthetic gap tables.
2. Full-image driver (AC2/AC4): all-bodies mode over the report's body list with a resumable per-body result log keyed on binary digest, dump script fingerprint and Ghidra version; rows already scored are skipped; a stale identity is rejected. Published sample baselines untouched (separate output dir).
3. Run the full dump and scoring; record actual counts, object size, limitations. Any body with a hole or failed stage is listed and blocks a runnable verdict (AC2).
4. Indirect control flow execution tests against the shipped reference (AC3), including unresolved and malformed cases failing safely.
5. Docs in docs/development.md with measured full-build numbers; task check; conventional commit without attribution.

Constraint carried from the subtask: no speculative semantics for unseen ops and no guessing an unresolved jump is a tail call.

Resume the pinned 65-shard build with one Ghidra worker. If shard 21 cannot finish by halving, use bounded smaller ranges and preserve a blocking row for any isolated failure. Validate cached row inventories against requested address/size pairs before using them for a runnable verdict. Keep coverage and build outputs separate from published sample baselines.

Add a blocker-only iteration command over a previous full verdict. Validate the baseline image and cached pcode, checkpoint blocker scores separately with a scorer identity, and require a fresh complete-image run for any runnable verdict.

Separate targeted jump-table recovery from the existing raw pcode baseline. Pilot a bounded, resumable evidence-only pass using explicit body addresses, compare C-disabled recovery against known shipped tables, and leave existing full-image dump identities untouched.

Compare explicit frame-bounded Ghidra functions against inferred functions on known slow and known-good addresses, then sample actual control-flow blockers if the benchmark preserves known tables. Record out-of-body targets without accepting them automatically.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Progress: TASK-080.12.06.01 is done. On the seed-81 and seed-82 draws (15,000 bodies each) BRANCHIND hole bodies fell 152 to 11 and 144 to 26, so the remaining holes in those samples are 11 and 26 BRANCHIND bodies plus 2 and 3 JUMPTABLE_TARGET bodies. The recorded reasons a BRANCHIND site stayed unproven are rsp not at its entry value, rsp untrackable on a path into the site, and no path in the dump reaching the site; the per-site census is in .tools/lift-probe-tailcall4-{81,82}/branchind.json. No acceptance criterion of this task is closed by it: the samples still cover a fraction of the image, and nothing yet accounts for runtime code outside the il2cpp section.

Constraint carried from the subtask: rsp at its entry value does not by itself make a jmp a tail call, since a frameless function with an unrecovered switch has the same rsp. Any later rule that lowers an unresolved jump must also require positive evidence of the target (a load from memory), and must keep the existing tests that pin computed and undefined targets as holes unchanged.

Step 1 done (scripts/lift_image.py, task re:lift-image, tests/test_lift_image.py, docs/development.md 'Accounting for the whole executable image'). Measured on the pinned image: il2cpp 196,137 bodies and .text 62,964 bodies with every inter-body gap decoded to nop padding except five frame-less code ranges: .init 36 B, .fini 14 B, .text start 208 B (four CRT functions, unsplit) and .text end 34 B. .plt is 28,112 B of lazy-binding stubs that bind to imports. coverage_complete is false until those five are lifted or excluded with a reason. AC1 is not closed: the report accounts for bytes but does not yet list per-body decoded/lifted/rejected outcomes.

Remaining: split the 208 B range into its four functions; add all-bodies mode to the driver with a resumable per-body log keyed on binary digest, dump fingerprint and Ghidra version; run the full dump (about 259k bodies; the 15,000-body sample scored in about 260 s, the Ghidra dump time for the full image is unmeasured); AC3 execution tests for indirect control flow; full-build docs.

The 65-shard driver now validates each cache against the requested address/size inventory. A timed-out dump preserves complete JSONL rows and retries only missing ranges; --retry-missing-dump revisits cached failures. Shard 21 yielded 2,167 complete rows before the first retry was interrupted and checkpointed. An audit also found 3,104 missing Ghidra rows in the earlier scored shard 14, so the single-worker resume is recovering both shards. The cached 64-shard aggregate is not the full result: its 255,108 rows contain 252,004 decoded/verified/compiled bodies, 249,445 clean bodies, and 561,241,240 object bytes. Wait for the final summary before publishing whole-image counts.

Shipped-reference execution tests cover a recovered jump table (82 entries and two out-of-range values) at 0x4bd70f0 and an indirect tail jump across FDE body boundaries (0x1d35190 to 0x1d41db0). The Linux x86-64 reference was captured from the same verified image digest; native arm64 output matches. Null and in-body target addresses abort through the checked dispatcher. Existing tests for computed and undefined targets are unchanged. Focused tests pass; full task check and the full-image verdict are pending.

Completed all 65 shards. The first verdict exposed six zero-length frame records sharing starts with real bodies; corrected the inventory and rescored shard 14 from validated pcode. The final report covers 259,102 executable bodies (259,095 nonempty frame records plus seven frame-less functions), with six empty frame records and the import stubs explicitly excluded. All bodies decoded, verified, and compiled for arm64; 256,118 lifted without holes and 2,984 block the runnable verdict. No missing dumps remain. The per-body objects total 581,169,280 bytes, not a linked image. The full report and tested cache reuse support AC1 and AC4; the native differential and rejection tests support AC3. AC2 remains open: the outstanding holes preclude a runnable image. task check passed (2,464 passed, 1 skipped, 1 xfailed); the final documentation also passed Markdown lint. Code and docs commits: 7a7b6fc, cf2ed81, 6477561.

Added --blockers-from for pcode-only rescoring against a complete baseline. It writes separate per-shard checkpoints keyed on the selected pcode, scorer source, LLVM versions, pipeline, and timeout. The subset report cannot claim full-image success. Tests cover baseline validation, reuse and invalidation, and rejection of an invalid pcode identity. The baseline run and full check are in progress.

Blocker-only driver, tests, and usage committed in ebd9ca8. task check passed (2,466 passed, 1 skipped, 1 xfailed).

Added bounded, checkpointed Ghidra jump-table evidence recovery for explicit body addresses in 322e019. The full-image pcode source and cache identities are unchanged; the targeted probe does not promote its evidence into the lifter. In a five-body comparison on the pinned image, C-disabled and C-enabled runs both took 19.7 seconds. Two known tables matched the baseline exactly; 0x2862830 and 0x28629a0 timed out near 5 seconds each, without preventing later bodies from finishing. A checkpoint rerun took 3.1 seconds without Ghidra. task check passed (2,467 passed, 1 skipped, 1 xfailed). AC2 remains open.

Explicit frame-bounded evidence mode and out-of-frame reporting committed in 32d933f. The five-body A/B was 19.7 s bounded vs 19.5 s inferred; inferred function bodies were already in frame, both slow functions timed out, and both tables matched. Of eight actual blockers, three returned no tables, two timed out, and three reproduced known cross-frame targets: 0x4922b60 to 0x4920a40, 0x4dd8b60 to 0x4dd7120, and 0x4e22690 to 0x4e22580. The destinations are exact starts of nonempty frame records, not by themselves proof of a valid tail-call lowering. No baseline changes or blockers cleared. task check passed (2,468 passed, 1 skipped, 1 xfailed).

Decided recovered case lists against the image's own table bytes. `scripts/lift_tables.py` decodes the `lea`/`movslq`/`add`/`jmp *` sequence at a site, takes the entry count from the `cmp $N` plus `ja` guard, and reads base-relative 4-byte or absolute 8-byte entries from the ELF; `lift_jump_evidence.py --baseline` audits a build's tables with it, and `pcode_lift.lift_body(..., evidence=...)` replaces a case list that runs past the body only when every decoded entry is an instruction the dump reported and every Ghidra-only case is a direct branch target of the same body. Auditing the 22 JUMPTABLE_TARGET blockers decoded all of their tables; ten lower over the bytes (0x41488d0, 0x417f8a0, 0x4188f10, 0x47a1a30, 0x4922a20, 0x4922b60, 0x4d8c980, 0x4dd8a20, 0x4dd8b60, 0x4e22690), each a table plus one direct-edge address. The three targets earlier read as cross-frame table cases are not table entries at all. Twelve stay holes: 0x415bfc0, 0x415c400 and 0x415d000 hold one case that is neither entry nor branch target, and the eight money_put/money_get bodies plus 0x243cf40 carry tables whose sites sit past the end of the frame being lifted. Lowering those needs the guard tied to the index register rather than a nearby cmp/ja pair; that change and its full-image re-measurement are open.

Tied the case bound to the switch index and all 22 blockers lower over the table bytes. The bound now has to compare the index register itself, or memory a move between the guard and the indexed load brings into it; a move within the index register (movl %eax,%eax; movzbl %al,%eax) keeps the bounded value, a load from anything else, a store to the compared memory or a call in between loses it, and the operand comparison ignores objdump's `#` symbol comment. Register names are read by canonical 64-bit name, and operand lists split on top-level commas only, so `0x5c(%rsp,%r13)` stays one operand. A table with such a guard names every target its switch has, so Ghidra cases beyond the decoded entries are now dropped when they lie outside the body instead of having to be direct edges; a case on the body's own code that no branch reaches still keeps the hole, which is the cross-check on the entry count. audit.jsonl reports those extras as extra_direct_edges, extra_outside_body and extra_unexplained. Over the 22: every table decoded, 1,206 extras lie outside the lifted frame, ten are direct edges, and the only case the bytes still cannot explain is five addresses in 0x2159b14, whose table also has five entries Ghidra's list omits; none of them blocks, all 22 lift with no holes. summary.json now also carries the tables tally (bodies and tables lowered from the bytes). Full-image rescore over seeded pcode pending.
<!-- SECTION:NOTES:END -->
