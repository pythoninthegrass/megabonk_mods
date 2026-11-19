---
id: TASK-084.03
title: Decide GO or NO-GO from the PCH-2000 swarm spike
status: In Progress
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T23:57:00Z'
labels:
  - ps-vita
  - vita-spike
dependencies:
  - TASK-084.02
documentation:
  - docs/performance.md#attributing-the-per-enemy-cost
  - .agents/skills/vita-port/references/measurement.md
parent_task_id: TASK-084
type: spike
ordinal: 288000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
An empty arena, emulator run or reduced-density demo does not establish full-port viability. This decision gates every subsequent subtask, regardless of Backlog dependency status.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Before benchmarking, record a minimum meaningful swarm density and gameplay checks against the pinned reference; use 240 enemies as a desktop comparison point, not an assumed Vita pass threshold.
- [x] #2 At 960×544 and stock clocks on a physical PCH-2000, repeat gathered/scattered runs with matched counts up through 240 or the first documented hardware limit. Record workload, duration, counts, p95/p99, hitches and peak MAIN/CDRAM.
- [x] #3 Record GO only if the representative gathered workload meets p95 ≤33.3 ms within 256 MiB MAIN and 112 MiB CDRAM and preserves the agreed combat feel and upgrade flow; otherwise record NO-GO or leave the gate open while evidence is missing.
- [ ] #4 On NO-GO, stop port work and mark every post-gate subtask Done with all ACs unchecked and a 'Not implemented — NO-GO' summary linking to this decision. Close the parent without checking full-port delivery.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Identify the locally owned Windows reference by Steam build/depot manifest and executable hash; retain game-derived data locally. On the pinned Forest build, record repeatable natural-play enemy counts and local swarm density during sustained pursuit and dodging, plus movement, auto-fire, XP pickup, and upgrade/resume checks. Use those observations to select and agree on the minimum meaningful workload before the first Vita timing run. Treat the previous desktop 240-enemy stress test as a comparison only.
2. Write host tests first for benchmark timing summaries (nearest-rank p95/p99, hitch counts, incomplete-run rejection) and workload validation. Instrument only benchmark mode at 960×544. Use presented-frame intervals if verifiable; distinguish application/submit cadence from presentation and never substitute GPU-only or submit timing for the gate. Capture count and local density through the window, verify clocks, and reconcile sampled MAIN/CDRAM deltas with allocations already present at the baseline. Export raw evidence outside measured windows.
3. At stock clocks on the PCH-2000, run at least three reset matched-count pairs with alternating leading layout, through 240 or the first documented hardware limit. Require an observed density difference, not just different starting labels. Keep inputs, duration, camera, and other work matched; repeat invalid or interrupted windows. Recheck normal Play separately with the hardware controls and no benchmark protections.
4. Record each valid run and the representative gathered verdict against p95 ≤33.3 ms, MAIN ≤256 MiB, CDRAM ≤112 MiB, and the agreed gameplay checks. Leave the gate open for missing or proxy-only evidence. Apply the documented downstream disposition only after an explicit GO or supported NO-GO; do not start full-port work here.

Approved a direct Vita instrumentation pilot before pinning the representative workload. Build, validate, and transfer the existing combat VPK over SFTP; reinstall only the combat title through VitaSSHd and launch from LiveArea because the installed server lacks remote launch. Add an in-app alternating paired sweep and export raw reports after each trial. Label the data pilot and leave the gate open.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started after the combat spike landed locally. The installed combat build has no timing or memory telemetry. Its layouts differ at reset but use identical pursuit and can converge later, so layout labels alone are not evidence of a density contrast. The prior 240-enemy desktop run was synthetic and is not a minimum meaningful Vita workload.

Found the configured local Windows installation: Steam build 21750826, Windows depot 3405342 manifest 446680890915713051. Read SHA-256 digests from the installed executable and GameAssembly.dll. This is the candidate behavioral reference; the historical desktop performance notes do not identify their exact build, so their numbers are comparison context only. No game launch or timed Vita run performed.

The maintainer approved Steam build 21750826 as the pinned behavioral reference and reports no game update since late January 2026. Verify the installed binary identity rather than inferring it from the update date.

The desktop harness state request timed out; the installed reference has not yet been played or sampled for natural swarm density. Added red-to-green host coverage for nearest-rank p95/p99, strict hitch thresholds, incomplete windows, and validation that a matched-count pair retains a density contrast. These helpers are not yet wired into the VPK. No hardware timing or memory results are available.

