---
id: TASK-035
title: Resolve the three profiler probes that never record a call
status: Done
assignee: []
created_date: '2026-11-02T07:48:00Z'
updated_date: '2026-11-02T21:06:00Z'
labels: []
dependencies: []
modified_files:
  - src/MegabonkLevels.Mod/perf_probes.cs
  - scripts/perf_sweep.py
priority: low
type: bug
ordinal: 144000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enemy.MyUpdate, EnemyHpBar.Update and VisualizeTargeting.Update recorded zero calls in every measurement window, across populations of 0 to 240 enemies, while the probes on Enemy.MyFixedUpdate, EnemyMovementRb.MyFixedUpdate and AnimatedMesh.Update recorded millions. Either the game does not call those methods on the path a live run takes, or the attribute-based Harmony patch never attaches to them (Il2Cpp interning or inlining, or the method being reached through a different entry point).

Until this is settled, do not treat those three costs as zero in any attribution. Reproduce with scripts/perf_sweep.py --count 240 and read the probes array in the window JSON; the patch installation path is in src/MegabonkLevels.Mod/perf_probes.cs.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach (agreed with Lance 2026-11-02)

Branch perf-035-probe-zero-calls off main (TASK-034 is merged); author on mbp, test on fedora worktree ~/git/megabonk_mods-035 (.env/.venv symlinked, same convention as 034).

Three probes record zero calls: Enemy.MyUpdate, EnemyHpBar.Update, VisualizeTargeting.Update. Evidence so far:
- All three targets exist in dump.cs with unique RVAs (Enemy.MyUpdate 0x4AF410, EnemyHpBar.Update 0x533520, VisualizeTargeting.Update 0x430E20); the patch never threw (no Harmony exception in fedora Latest.log).
- EnemyHpBar/VisualizeTargeting use Unity magic Update (only invoked on active+enabled components); AnimatedMesh.Update, same kind, records millions - so attach works for this class of method. Primary hypothesis: no live enabled instances during a run.
- Enemy has NO MonoBehaviour Update; MyUpdate/MyFixedUpdate are game-dispatched. Enemy has no subclasses and the methods are non-virtual. MyFixedUpdate records (dispatched from EnemyManager.FixedUpdate native loop, direct call); MyUpdate zero. Candidates: never called on the live path, or the call site was C++-inlined by the il2cpp toolchain.

Steps:
1. [done] Runtime diagnostics in the mod (gated on DevHarness like the rest of perf): (a) patch-attach report - Harmony GetPatchInfo per KnownProbes target, surfaced in perf status/report as probeAttach; (b) perf census action - component counts for Enemy, EnemyHpBar, VisualizeTargeting, AnimatedMesh with scene/live/any levels. Pure aggregation logic (PerfProbePlan) got unit tests first.
2. [done] Static caller scan (one-off, not committed): E8 rel32 scan of the fedora Windows GameAssembly.dll. Outcome: ALL FOUR targets (positive control MyFixedUpdate included) have zero direct call sites and exactly one .data function-pointer reference each - dispatch goes through stored pointers, so the scan ruled inlining out for MyUpdate but could not distinguish called-vs-uncalled; the runtime counters do that.
3. [done] Reproduced on fedora: gated 20s window at 240 enemies, fresh offline launch. probeAttach patched=true for all eleven targets (attach failure ruled out); probes array still showed zero calls for the three; census Enemy=232/232/241, EnemyHpBar=0/0/1 (prefab only), VisualizeTargeting=0/0/0, AnimatedMesh=232/232/241.
4. [done] Resolved as ghost/dead code: EnemyHpBar and VisualizeTargeting never instantiate; Enemy.MyUpdate is dead code (259k MyFixedUpdate calls on the same live enemies, attached MyUpdate prefix never fires). Dropped the three probes from perf_probes.cs and KnownProbes; kept the attach report and census verb as the classifier for future zero-call probes.
5. [done] Docs: docs/performance.md replaces the "Three probes recorded zero calls" paragraph with the settled finding and drops the trailing open item; docs/development.md documents the probeAttach array, the census verb, the retired probes, and the --launch-cmd absolute-path/detach requirements for direct-Proton hosts.
6. [done] task check exit 0 (build+tests+lint), 1702 C# and 1014 Python tests green on mbp; conventional commits; finalized per guide.

