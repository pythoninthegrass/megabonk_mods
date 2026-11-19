# PS Vita Forest combat prototype

**Megabonk Vita Combat** (`MBVK00002`) is a standalone feasibility build, not a port of the shipped Unity player. It renders an orthographic 3D Forest graybox as a depth-tested triangle batch through GXM and [libvita2d](https://github.com/xerpi/libvita2d) at 960×544 with no MSAA. It uses original geometry and the Vita system font. The VPK does not bundle commercial game assets or Sony modules and requires no runtime plugins, shader compiler installation, or clock override.

## Build and install

Use VitaSDK 2026.08 with ARM GCC 15.2.0 and the VitaSDK `libvita2d` package. From the repository root, `mise exec -- task vita:combat` builds and validates `.tools/vita-combat/megabonk-vita-combat.vpk`. Override the SDK path with `VITASDK` or the build directory with `VITA_COMBAT_BUILD_DIR`. Run the portable simulation tests with `mise exec -- uv run pytest -n0 tests/test_vita_combat.py`.

Install the VPK with VitaShell or stage it and install it with a development SSH server that supports third-party VPKs. Launch **Megabonk Vita Combat** from LiveArea. This developer-only build uses the SDK's precompiled libvita2d shaders; review linked library distribution requirements before distributing a VPK.

## Physical play check

1. Press Cross at the title. The left stick moves the character; the right stick aims without changing movement. Releasing the right stick retains the most recent aim. The weapon fires automatically.
2. Defeat enemies and move over four cyan XP drops. Combat stops while the upgrade menu is open. Use D-pad Up or Down to highlight **Power** or **Haste**, then press and hold Cross. Level should change from 1 to 2 exactly once, and only the selected stat should change: damage rises from 1 to 2, or the shot interval drops from 18 to 15 simulation ticks. Movement, enemy pursuit, and firing should resume.
3. Start returns to the title. Square and Triangle do not enable benchmark controls during an ordinary run.

## Benchmark setup

Press Triangle at the title. D-pad Left or Right adjusts the live count in increments of 24 (24–240); Up selects **Gathered**, Down selects **Scattered**. Cross starts the run; Square resets it to the same initial state. Start returns to the title. To repeat a matched pair, keep the count unchanged and leave both sticks neutral.

Both layouts use the same enemy geometry, initial HP, AI, weapon targeting and viewport scale. Scattered starts with three times the spacing along both axes. Enemies pursue the player in both cases; the labels describe the initial layouts, not the spacing after pursuit. Benchmark runs do not take player damage or accumulate XP, and a defeated enemy is replaced at its initial position so the selected live count remains constant. Normal Play does not use these rules. This app provides the workload, not a measurement or a full-port viability verdict.

## PCH-2000 verification

Version 01.00 installed and launched on a physical PCH-2000. The playtest confirmed independent movement and aim, automatic combat, XP pickup, a single upgrade application, and resumed combat. Both benchmark layouts ran, and Square restored their starting positions. The tester noticed no performance dips, but the enemy count was not recorded and this version does not capture timing or memory telemetry. This observation does not establish the performance threshold.

## Instrumentation pilot

Version 01.01 adds an automated sweep. Set `VITA_COMBAT_SSH` to the intended console's SSH user and host, then run `mise exec -- task vita:combat:deploy` with the combat app closed. This builds, validates, stages, and reinstalls only `MBVK00002`. It does not update or restart the SSH server. Launch the combat app from LiveArea.

Press Triangle at the title, then Triangle again at **Benchmark Setup**. Leave the app in the foreground, with no overlay or suspend. The pilot runs three pairs at each of 24, 48, 96, 144, 192, and 240 enemies, alternating which layout leads each pair. Each trial resets the simulation, uses neutral controls, and records at least five seconds after a short warmup. The sweep takes about 3½ minutes. Start cancels the sweep and leaves any completed trials on disk.

After **Pilot sweep saved**, return to VitaSSHd if necessary. Pull the new `pilot-*` directory from `/ux0/data/megabonk-vita-combat/` over SFTP. Each trial is written to a separate CSV after the measured window. The CSV includes raw vertical-blank counts and timestamps, enemy and crowding samples summarized as a count range and a near-player sum, clock readbacks, and minimum free MAIN/CDRAM values. The timing hook checks that the queued buffer is current after the display callback's vblank wait; the timestamps are observations after that wait, not hardware scanout timestamps. Missing confirmations invalidate the summary. The summary uses nearest-rank p95 and p99, counts intervals strictly over 33.3 ms, and counts hitches strictly over 50 ms.

Free-pool changes are relative to the first in-process sample, before renderer initialization; they do not include the 8 MiB newlib reservation or other allocations made before that sample. Layout labels describe starting positions; compare the recorded average count within 8 units rather than assuming the contrast survives pursuit. These are pilot data, not a GO/NO-GO decision.

### Physical pilot results

The PCH-2000 completed all 36 neutral-input trials at 960×544. Each held its exact target count and recorded 307 intervals over about 5.122 seconds. Across 11,052 intervals, the vblank count advanced by exactly one every time, with zero failed framebuffer confirmations. Per-trial p95 was 16.728–16.735 ms and p99 was 16.733–16.765 ms. The longest interval was 16.774 ms, with no intervals over 33.3 ms or 50 ms. This establishes that the graybox kept up with display pacing in this pilot, not the amount of unused CPU or GPU time.

At 240 live enemies, the mean number within eight world units was 232.52 Gathered vs. 72.57 Scattered in each repeat. The other five counts also showed a density contrast in every matched pair. All trials sampled peak free-pool decreases of 11 MiB MAIN and 23 MiB CDRAM relative to the in-process baseline. Clock readbacks were 333/222/111/111 MHz (ARM/bus/GPU/crossbar) at the start and end of every trial. These readbacks do not independently rule out external clock overrides or prove total process memory use.

The first pilot's three count fields printed `zu` rather than numbers. Frame counts and both threshold counts were recomputed from the raw CSV rows; recomputed p95, p99, maximum, and duration matched the device summaries in all trials.

## Representative workload check

The approved workload is 96 live enemies, with at least five within eight Vita world units of the player in every sampled Gathered snapshot. The floor comes from active Tier 1 Forest play on Steam build `21750826`: 72 unpaused snapshots had a median live count of 32, a p90 of 103, and a maximum of 134. Two consecutive snapshots near the late-stage peak had 114 and 134 live, with 9 and 14 movement records within 20 desktop units of their target. Desktop target distance is a proxy, not the same measurement or scale as Vita player-relative distance. The 240-enemy sweep remains a stress test.

On version 01.02, press Triangle at the title and Square at **Benchmark Setup**. The six-trial check takes about 35 seconds and writes to a new `gate-*` directory under the same data path as the pilot. **Gate check saved** confirms report export, not a GO verdict. The benchmark isolates timing and density; confirm movement, aim, automatic combat during evasion, XP pickup, and a single upgrade followed by resumed combat separately in ordinary Play.

### Physical workload results

The PCH-2000 completed three matched pairs at 96 live enemies and 960×544. Each trial recorded 307 intervals over about 5.122 seconds. No vblanks were missed and there were no framebuffer confirmation errors or intervals over 33.3 ms. Gathered snapshots had at least 33, 37, and 37 enemies within eight units in the three repeats; Scattered had zero in all sampled snapshots.

| Repeat | Gathered p95 / p99 | Scattered p95 / p99 |
| --- | --- | --- |
| 1 | 16.731 / 16.736 ms | 16.730 / 16.735 ms |
| 2 | 16.732 / 16.738 ms | 16.731 / 16.736 ms |
| 3 | 16.730 / 16.735 ms | 16.730 / 16.735 ms |

Raw intervals reproduce the device's numeric summaries. The clock readbacks matched the pilot at 333/222/111/111 MHz, treated as default for this check rather than independently verified. Minimum measured free memory was 230 MiB MAIN and 89 MiB CDRAM. These are free-pool readings, not process allocation totals; the next section turns them into peak-use bounds.

A separate ordinary Play check on version 01.02 confirmed movement and aim during combat, automatic attacks, XP pickup, and a normal UI selection that applied an upgrade once and resumed combat. Density, timing, and the ordinary Play checks passed.

## Memory accounting

`sceKernelGetFreeMemorySize` reports the free bytes of the pool a process allocates from: `size_user` for the `*_USER_RW` (MAIN) blocks and `size_cdram` for CDRAM blocks. It reports no capacity, and `sceAppMgrGetBudgetInfo`, which would, always fails in a normal application. A free reading therefore says how much of the pool was still unallocated, not how much the app used, and subtracting it from an acceptance limit is only valid after the pool's capacity is established.

The sample points are the first line of `main` (before the renderer, GXM and any benchmark state exist) and every 250 ms inside each measured window. Every trial's minimum includes the initial sample. The app makes no `sceKernelAllocMemBlock`, `malloc` or `calloc` calls of its own: the only allocators are the 8 MiB newlib heap reserved before `main`, and vita2d and GXM during `render_init`. All six gate trials read the same minimum (241,172,480 bytes MAIN, 93,323,264 bytes CDRAM), which fits memory that is allocated once at startup and then static, so the 250 ms cadence cannot have missed a later transient peak. `ATTRIBUTE2` in the built `param.sfo` is 0, so the app has the default budget with no enlargement.

| Pool | Free at first sample | Minimum free | Free at first sample, as a share of the documented budget |
| --- | --- | --- | --- |
| MAIN | 241 MiB (252,706,816 B) | 230 MiB | 15 MiB below 256 MiB |
| CDRAM | 112 MiB (117,440,512 B) | 89 MiB | equal to 112 MiB |

### Establishing the capacities

CDRAM: the first sample is exactly 112 MiB, before anything in the process has touched GXM. That equals the documented default budget byte for byte, so the pool queried is the 112 MiB pool and nothing in it was used before the first sample. MAIN: the first sample is 15 MiB short of the documented 256 MiB. The 8 MiB newlib reservation is known; the eboot image is about 0.4 MiB (`text` 112 KB, `data` plus `bss` 309 KB); the remaining roughly 6.6 MiB (stacks, the SceLibc heap, linked libraries and any system-side bookkeeping) is not itemized. The MAIN capacity itself was not measured independently, so the bounds below are stated under two readings.

### Peak-use bounds

Peak use is capacity minus minimum free, and that subtraction counts every byte missing from the first sample as used, including the 8 MiB newlib reservation and the unitemized remainder, so it includes startup allocations and overstates rather than understates use.

| Reading of the capacity | MAIN peak use | CDRAM peak use |
| --- | --- | --- |
| Documented default budgets (256 MiB, 112 MiB) | at most 26 MiB | at most 23 MiB |
| Largest possible pool: 365 MiB MAIN (the maximum with `ATTRIBUTE2=12`, which this build does not set) and 128 MiB physical CDRAM | at most 135 MiB | at most 39 MiB |

Both readings leave the app far below its limits of 256 MiB MAIN and 112 MiB CDRAM, so the conclusion does not depend on the exact MAIN capacity. These are upper bounds derived from free-pool readings and documented capacities, not a directly measured peak of process allocations.

### Included and excluded

Included: the newlib heap, thread stacks, libraries and any other allocation made from the user MAIN pool before or after the first sample, and every CDRAM allocation (display buffers, GXM and vita2d pools). Excluded: memory the kernel or system services allocate on the app's behalf outside these two pools, PHYCONT memory, and memory that exists only in the 250 ms gaps between samples (none is expected, per the allocator inventory above). The workload is the graybox with 96 live enemies and no game assets; it does not forecast the footprint of a full port.

## Gate verdict

GO for the swarm spike. At 960×544 on the PCH-2000, the 96-enemy Gathered workload (at least 33 enemies within eight units in every sampled snapshot, against a floor of five) ran at p95 16.730–16.732 ms against the 33.3 ms limit, with no missed vblanks or hitches. Peak memory is bounded at 26 MiB MAIN and 23 MiB CDRAM, inside 256 MiB and 112 MiB. The maintainer confirmed movement, aim, automatic combat during evasion, XP pickup and a single upgrade followed by resumed combat in ordinary Play.

Assumptions and limits: the clock readbacks (333/222/111/111 MHz) are treated as the default clocks at the maintainer's direction, not independently verified; the memory figures are upper bounds under the stated capacity readings; and the remaining headroom (at least 230 MiB MAIN and 89 MiB CDRAM) is what a full port's textures, models and audio would have to fit into, which this spike does not test.
