# Performance

What a large enemy population costs in Megabonk, measured in the running game, and how much of that cost the mod owns. Every number here came from the harness profiler described in [Frame-time profiling](development.md#frame-time-profiling); read that section before repeating or extending any of it.

The short version: frame time roughly doubles between an empty level and 240 enemies, and essentially all of that growth is the game's own enemy update and physics — turning off only the enemies' renderers, with AI, physics and animation still running, changes the frame by less than the session-to-session offset. The mod is about one percent of a 240-enemy frame. What the mod did own was a 112 ms single-frame spike, which is fixed.

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

Summing to about 0.7 ms/frame against a 7.02 ms mean: roughly 6.3 ms of the frame is not covered by any probe. That residual is Unity's own work — rendering, the physics broadphase and solver, animation beyond the one probed method, UI rebuilds, and GC — plus any stock code that is not probed. At 0 enemies the four enemy probes measure about 0.001 ms/frame and the residual is the engine's own 4.11 ms, so of the +2.87 ms growth to 240 enemies, 0.63 ms is probed stock enemy work, 0.044 ms is mod work, and about 2.2 ms is inside the engine's unprobed per-enemy cost. Whatever is slow about many enemies is mostly inside the engine, and finding it needs a frame-level profiler, not more Harmony probes. That last clause has since been half-answered without one: the controls in [Engine-side A/B: the solver and animation](#engine-side-ab-the-solver-and-animation) take one engine subsystem out at a time and measure what the frame stops paying, which put 0.90–1.34 ms of a leg's growth on the simulated bodies and ≲0.06 ms on animation.

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

## Attributing the per-enemy cost

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

**Render-only A/B: what the frame waits on is not enemy draw submission.** Submission volume says what the render thread is handed, not what the frame clock is charged for it, and the replayed GPU clock cannot settle that (above). The control that can is `perf render --disable`: it sets `Renderer.enabled = false` on every renderer under the live enemies and nothing else, so their AI, Rigidbody and animation components keep running. Only renderers the control disabled are restored, and the rescan runs on population change or a 0.5 s interval, which keeps the control itself at 0.027–0.045 ms/frame while armed and 0.0006 ms/frame while disarmed. Measured on the fedora host, tier 4, seed 20261102, 20 s gated windows, arms interleaved with the leading arm flipped every repeat, two sessions, every window `pausedFrames == 0` and the player teleported to the standing point before it (the largest start offset any window recorded was 4.4 units, which is the swarm shoving the player during the settle, not a failed teleport).

What the control removes, from `--structured` replay of the same leg's captures:

| condition | draw calls | submitted vertices | enemy body shape (2,013 indices, instanced) |
| --- | ---: | ---: | ---: |
| 0 enemies | 745–746 | 772,608–773,178 | 0 draws / 0 vertices |
| 240, render on | 994–1,004 | 2,026,260–2,052,171 | 8–9 draws / 889,746–966,240 |
| 240, render off | 892–940 | 829,788–859,902 | 0 draws / 0 vertices |

The enemy shapes drop to exactly the zero-enemy value with the cull armed, and 93–96% of the enemy-attributable submitted vertices go with them. Draw calls fall only from +248/+259 above baseline to +146/+195 because 240 enemies are instanced into a handful of draws; what is left above the baseline is shape churn present with *and* without enemies (a 2,304-index shape at 23–55 k, the shared 4,812 and 4,020-index shapes), not enemy meshes. The two arms measure the same population: `enemiesLast` 240 in both, `enemyPositionSum` still advancing while culled, pool 240/550 in both, and the same spread of combat deaths, so the toggle changes neither despawn nor pool behaviour.

Frame time from the same protocol, two sessions, mean ms per window (the 0-enemy column pools both arms, which are one condition at zero population):

| leg | 0 enemies | 240 render on | 240 render off | `on − off` per pair |
| --- | --- | --- | --- | --- |
| A | 5.15–5.31, mean 5.22 | 9.19–9.99, mean 9.60 | 9.32–9.79, mean 9.54 | −0.13, +0.49, −0.16 |
| B | 5.13–5.31, mean 5.25 | 9.10–9.64, mean 9.39 | 9.84–12.48, mean 11.08 | −0.20, −3.38, −1.51 |

Leg A puts enemy render submission at **−0.61 to +0.66 ms**, inside the ~0.8 ms session-to-session offset: not a result, and reported as unmeasurable rather than as a number. Leg B's off arm read *slower* than its on arm, which removing work cannot cause — its three off windows are the ones in which the swarm carried the player 35 to 178 units from the standing point, and pathing after a moving target is exactly the work that grows (its r2 window sampled 1,744 frames against ~2,250 in the others). Of the six pairs the on arm is slower in one. What clears the offset in both legs is the engine side: with the enemies hidden the frame still carries **+4.06 to +4.65 ms** over the same leg's 0-enemy window in leg A (+4.53 to +7.36 in leg B), 17–19 µs per enemy.

So the share of the per-enemy frame cost that is render-thread submission of enemy geometry is bounded at ≲0.7 ms per frame at 240 enemies — consistent with zero, and at most about a sixth of that leg's growth — and the rest is engine work on the main and physics threads: per-enemy AI, the Rigidbody under Unity's solver, and animation. These legs measured a larger per-enemy growth (+3.9 to +4.8 ms) than the published table's +1.99 ms because the player was being shoved through the swarm; submission work does not depend on where the player stands, so the bound carries to the published leg. One exception to "engine work only": Unity culls animator updates by renderer visibility, so hiding 240 enemies may also have skipped their animator work — the probed `AnimatedMesh.Update` across the whole population is 0.039 ms/frame, which is how much that can distort the split.

### Engine-side A/B: the solver and animation

Rendering controls cannot split the engine side any further, so the harness gained two more: `perf physics --disable` sets `Rigidbody.isKinematic = true` on every Rigidbody under the live enemies, taking the swarm out of Unity's solver with AI, renderers and animation still running, and `perf animation --disable` sets `Behaviour.enabled = false` on their `AnimatedMesh`/`Animator` components with renderers, colliders and bodies still running. Both restore exactly the value they found, rescan on population change or 0.5 s, and are timed as their own ticks so the armed arm's rescan is inside the report. Legs on the fedora host, tier 4, seed 20261102 (`LevelLoader: starting map=Forest stage=0 tier=4 seed=20261102`), 0 and 240 enemies, 20 s windows, three repeats per arm, arms interleaved with the leading arm flipped every repeat. All 24 windows: `pausedFrames == 0`, vsync off, no `_suspect`, player within the 8-unit gate at window start.

Mean ms per window, with the per-pair deltas of the armed arm against its own repeat's baseline:

| leg | 0 enemies: base / armed | 240 base | 240 armed | armed − base, per pair |
| --- | --- | --- | --- | --- |
| physics (`physbase` / `physkin`) | 4.79–4.99, mean 4.93 / 4.98–5.03, mean 5.00 | 8.66–9.18, mean 8.98 | 7.78–7.97, mean 7.87 | −0.88, −1.32, −1.12 |
| animation (`animbase` / `animoff`) | 5.04–5.07, mean 5.06 / 5.07–5.16, mean 5.10 | 8.66–9.44, mean 8.94 | 8.73–9.55, mean 9.18 | +0.59, +0.02, +0.11 |

The two legs' 240-enemy baselines agree to 0.04 ms of each other (8.98, 8.94) despite being separate sessions, and their 0-enemy baselines differ by 0.13 ms — well inside the ~0.8 ms session offset, which is the bar every figure below is read against. At 0 enemies both arms are noise, as they should be: +0.24, −0.01, −0.01 and +0.02, +0.09, +0.03 with nothing to freeze or stop.

**The solver is the first engine figure that clears the offset.** Taking the swarm out of it is worth **0.88–1.32 ms/frame at 240 enemies** (mean −1.11, ~4.6 µs per enemy), every pair clearing the offset in the right direction. It is a lower bound on what leaving the solver is worth: the armed arm pays 0.025 ms/frame of its own rescan inside that number (0.0251–0.0262, against 0.0003 disarmed), so add it back — 0.90–1.34 ms. The arm demonstrably did what it says: `rigidbodiesFound` 240 with 240 enemies, `rigidbodiesKinematic` 140/240/133 at the moment of arming, and a live check of the same control logged `froze 116 rigidbodies` on its first sweep and `restored 240` at the end of a 25 s arm — the 0.5 s rescan keeps claiming bodies the game makes dynamic again, so a window is run against a continuously frozen swarm even though the arm-time counter reads lower. The marginal figure is 5.5–8.4 µs per body actually frozen.

The stock probes move the way the arm predicts and no further: `EnemyMovementRb.MyFixedUpdate` 0.114 → 0.046 ms/frame, `Enemy.MyFixedUpdate` 0.318 → 0.224, `EnemyManager.FixedUpdate` 0.369 → 0.271 — the AI methods get cheaper because their `rb.velocity` writes and sweep calls are cheap on a kinematic body — while `AnimatedMesh.Update` is flat across the two arms (0.057 → 0.061), so animation is untouched. Its fidelity is the confound and it is a real one: a kinematic swarm stops translating. Position-sum drift across the window is +1579, +114, +1247 (mean +980) in the baseline arms against −94, −10, +754 (mean +217) armed. So this figure is the solver *plus* the contacts those bodies stop generating and the broadphase work they stop feeding, *plus* whatever movement the game drives through `Rigidbody.velocity`, which a kinematic body ignores. It says "the body is not simulated", not "the solver alone costs this".

**Animation is bounded by its own probe, not by the A/B.** The arm removes work the probe can see and the frame cannot: `AnimatedMesh.Update` goes 0.060 → 0.0000 ms/frame with `behavioursOff` 240 of `componentsFound` 240 and `byType` `{AnimatedMesh: 240}` (one animation Behaviour per enemy — the enemies carry no `Animator`), yet the armed frame is 0.02–0.59 ms *slower* (mean +0.24). Every pair is inside the offset and the sign is wrong, so the delta is inconclusive on its own. It is also nearly self-cancelling: the cull's rescan costs 0.036–0.051 ms/frame while armed, the same size as the 0.055–0.065 ms/frame of probed animation work it takes out, which is exactly why the frame cannot resolve it. The honest figure is therefore the probe's: all 240 enemies' animation is **~0.06 ms/frame**, 0.25 µs each, and that is also the most the earlier caveat — Unity culling animator updates by renderer visibility — can have distorted the render bound by. Movement does not depend on it: the position sum still races around in the armed arm (+677, +324, −8,316 per window) as it does unarmed, so AI, colliders and bodies keep running.

The three arms together, at 240 enemies in these legs (growth over the same leg's 0-enemy mean: +4.05 physics leg, +3.88 animation leg): simulation of the bodies **0.90–1.34 ms**, animation **≲0.06 ms**, enemy draw submission **≲0.7 ms and consistent with zero**, and the four probed stock methods 0.86 ms/frame (0.32 + 0.11 + 0.37 + 0.06) — a figure that overlaps the physics delta rather than adding to it, since part of what those probes measure gets cheaper when the body stops being simulated. What that leaves unattributed in a leg with ~4 ms of growth is the game's non-instrumented enemy work: hit and damage paths, spawn and pool churn, and AI decisions outside the four patched methods. Sharpening it needs probes on those paths, not more controls.

**Attribution summary at 240 enemies, gathered:**

| cost | ms/frame | source |
| --- | ---: | --- |
| zero-enemy baseline (engine, render, non-enemy AI, mod ticks at rest) | 4.33 | 0-enemy window mean |
| probed stock enemy paths | 0.63 | Harmony prefix timers |
| contact-density overhead | ~0.18 | density A/B delta, gathered against strung-out at 240 |
| mod work driven by the population | ~0.04 | mod ms/frame 0.042 at 0 enemies rising to 0.086 at 240 |
| per-enemy engine update (AI, Rigidbody, animation) with render submission bounded out | ~1.14 | 1.99 ms growth − 0.63 − 0.18 − 0.04; the render-only A/B bounds enemy draw submission at ≲0.7 ms, consistent with zero. The engine-side arms split this residual in a separate session — the simulated bodies are worth 0.90–1.34 ms of that leg's larger +4.0 ms growth, animation ≲0.06 — so it is one residual, not a sum with those figures |
| **frame total** | **6.32** | the baseline plus the four growth slices, which is what closes on it |
| mod CLR GC pause | 0.000 | EventListener on GCSuspendEE |

The mod's whole cost at 240 enemies is ~0.10 ms/frame (0.086 measured), not ~0.04: most of it runs at 0 enemies too, so only the part that grows with the population belongs in a growth decomposition and the rest is already inside the 4.33 ms baseline. Quoting the mod's share of a 240-enemy frame, use 0.086 ms/frame, 1.2%.

**Why this says ~1.1 ms where earlier notes said ~2.2 ms.** The 2.2 ms figure is the residual of a different session: 4.15 ms at 0 enemies against 7.02 ms at 240, so +2.87 ms of growth, minus 0.63 ms of probed stock paths and 0.044 ms of mod work. That sweep had no density control and its baseline came from a separate window set. This protocol's growth is 0.88 ms smaller, which is the same order as the ~0.8 ms session-to-session offset and the ±1.5 ms window spread recorded above, so the two are not inconsistent — they are two sessions, and the gated-window density protocol is the one that supports a decomposition because it is the one that measures its own 0-enemy baseline. Quote ~1.1 ms per enemy-scaled frame here; the 2.2 ms figure stands only as "the unprobed part of a 2.87 ms growth measured in another session". The render-only A/B above says which side of the render thread it sits on: hiding the enemies' renderers removes 93–96% of the enemy-attributable submitted vertices and changes the frame by less than the session offset, so this ~1.1 ms is engine-side work, not submission. The engine-side arms above say which part of the engine: taking the bodies out of the solver is the share that measures (0.90–1.34 ms of a separate leg's larger growth), and all the animation in the frame is ≲0.06 ms.

Nothing here is fixed. Each is listed with the number that would have to move.

- **Stock `Enemy.MyFixedUpdate` and `EnemyMovementRb.MyFixedUpdate` are the only meaningful lever**: 2.81 µs and 0.92 µs per call, 84 calls per frame at that population, 0.31 ms/frame, and they carry the steepest slopes of anything measured (1.04 and 0.32 µs per extra enemy). They run at the 50 Hz fixed-update rate. Lowering `Time.fixedDeltaTime`'s cost is not available to a mod, and the game's own movement is a Rigidbody under Unity's physics solver, which is where the per-enemy engine time sits — no longer an inference from what the render thread is not: kinematicising the swarm, contacts and `rb.velocity` movement included, is the only engine change that moves the frame outside the session offset, 0.90–1.34 ms at 240 enemies, and it is exactly these two methods whose probed cost falls when the body stops being simulated (`EnemyMovementRb.MyFixedUpdate` 0.114 → 0.046, `Enemy.MyFixedUpdate` 0.318 → 0.224 ms/frame). Any work here means patching stock movement. Another frame capture cannot sharpen this: replayed per-event GPU timings are inflated past usefulness and a Harmony probe has already mapped this region.
- **`AnimatedMesh.Update` runs 239 times a frame at 240 enemies** (0.039 ms/frame, 238.9 calls/frame, 0.16 µs each). Cheap individually, and it scales linearly with no culling visible at this population. The `--anim-arms` leg confirms the ceiling rather than raising it: stopping all 240 components drops the probe to exactly 0.0000 ms/frame and moves the frame by +0.02 to +0.59 ms, i.e. nothing outside the session offset, because the arm's own rescan (0.036–0.051 ms/frame) is as large as what it removes. So the whole enemy animation population is worth ~0.06 ms/frame, 0.25 µs per enemy, and no measurement this side of a stock-side change can sharpen it further. If enemy counts are to go higher, this is the second thing after the fixed update to look at, and the lever is animation LOD or culling distance rather than the mod.
- **The per-enemy engine cost is split, and the solver is the half that measures.** The three live-enemy controls (`perf render`, `perf physics`, `perf animation`, swept by `--render-arms`, `--physics-arms` and `--anim-arms`) each take one subsystem out with the others running, measured the same gated, arm-interleaved way. What leaves the frame when the bodies leave the solver is 0.88–1.32 ms per pair at 240 enemies (0.90–1.34 with the arm's own 0.025 ms/frame rescan added back), the only engine figure that clears the ~0.8 ms session offset. Animation is bounded at ~0.06 ms/frame by its own probe, which the A/B cannot resolve because the arm's rescan costs the same. Render submission stays bounded at ≲0.7 ms, consistent with zero. The remaining engine share is non-instrumented game work — hit and damage paths, spawn and pool churn, AI outside the four patched methods — and the lever for it is those paths, not the render thread and not animation. Two confounds carry with the solver figure and are recorded in the window JSONs rather than smoothed over: the kinematic swarm also loses its contacts, the broadphase work those contacts generate, and any movement driven through `Rigidbody.velocity` (its position-sum drift falls from a mean +980 to +217, which is the proof it stopped walking); and the arm only ever claims bodies the game left dynamic — at the moment of arming that was 140, 240 and 133 of the 240 bodies found across the three repeats, and a live check armed with 116 and released 240 after 25 s of rescan. Why some enemy bodies sit kinematic is not settled: the dump shows declarations, not callers, so which stock state sets `isKinematic` needs native reading of the callers or watching one enemy's flag across its lifetime.
- **Reward-window and death-screen pauses are a gameplay-level frame problem** for anyone who measures or plays at high counts: a window opened mid-run holds `MyTime.paused` and the frames it produces are menu frames. Harness-side handling exists (skip, report, discard); stock menus that pause the run for any other reason would need the same gate.

## Reproducing

The sweep that produced these tables lives in `scripts/perf_sweep.py`; it relaunches the game, loads the level, and takes one gated window per enemy count, writing one JSON per window plus its own rejection reasons. See [Frame-time profiling](development.md#frame-time-profiling) for the verbs it drives and the gates it enforces.

The arm legs above ran on the fedora host as:

```sh
uv run scripts/perf_sweep.py --out /tmp/perf-physics   --count 0 --count 240 --physics-arms 3 --tier 4 --seed 20261102 --seconds 20
uv run scripts/perf_sweep.py --out /tmp/perf-animation --count 0 --count 240 --anim-arms 3    --tier 4 --seed 20261102 --seconds 20
```

add `--launch-cmd "sh <the host's launcher>"` on a direct-Proton host where `task game:run` is unavailable. Read a leg out of its window JSONs, not its log: `_controlState` is the harness's account of what the arm held, `_controlMsPerFrame` is the arm's own cost to be added back before a saving is quoted, and `_probesMsPerFrame` is what says the arm touched only what it targets. A pair whose delta is smaller than the ~0.8 ms session-to-session offset is inconclusive, not small.