Risks: FindObjectsOfType(Type) interop under Il2CppInterop (materialized: use the generic form) ; census allocates - only inside harness mode and on demand (accepted).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
fedora worktree ~/git/megabonk_mods-035 set up (branch perf-035-probe-zero-calls, .env/.venv symlinked). Mod compiles and deploys on fedora; 2 interop fixes needed (FindObjectsOfType needs the generic form; Harmony class needs full qualification under the mod's usings). fedora test baseline note: 11 THPS C# tests and 8 Python tests (6 thps + 2 wineserver) fail on fedora's main checkout too - pre-existing per-machine failures from missing thps pack/wine environment, not from this branch. Same suites fully green on mbp (1702 C#, my 5 new PerfProbePlan tests + census command tests included).

Verification (fedora, offline direct-Proton launch via ~/.local/share/scripts/launch-megabonk.sh, recreated for the sweep): gated 20s window at 240 enemies with the diagnostics build -> probeAttach patched=true for all eleven targets, the three probes still zero calls, census Enemy=232/232/241, EnemyHpBar=0/0/1, VisualizeTargeting=0/0/0, AnimatedMesh=232/232/241. After retiring the probes: fresh launch of the final DLL, sweep wrote three gated windows, probes array lists exactly the eight kept probes, attach_count=8 all patched, perf census still counts all four component types (Enemy 240/240/241 in that run). mbp: task check exit 0 (build+tests+lint), 1702 C# tests, full pytest 1014 passed. Binary-scan surprise (corrected in plan): the E8 scan found zero direct call sites even for the positive control MyFixedUpdate - all four methods are reached through stored .data pointers - so static scanning cannot classify zero-call probes; attach report + census + runtime counters can.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Settled the three zero-call probes: all three patches DO attach (Harmony patch report in every perf report/status), so the old "maybe the patch never attached" question is closed. The methods simply never run in a live game: a component census during a 240-enemy window finds EnemyHpBar only as its uninstantiated prefab (scene 0, live 0, any 1), VisualizeTargeting nowhere in the loaded assets (0/0/0), and Enemy.MyUpdate dead on the same 232-240 live enemies that logged ~259k sibling MyFixedUpdate calls. An E8 call-site scan of GameAssembly.dll ruled out inlining (all four probe targets, positive control included, are reached through stored .data pointers rather than direct calls - so static scanning cannot classify zero-call probes; attach report + census + runtime counters can).

Changed: PerfProbes keeps eight probes (the three dead ones and their ProbeTargets/KnownProbes rows are dropped); PerfProbePlan (pure, unit-tested) shapes the probeAttach and census JSON; PerfMonitor.Census counts Enemy/EnemyHpBar/VisualizeTargeting/AnimatedMesh at scene/live/any levels; new perf census harness verb wired through HarnessCommand, dev_harness and run.py. docs/performance.md now states the settled finding where the open question stood and drops the trailing open item; docs/development.md documents the classifier workflow, the census verb, and the --launch-cmd requirements (absolute paths, detached launcher, exported DISPLAY/XAUTHORITY) for direct-Proton hosts.

Verification: fedora gated sweeps before and after the removal - the after-DLL reports exactly eight probes, all patched, and the census still separates live (Enemy 240/240/241) from ghost (EnemyHpBar 0/0/1, VisualizeTargeting 0/0/0). mbp task check exit 0; 1702 C# + 1014 Python tests pass. Follow-up: none open; if a game update ever makes the ghost components live, perf census is the tripwire.
<!-- SECTION:FINAL_SUMMARY:END -->