The pinned shipped Windows player (title screen 1.0.69) ran under plain Wine. The MCP started an unedited example Forest pilot as Calcium (tier 1, stage 0, level seed 20261007) and exited editor mode. Natural spawns and damage were on at time scale 1; no injected spawns, items, or health. Live counts observed: 5 before the first offer, 8 at the first natural XP level-up, 10 after the choice, 14 at a later paused sample. Active EnemyMovementRb distanceToTarget reported 3 within 10 units and 3 within 20 at the first offer, and 3 within 10 and 10 within 20 at the later sample (distance-to-target proxy, not a player-relative geometric census). The first offer opened around 27 seconds, with 19 kills. MCP selected Bone; HUD showed Bone LVL 1 before and LVL 2 afterward, the dialog cleared, and the stage clock/combat advanced. Screenshots retained in gitignored evidence. This was an idle, harness-loaded pilot with normal combat, not a repeatable stock-menu dodging playthrough or an ordinary UI input check. Minimum meaningful density remains unset; no Vita timings taken.

Built and validated combat VPK 01.01 and installed it over the combat title on the physical Vita via the new vitadeploy task (`vita:combat:deploy`). The pilot offers 36 automatically reset trials, three alternating pairs at each of six counts. It records raw vblank/timestamp rows, checks the current framebuffer against each requested flip, and exports clock, density, and free-pool observations outside the timed window. Host tests, VPK validation, and targeted docs lint passed. LiveArea launch and report collection remain unverified.

Retrieved all 36 PCH-2000 pilot CSVs. All held exact live counts and had 307 intervals each (~5.122 s), 11,052 one-vblank increments, and zero framebuffer confirmation errors. Per-trial p95 16.728–16.735 ms, p99 16.733–16.765 ms, max 16.774 ms, zero intervals over 33.3 or 50 ms. At 240, mean near-player count within 8 units was 232.52 gathered vs 72.57 scattered; all matched pairs had a density contrast. The free-pool peak deltas were 11 MiB MAIN and 23 MiB CDRAM after the initial in-process baseline; not total process use. Clock samples were 333/222/111/111 MHz; external overrides were not independently checked. Recomputed counts from raw timestamps because the device printed literal zu for three size_t fields. Changed those fields to unsigned output and validated the local VPK, but did not reinstall this formatting fix. The minimum representative workload, stock-clock confirmation, total allocation accounting, and GO/NO-GO remain open.

Relaunched the pinned local Windows build via the offline Wine task and confirmed that the dev harness answers at the main menu. The macOS session denied assistive access to scripted stock menu/gameplay input; no ordinary Forest run or minimum-density sample was taken. Read-only Vita SSH verified firmware 3.74 and the existence of a PSVshell global fallback profile, with no combat-title profile listed. Both PSVshell and NoPowerLimits appear in the taiHEN config. No configuration was changed; the pilot clock readbacks do not establish Default mode.

Maintainer requested treating current Vita clocks as default for now; record this as an assumption, not an independent verification. Captured a user-driven stock Forest run on pinned Windows build 21750826 at normal damage/spawns/time scale with no injected gameplay. Over 606 real seconds: 102 snapshots, 72 live/unpaused, 70 of 71 consecutive live samples changed player position by more than one unit. Median/p90/max live population 32/103/134; median/p90/max moving enemies within 20 units of their own target 1/5/17. Two adjacent live samples reached 114/134 total and 9/14 within 20. Separate read-only commands can skew counts (maximum observed mismatch 10), and the target-distance proxy does not measure distance to the player directly. A screenshot at 7:58 of stage time showed level 25 and 1,508 kills. Recommend a provisional matched workload of at least 96 live and at least five near the player in an equivalent pursuit range; this is a floor from late play, not an early-run average. Windows and Vita distance scales are not directly equivalent. Keep 240 as stress comparison only. No GO/NO-GO verdict.

The maintainer confirmed Lil Bark was defeated with about 0:03 left on the Forest stage timer and continued into the endless ghosts. The separate late/endless sampler stopped at natural death after 96 real seconds: 17 snapshots, 13 active at time scale 1 and no errors. Active live count median/p90/max was 17/30/34; enemy-reported distance-to-target proxy within 20 units was 3/7/13, respectively. The highest live sample had 34 live (32 active movement records), 9 within 10 and 13 within 20. This short observed endless segment showed close crowding but did not raise the stage-based 96-live proposal or establish a worst-case endless workload.

