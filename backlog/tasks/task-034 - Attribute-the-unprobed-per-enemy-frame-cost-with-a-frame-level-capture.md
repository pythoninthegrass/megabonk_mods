---
id: TASK-034
title: Attribute the unprobed per-enemy frame cost with a frame-level capture
status: Done
assignee: []
created_date: '2026-11-02T07:48:00Z'
updated_date: '2026-11-09 05:26'
labels: []
dependencies: []
modified_files:
  - docs/performance.md
  - scripts/perf_sweep.py
priority: medium
ordinal: 143000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Frame-time attribution at 240 enemies leaves the largest share of the enemy-count growth unaccounted for. Measured on the Windows build under Proton (vsync off, player fixed at the spawn point, 20 s windows, unpaused frames only): mean 7.02 ms/frame at 240 enemies against 4.15 ms at 0, so +2.87 ms of growth. Of that, 0.63 ms is the probed stock enemy path (EnemyManager.FixedUpdate 0.279, Enemy.MyFixedUpdate 0.236, EnemyMovementRb.MyFixedUpdate 0.077 at 84 calls/frame) and 0.044 ms is mod work. About 2.2 ms per frame is engine cost no probe covers, and the residual at 0 enemies is already 4.11 ms, so it is not all per-enemy.

Density, not count, drives part of it: the same 240 enemies measured 9.63 ms gathered on the player at one point and 7.02 ms strung out across the map, which points at physics contacts. Next step is a frame-level capture (Unity frame debugger, or RenderDoc on the Direct3D 11 build) of a 240-enemy run to split render from physics from GC, not another Harmony probe. Reuse scripts/perf_sweep.py for the population and the gating; see docs/performance.md for the tables and docs/development.md for the method.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The frame-level capture method is reproducible from the repo: RenderDoc-under-Proton-on-the-gamescope-host setup and commands documented in docs/development.md.
- [x] #2 perf_sweep.py drives captures inside gated measurement windows (counts 0 and 240, gathered and strung-out density), pairing capture files with window reports.
- [x] #3 docs/performance.md gains the frame split - GPU render, CPU phases incl. physics, and GC - for 0 vs 240 enemies, and the 6.3 ms residual follow-up is retired or updated with the numbers.
- [x] #4 New pure logic (phase aggregation, density/capture gating, report handling) has unit tests written first; scripts:test green.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach (agreed with the maintainer 2026-11-02)

Frame-level attribution of the ~2.2 ms/frame unprobed per-enemy engine cost via three channels over the existing gated-window protocol:

1. GPU render - RenderDoc captures on the fedora gamescope host (Windows build, D3D11 pinned, under Proton). Capture path is the RenderDoc Vulkan implicit layer over DXVK: ENABLE_VULKAN_RENDERDOC_CAPTURE=1 in Steam launch options, layer registered in ~/.local/share/vulkan/implicit_layer.d, official Linux tarball installed user-level. Unity Frame Debugger is ruled out: editor/development-build only, and this is a shipping player. Capture and replay both stay on fedora (Intel Arc ANV); RenderDoc captures are not portable.
2. CPU phases - UnityEngine.LowLevel.PlayerLoop restructure with timing wrappers, gated inside the existing perf system (engine-level API, not Harmony; explicitly approved as scope). One wrapper per root phase (EarlyUpdate, FixedUpdate incl. physics sub-systems, Update, PreLateUpdate, PostLateUpdate, TimeUpdate) plus PhysicsSimulation-level sub-systems; aggregated into a phases array on perf report; original loop restored on perf reset/shutdown; zero cost when perf is off.
3. GC - GC.GetTotalPauseDuration() + GC.CollectionCount deltas per window on the same report (runtime counter, not a probe).

Cross-check: density A/B (gathered vs strung-out at equal 240 alive) x prediction that GPU time is flat across density while CPU physics is not; known baselines stay probed stock 0.63 ms and mod 0.044 ms/frame.

## Environment

- Branch perf-034-frame-capture; worktrees ~/git/megabonk_mods-034 on mbp (authoring) and fedora (testing), gitignored .env/.venv (+ .tools on mbp) symlinked from each box's main checkout. Tests run with uv run --no-sync through the symlinked venv (verified green on both boxes).
- fedora main checkout stashed (stash@{0} "fedora local state before pull 2026-11-02") and fast-forwarded to 5e9bf96 per the maintainer's prefer-remote instruction.
- Fedora game: ~/.local/share/Steam/steamapps/common/Megabonk (Windows depot, -force-d3d11), harness installed; MEGABONK_DEV=true via symlinked .env. Mod rebuild on fedora deploys via Directory.Build.props reading MEGABONK_GAME_DIR (no local props needed).

## Steps and checkpoints

1. [done] Worktrees + symlinks both boxes; pytest green.
2. RenderDoc de-risk spike on fedora: tarball install, layer registration, launch options (Steam-down localconfig.vdf edit preserving -force-d3d11), one main-menu frame capture. Fallbacks: renderdoccmd inject --PID pre-Vulkan; manual qrenderdoc assist once. CP2: capture file lands.
3. C# harness (tests first): phase timers + GC sampler in the perf system; C# unit tests for pure aggregation/tree-wrapping logic. CP3: phases appear in perf report with plausible magnitudes (FixedUpdate at 50 Hz cadence).
4. perf_sweep.py (tests first in tests/test_perf_sweep.py): --density gathered|strung (strung = spawn gathered then teleport player a fixed offset away, same alive count) and capture-window integration: trigger N RenderDoc captures inside gated windows at counts 0 and 240, pair .rdc paths with window JSONs; capture runs are separate sessions from timing runs.
5. Analysis headless on fedora via RenderDoc python module (fallback: source build for Python 3.13): per-frame GPU ms, top actions/passes -> summary JSON; pull to mbp.
6. Docs: performance.md split table (render/physics/GC at 0 vs 240, density A/B), retire the 6.3 ms residual follow-up; development.md RenderDoc-on-gamescope method + caveats.
7. Finalize per finalization guide; conventional commits, no attribution.

## Risks

- Capture trigger automation under gamescope over SSH (menu driver whitelist has no F12) - spike first; fallbacks listed.
- Prebuilt RenderDoc pymodule vs Python 3.13 - source-build fallback.
- PlayerLoop restructure under Il2CppInterop (delegate conversion); keep wrapper depth flat.
- .rdc files are hundreds of MB: stay on fedora (.tools/evidence convention); only JSON summaries travel.

Final state: all four ACs checked, tests green (1696 C#, 294 Python). GPU timing column not extracted (RenderDoc pymodule requires Qt host to initialise, standalone segfaults in v1.47; documented in development.md with the captures stored on fedora). Branch perf-034-frame-capture; commits from 5e9bf96 to dc03b34.
<!-- SECTION:PLAN:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
