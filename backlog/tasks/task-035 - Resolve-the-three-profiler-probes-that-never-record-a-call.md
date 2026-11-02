---
id: TASK-035
title: Resolve the three profiler probes that never record a call
status: In Progress
assignee: []
created_date: '2026-11-02T07:48:00Z'
updated_date: '2026-11-02T20:41:00Z'
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
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
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
1. [pending] Runtime diagnostics in the mod (gated on DevHarness like the rest of perf): (a) patch-attach report - Harmony.GetAllPatchedMethods() matched against the KnownProbes targets, surfaced in perf status/report as probeAttach; (b) perf census action - live component counts for Enemy, EnemyHpBar, VisualizeTargeting, AnimatedMesh with enabled/activeInHierarchy flags. Pure aggregation logic gets unit tests first.
2. [pending] Static caller scan (one-off, not committed): parse the fedora Windows GameAssembly.dll for E8 rel32 call sites to each probe RVA (target rva - site rip); positive control = Enemy.MyFixedUpdate 0x4AEE90 which must show sites; absence for MyUpdate distinguishes never-called-or-inlined from dispatched.
3. [pending] Reproduce on fedora: relaunch harness, spawn 240, one gated window, read probes + probeAttach + census in the report JSON.
4. [pending] Resolve per finding: ghost components -> drop the probes (and KnownProbes entries) and say so in docs/performance.md; attach failure -> fix the patch target; MyUpdate inlined/uncalled -> drop or retarget to the dispatch site and update the attribution table wording so the three are no longer an open question.
5. [pending] Docs: docs/performance.md replaces the "Three probes recorded zero calls" paragraph and the trailing open item with the settled finding; docs/development.md records the method if a new one was needed.
6. [pending] task scripts:test + dotnet tests green; conventional commit; finalize per guide.

Risks: FindObjectsOfType(Type) interop under Il2CppInterop (fallback: EnemyManager.enemies iteration for Enemy, and Object.FindFirstObjectByType per type); census allocates - only inside harness mode and on demand.
<!-- SECTION:PLAN:END -->