The maintainer approved the workload floor: 96 live enemies, at least five near the player; 240 remains a stress-test comparison. Compare near-player pursuit pressure at the Vita workload's documented radius, not by equating desktop target-distance units to Vita units. Ordinary Play checks are independent movement and aim, automatic combat while evading enemies, XP pickup, and selecting an upgrade through the normal UI that applies once and resumes play. Approval followed the exploratory instrumentation pilot and precedes the representative gate check.

Added and installed combat build 01.02 with a focused six-trial, three-pair gate check at 96 enemies, recording minimum near-player count at radius eight. Host tests passed and VPK validation was clean. The normal-app VitaSDK header says sceAppMgrGetBudgetInfo is unavailable in normal applications; do not present free-pool deltas as total allocations. Need gate CSV artifacts and explicit memory budget accounting before finalizing.

Pulled six valid gate CSVs, verified summaries from raw vblank/timestamp rows. All trials held 96 live; Gathered minimum local counts were 33/37/37 within eight Vita units, Scattered zero each. Gathered p95 16.730–16.732 ms and p99 16.735–16.738 ms; each trial had 307 intervals, zero hitches, missed vblanks or framebuffer errors. Default clocks assumed per instruction; observed 333/222/111/111 MHz. Minimum observed free pools: 230 MiB MAIN / 89 MiB CDRAM, not process allocation totals. Timing and workload passed; awaiting 01.02 ordinary Play confirmation and total-memory evidence.

The maintainer confirmed all ordinary Play checks on combat build 01.02: movement and aim, automatic combat during evasion, XP pickup, and a normal UI upgrade that applied once and resumed combat. The outstanding verdict evidence is total MAIN/CDRAM use; the user instructed treating clocks as default for this evaluation.

Memory accounting, no new device run needed. sceKernelGetFreeMemorySize reports free bytes only (size_user for MAIN, size_cdram for CDRAM); sceAppMgrGetBudgetInfo always fails in a normal app, so free readings were not subtracted from the limits until capacity was established. Raw gate CSVs: first sample 252,706,816 B MAIN (241 MiB, 15 MiB below the documented 256 MiB) and 117,440,512 B CDRAM (exactly 112 MiB, taken before any GXM use); minimum free 230 MiB MAIN and 89 MiB CDRAM, identical in all six trials. The app makes no AllocMemBlock/malloc calls of its own; allocators are the 8 MiB newlib heap reserved before main and vita2d/GXM at init, so the 250 ms sampling cannot have missed a later transient. param.sfo ATTRIBUTE2 is 0 (default budget). The eboot image is about 0.4 MiB; roughly 6.6 MiB of the MAIN gap is not itemized (stacks, SceLibc heap, libraries, system bookkeeping). MAIN capacity was not measured independently.

Bounds (capacity minus minimum free, counting every byte missing from the first sample as used, so startup allocations are included and use is overstated): documented budgets give at most 26 MiB MAIN and 23 MiB CDRAM; the largest possible pools (365 MiB MAIN, 128 MiB physical CDRAM) give at most 135 MiB and 39 MiB. Both are far inside 256 MiB and 112 MiB, so the verdict does not depend on the exact MAIN capacity. These are upper bounds, not a measured peak of process allocations. Excluded: kernel or system allocations outside these pools, PHYCONT, and anything only present between samples. The graybox has no game assets, so it does not forecast a full port's footprint; the headroom is at least 230 MiB MAIN and 89 MiB CDRAM.

Verdict: GO. p95 16.730-16.732 ms against 33.3 ms with zero hitches and missed vblanks at the approved 96-enemy Gathered workload, memory inside both limits by the bounds above, and ordinary Play checks confirmed by the maintainer on build 01.02. Clocks of 333/222/111/111 MHz are an assumption (treated as default at the maintainer's direction), not independently verified. Details in docs/vita-combat.md under Memory accounting and Gate verdict. task check passes. AC 4 applies to NO-GO only and is not triggered. Downstream subtasks are not started and need separate approval; changes are uncommitted.
<!-- SECTION:NOTES:END -->
