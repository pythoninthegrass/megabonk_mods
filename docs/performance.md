# Performance

What a large enemy population costs in Megabonk, measured in the running game, and how much of that cost the mod owns. Every number here came from the harness profiler described in [Frame-time profiling](development.md#frame-time-profiling); read that section before repeating or extending any of it.

The short version: frame time roughly doubles between an empty level and 240 enemies, and essentially all of that growth is the game's own enemy update and physics. The mod is about one percent of a 240-enemy frame. What the mod did own was a 112 ms single-frame spike, which is fixed.

## Frame time against enemy count

`levels/example-forest.mblevel.json`, tier 4, seed 20261102, vsync off, the player held at the spawn point, twenty-second windows, unpaused frames only, one window per count, same build and same protocol throughout:

| enemies | mean ms | p50 | p90 | p99 | max | mod ms/frame | mod share |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 4.15 | 4.01 | 4.78 | 5.08 | 10.4 | 0.042 | 1.0% |
| 40 | 4.45 | 4.29 | 5.07 | 5.64 | 10.6 | 0.051 | 1.1% |
| 80 | 4.77 | 4.61 | 5.43 | 6.57 | 10.3 | 0.057 | 1.2% |
| 120 | 5.07 | 5.00 | 5.80 | 7.10 | 11.0 | 0.063 | 1.2% |
| 160 | 4.99 | 4.93 | 5.83 | 7.32 | 12.2 | 0.064 | 1.3% |
| 200 | 7.37 | 6.83 | 10.38 | 16.12 | 24.9 | 0.084 | 1.1% |
| 240 | 7.02 | 6.66 | 9.68 | 13.03 | 20.4 | 0.086 | 1.2% |

There is deliberately no fps column. The profiler keeps frame times and nothing else (`FrameBuffer` and `FrameTimeStats` in `src/MegabonkLevels.Mod/perf_stats.cs` report frames, percentiles and the mod's own ms/frame), and a rate derived by dividing the frame count by the window length runs 5–8% above 1000/mean on these same windows, so the "260 to 154 fps" figures in older task notes are not the reciprocal of the mean in this table. Quote milliseconds.

An extra enemy costs about 12 µs of frame time on average (4.15 → 7.02 ms over 240). The curve is not linear: 0 to 160 enemies adds 0.84 ms total, then the 200 and 240 windows jump. The 200-enemy window is the expensive outlier of the two, so the jump is at least partly the swarm's spatial state rather than the count — see [What a window is actually measuring](#what-a-window-is-actually-measuring).

Two things are worth saying about the numbers before using them. At 240 enemies, repeating the same window in the same session gave means of 6.5, 7.0, 7.8 and 9.6 ms, so window-to-window spread is about ±1.5 ms and differences smaller than that in a total frame time are not evidence of anything. Totals per tick, and worst single calls, are far steadier, and those are what the rest of this page leans on.

## Where a 240-enemy frame goes

`ms/frame` is that source's measured time divided by frames in the window. `calls/frame` shows how often it runs: 240 enemies make 83.9 `Enemy.MyFixedUpdate` calls per frame, 0.35 of a call per enemy per frame, which is the 50 Hz fixed update running against the ~143 fps that the 7.02 ms mean implies.

| source | ms/frame | calls/frame | µs/call | worst call ms |
| --- | ---: | ---: | ---: | ---: |
| `EnemyManager.FixedUpdate` (stock) | 0.279 | 0.4 | 793.9 | 2.58 |
| `Enemy.MyFixedUpdate` (stock) | 0.236 | 83.9 | 2.81 | 0.87 |
| `EnemyMovementRb.MyFixedUpdate` (stock) | 0.077 | 83.9 | 0.92 | 0.09 |
| `AnimatedMesh.Update` (stock) | 0.039 | 238.9 | 0.16 | 0.03 |
| `DevHarnessPoll` (mod, diagnostics only) | 0.027 | 1.0 | 27.4 | 7.56 |
| `GrindAssist` (mod) | 0.013 | 1.0 | 13.2 | 0.05 |
| `KillFloor` (mod) | 0.013 | 1.0 | 13.1 | 1.15 |
| `PositionLabel` (mod) | 0.012 | 1.0 | 12.4 | 1.38 |
| `EditorMode` (mod) | 0.010 | 1.0 | 10.5 | 0.03 |
| `AlwaysManager.Update` (stock) | 0.008 | 1.0 | 8.1 | 0.05 |
| everything else measured | 0.016 | — | — | — |

Summing to about 0.7 ms/frame against a 7.02 ms mean: roughly 6.3 ms of the frame is not covered by any probe. That residual is Unity's own work — rendering, the physics broadphase and solver, animation beyond the one probed method, UI rebuilds, and GC — plus any stock code that is not probed. At 0 enemies the four enemy probes measure about 0.001 ms/frame and the residual is the engine's own 4.11 ms, so of the +2.87 ms growth to 240 enemies, 0.63 ms is probed stock enemy work, 0.044 ms is mod work, and about 2.2 ms is inside the engine's unprobed per-enemy cost. Whatever is slow about many enemies is mostly inside the engine, and finding it needs a frame-level profiler, not more Harmony probes.

Three probes recorded zero calls across every window: `Enemy.MyUpdate`, `EnemyHpBar.Update` and `VisualizeTargeting.Update`. This is settled — all three are genuinely not running, and their cost is zero. Harmony's patch report shows every one of the targets attached, so it is not an attach failure; a component census (`perf census`, see [Frame-time profiling](development.md#frame-time-profiling)) against a run with 232 live enemies explains the rest. `EnemyHpBar` exists only as its prefab — 0 components in the scene, 1 loaded asset — and `VisualizeTargeting` is not in the loaded assets at all (0/0/0), so Unity never had a component of theirs to call. `Enemy.MyUpdate` is dead code in this build: the same window recorded 259k calls of its sibling `Enemy.MyFixedUpdate` on those same enemies while the attached `MyUpdate` prefix never fired. The three probes are gone; the patch report (`probeAttach` in every `perf report`/`status`) and the census stay, so a future zero-call probe is classified the same way in one step.

## The mod's share, and what was fixed

The mod's ticks are `KillFloor`, `PositionLabel`, `GrindAssist`, `EditorMode`, `MaxSlopeAngle`, `StartupCover`, `LevelMusic`, `MenuNotice` and `DevHarnessPoll`; the probes are diagnostics and are not part of normal play. Together they measured 0.086 ms of a 7.02 ms frame at 240 enemies.

Turning every mod tick and probe off in the same session gave 6.51 ms against 7.02 ms with them on; before the fixes below, the same control read 7.79 ms off against 7.93 ms on — the control is within the run-to-run spread, in both directions. So the honest claim is that the mod's contribution to total frame time at 240 enemies cannot be separated from noise, and the measured 0.086 ms/frame of its own work is the figure to quote.

Four costs scaled with the enemy population. All four are fixed.

**Collider bounds on every actor, every check.** `KillFloorWatcher` asked each enemy for `collider.bounds.min.y` twice a second, for every enemy, every time. Unity builds a collider's bounds lazily, so on a freshly spawned actor that read rebuilds them; with a few hundred actors it produced a 112.55 ms single call at 120 enemies and 58.41 ms at 160 — the hitch a player would feel as a stall, produced by the mod. The watcher now reads bounds only for an actor whose pivot is within `KillFloor.ColliderProbeMargin` (25 units) of the kill floor, where the collider is what the kill decision actually needs, and reuses its actor and lowest-point dictionaries instead of allocating them per check. The heartbeat's log line also no longer runs a `ToArray().Where(...)` over bosses on every check.

| `KillFloor` tick at 240 enemies | ms/frame | µs/call | worst call ms |
| --- | ---: | ---: | ---: |
| before | 0.022 | 22.1 | 1.73 |
| after | 0.013 | 13.1 | 1.15 |

The worst call across a 120-enemy window went from 112.55 ms to 0.53 ms. The earlier spike did not survive a rerun of the pre-fix build under the fixed protocol (its worst was 0.87 ms), which is itself informative: the spike needs freshly spawned colliders, so it lands in a window whose population grew just before it. It is rare and it is real, and the fix removes the code path that made it possible.

**The actor overlay walking the whole population four times a second.** `PositionLabel` rendered every live enemy's name and position as text. Halving-and-a-bit the cadence (0.25 s to 0.75 s) took it from 0.022 to 0.012 ms/frame at 240, worst call 3.48 ms to 1.38 ms. Nobody reads that overlay faster than that.

**LINQ allocations in the kill decision.** `KillTracker.Select` took an `IEnumerable` of tuples, group-by'd them into a fresh dictionary, and rebuilt the stale-key list with `Where(...).ToList()` on every check — several allocations per check, per population, feeding GC pressure that shows up as periodic frame spikes rather than as average cost. It now takes the watcher's already-keyed `IReadOnlyDictionary<uint, float>` and reuses two scratch collections. Behaviour is unchanged and covered by `tests/MegabonkLevels.Tests/kill_tracker_tests.cs`.

**Repeated `FindAll` in the harness poll** is discussed under [diagnostics](development.md#frame-time-profiling); `DevHarnessPoll` at 0.027 ms/frame is the most expensive mod tick after the fixes, and it exists only to serve the harness.

## What a window is actually measuring

Three findings about the measurement, each of which produced a wrong number before it was understood:

**Enemy count is not the variable; the swarm's shape is.** Teleporting the player to the spawn point gathers the whole population into one dense cluster around them; leaving the player where the run drifted leaves the same 240 enemies strung out across the map. Those two states measured 9.63 ms and 7.02 ms. Physics contacts scale with local density, so a converged swarm is a different benchmark than a scattered one. Windows now teleport the player to a fixed point before each measurement so the counts mean the same thing each time — and note that convergence grows through a session, so later windows in a sweep read high.

**Paused frames are UI frames.** While the level-up screen or a death screen holds the run, Unity keeps rendering at a rate that has nothing to do with gameplay, and those frames are long. The profiler counts them separately; any window with `pausedFrames > 0` is discarded and retaken. Kill-floor deaths award XP, so a long sweep opens reward windows by itself — a 160-enemy window collected 784 paused frames this way before being thrown out.

**A dead player ends a run mid-window.** `perf health` raises `PlayerHealth.hp` and grants Mirror stacks, which stops damage, but the kill floor kills a knocked-off-the-map player through `PlayerHealth.KillPlayer`, which bypasses both. The driver teleports the player back before every window; the health grant alone is not enough.

**Windows read high in the order they were taken.** The capture sweep that filled `/tmp/perf-captures-g` measured the same 240-enemy population three times in a row — mod on, mod off, mod on again — and got 7.482 ms, 7.784 ms, 9.501 ms mean. A second session (`/tmp/perf-captures-s`) repeated it at 8.258 ms, 8.658 ms, 9.376 ms. Cost walks upward through a session regardless of which condition is being measured, and two sessions of the same condition differ by ~0.8 ms, which is the same order as the per-enemy residual attributed in the next section. An A/B whose arms are in a fixed order is measuring the drift as well as the toggle; at this resolution the arms have to be interleaved or taken in separate sessions, and a delta smaller than the session offset is not a result. The same sweep also shows the mod's own toggle is not where the time is: with the mod switched off the frames got ~0.3 ms *slower* while the mod's self-measured cost fell by only 0.056 ms/frame.

## Attributing the unprobed per-enemy cost

The probed stock work and the mod together account for ~0.7 ms of the 6.32 ms mean at 240 enemies (fedora host, offline direct-Proton, tier 4, seed 20261102; numbers below are from the same 20 s gated-window protocol). What is left of the frame is either population-independent, sitting in the 0-enemy baseline, or scales with the enemy count, and separating those two is what a density A/B measures:

**Density A/B: gathered vs strung-out.** Spawning 240 enemies at the player's feet (gathered) vs teleporting the player 150 units away after spawning (strung-out) isolates contact-density-driven cost while keeping enemy count constant:

| density | 0 enemies | 240 enemies | growth vs zero |
| --- | ---: | ---: | ---: |
| gathered (swarm at player) | 4.33 ms | 6.32 ms | +1.99 ms |
| strung-out (player 150 units away) | 4.38 ms | 6.14 ms | +1.76 ms |

Density effect: +0.18 ms (gathered vs strung at 240). This is small — the per-enemy growth is largely density-independent, which means it is per-enemy **update** work (EnemyMovementRb, animator, AI state), not broadphase contacts. The earlier 9.63 vs 7.02 ms density gap (task-029) was measured with the player standing in the middle of the swarm vs leaving the run to run naturally; that is a much wider density spread and a different protocol.

**GC: mod's CLR GC is zero by design.** The `gcPauseMsPerFrame` field on every window read 0.000 ms with 0 collections: the mod's managed (.NET CLR) GC allocates nothing during steady-state frames. The game's own il2cpp Boehm GC has no managed events and is not visible to this sampler — it shows up only as frame-time outliers in the p99/max columns.

**GPU render time: the enemies are about half the frame's GPU work, and the frame is not waiting for them.** `scripts/renderdoc_replay.py` replays the `.rdc` files at `/tmp/perf-captures-g/captures/` and `/tmp/perf-captures-s/captures/` headlessly (no Qt host; see [RenderDoc on a direct-Proton Linux host](development.md#renderdoc-on-a-direct-proton-linux-host)). What that replay supports, and what it does not:

*Per-event GPU duration is not a frame clock.* Summing `EventGPUDuration` over the 0-enemy frame reports 22.8 ms, while the same condition measured 4.88 ms mean / 4.16 ms p50 in the harness — so the replayed figure overstates the real GPU frame by at least 4.7×, and it does not track submitted work either: the two latest captures of a sweep report 101 ms and 74 ms on 0.7–0.9 M submitted vertices while a 2.5 M-vertex frame reports 44.5 ms. This driver offers no whole-frame `Duration` counter to cross-check against (`EnumerateCounters` starts at 1). Read the numbers as a consistent-but-inflated clock, useful only for ratios within one session.

*On that clock, enemy meshes are roughly half the GPU's work.* Matching draw records (method, index count, instance count) between the 0-enemy frame and the 240-enemy frames, 38–54% of the summed per-event GPU time sits in shapes that do not exist at zero enemies (35–47% with the mod off), against a 4.4% churn floor measured between two captures of the *same* condition. The two latest windows of one session read 67–69%, and those are the windows whose totals are demonstrably artefacts. The enemy shapes are indexed draws at 6, 12, 78, 180 and 2,304 indices, about one indexed draw per enemy accompanied by small companion draws.

*The frame is CPU-gated.* Within one session, going from 0 to 240 enemies roughly doubles the summed per-event GPU time (22.8 ms to 44.5 ms) and triples submitted vertices (0.85 M to 2.54 M), while the wall-clock frame rises only 1.6× (4.877 ms to 7.482 ms mean). A GPU holding the critical path cannot absorb twice its work inside a 60% frame increase, so enemy rendering ran with headroom and off the critical path. Its cost is therefore real but not what the measurement is waiting on.

*What does scale per enemy on the CPU side is submission volume:* +0.88 to +1.18 draw calls and +3,405 to +7,022 submitted vertices per enemy (both 240-enemy captures against the 0-enemy control), so every enemy costs a Vulkan draw plus its state setup on the render thread, on top of the engine's per-enemy work on the main and physics threads.

**Attribution summary at 240 enemies, gathered:**

| cost | ms/frame | source |
| --- | ---: | --- |
| zero-enemy baseline (engine, render, non-enemy AI, mod ticks at rest) | 4.33 | 0-enemy window mean |
| probed stock enemy paths | 0.63 | Harmony prefix timers |
| contact-density overhead | ~0.18 | density A/B delta, gathered against strung-out at 240 |
| mod work driven by the population | ~0.04 | mod ms/frame 0.042 at 0 enemies rising to 0.086 at 240 |
| per-enemy CPU-side update, submission and engine overhead (unprobed) | ~1.14 | 1.99 ms growth − 0.63 − 0.18 − 0.04; replay rules GPU render out as the constraint |
| **frame total** | **6.32** | the baseline plus the four growth slices, which is what closes on it |
| mod CLR GC pause | 0.000 | EventListener on GCSuspendEE |

The mod's whole cost at 240 enemies is ~0.10 ms/frame (0.086 measured), not ~0.04: most of it runs at 0 enemies too, so only the part that grows with the population belongs in a growth decomposition and the rest is already inside the 4.33 ms baseline. Quoting the mod's share of a 240-enemy frame, use 0.086 ms/frame, 1.2%.

**Why this says ~1.1 ms where earlier notes said ~2.2 ms.** The 2.2 ms figure is the residual of a different session: 4.15 ms at 0 enemies against 7.02 ms at 240, so +2.87 ms of growth, minus 0.63 ms of probed stock paths and 0.044 ms of mod work. That sweep had no density control and its baseline came from a separate window set. This protocol's growth is 0.88 ms smaller, which is the same order as the ~0.8 ms session-to-session offset and the ±1.5 ms window spread recorded above, so the two are not inconsistent — they are two sessions, and the gated-window density protocol is the one that supports a decomposition because it is the one that measures its own 0-enemy baseline. Quote ~1.1 ms per enemy-scaled frame here; the 2.2 ms figure stands only as "the unprobed part of a 2.87 ms growth measured in another session".

Nothing here is fixed. Each is listed with the number that would have to move.

- **Stock `Enemy.MyFixedUpdate` and `EnemyMovementRb.MyFixedUpdate` are the only meaningful lever**: 2.81 µs and 0.92 µs per call, 84 calls per frame at that population, 0.31 ms/frame, and they carry the steepest slopes of anything measured (1.04 and 0.32 µs per extra enemy). They run at the 50 Hz fixed-update rate. Lowering `Time.fixedDeltaTime`'s cost is not available to a mod, and the game's own movement is a Rigidbody under Unity's physics solver, which is where the unprobed per-enemy time above most likely lives. Any work here means patching stock movement, and the next measurement worth making is the render-only A/B described below, not another frame capture: replayed per-event GPU timings are inflated past usefulness and a Harmony probe has already mapped this region.
- **`AnimatedMesh.Update` runs 239 times a frame at 240 enemies** (0.039 ms/frame, 238.9 calls/frame, 0.16 µs each). Cheap individually, and it scales linearly with no culling visible at this population. If enemy counts are to go higher, this is the second thing after the fixed update to look at, and the lever is animation LOD or culling distance rather than the mod.
- **The ~1.1 ms/frame of per-enemy engine update overhead** sits inside the unprobed engine work — per-enemy AI, Rigidbody physics, animation beyond the probed method — and accounts for most of the +1.99 ms growth from 0 to 240 enemies (after subtracting the probed 0.63 ms stock paths, the ~0.18 ms density-contact cost and the ~0.04 ms of mod work that grows with the population). Replay rules out GPU render as the constraint (above), so it is CPU-side: the engine's per-enemy work plus roughly one Vulkan draw and ~5k submitted vertices per enemy on the render thread. Splitting those two needs a control that neither capture set has: a harness switch that turns off only the enemies' renderers, leaving AI, physics and animation running, measured as a gated window against `count_240`. That is a render-only A/B on the harness's own clock, which is the clock these numbers have to be measured on.
- **Reward-window and death-screen pauses are a gameplay-level frame problem** for anyone who measures or plays at high counts: a window opened mid-run holds `MyTime.paused` and the frames it produces are menu frames. Harness-side handling exists (skip, report, discard); stock menus that pause the run for any other reason would need the same gate.

## Reproducing

The sweep that produced these tables lives in `scripts/perf_sweep.py`; it relaunches the game, loads the level, and takes one gated window per enemy count, writing one JSON per window plus its own rejection reasons. See [Frame-time profiling](development.md#frame-time-profiling) for the verbs it drives and the gates it enforces.
