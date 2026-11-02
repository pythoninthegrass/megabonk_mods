---
id: TASK-036
title: >-
  Split the unprobed per-enemy frame cost into GPU render and CPU physics via
  the RenderDoc replays
status: To Do
assignee: []
created_date: '2026-11-02T21:32:00Z'
labels: []
dependencies: []
documentation:
  - docs/performance.md
  - docs/development.md
modified_files:
  - docs/performance.md
  - docs/development.md
priority: medium
type: spike
ordinal: 145000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Frame-time attribution at 240 enemies (levels/example-forest.mblevel.json, tier 4, seed 20261102, vsync off, scripts/perf_sweep.py gated windows) accounts for only part of the growth over an empty level: mean 7.02 ms/frame at 240 vs 4.15 ms at 0. Probed stock enemy paths are ~0.63 ms/frame (Enemy.MyFixedUpdate, EnemyMovementRb.MyFixedUpdate, AnimatedMesh.Update et al.), the mod is ~0.04-0.1 ms, density-contact overhead ~0.18 ms - leaving roughly 1.6 ms/frame of unprobed per-enemy engine work (Unity rendering, physics broadphase and solver, animation beyond AnimatedMesh). Harmony probes are exhausted on this; docs/performance.md's open items say the next step is separating GPU render time from CPU-side physics through a RenderDoc capture replay.

The captures exist on fedora (ssh fedora, tailscale only): /tmp/perf-captures-g/captures/count_240_0.rdc and count_240_1.rdc (plus count_0 controls) and /tmp/perf-captures-s/captures/*.rdc (density A/B and mod-off/reenabled controls), taken through the DXVK layer under Proton Experimental per the "RenderDoc on a direct-Proton Linux host" section of docs/development.md. /tmp is volatile - if they are gone, regenerate from ~/git/megabonk_mods with: ENABLE_VULKAN_RENDERDOC_CAPTURE=1 launch plus uv run scripts/perf_sweep.py --count 240 --captures 2 --capture-dir /tmp/RenderDoc --launch-cmd "sh /home/lance/.local/share/scripts/launch-megabonk.sh" (absolute launch-cmd path is required; the game launches offline via the steamstub, no Steam session needed).

Deliverable: replay the 240-enemy captures in the RenderDoc Qt UI (renderdoccmd or the GUI on fedora's GNOME session, or copy the .rdc files to a machine with the RenderDoc app), read GPU frame duration, draw-call count and the per-enemy mesh/animation submission, and settle how much of the ~1.6 ms is GPU render versus CPU-side physics/animation. Write the verdict and the numbers into docs/performance.md - replace the "~1.6 ms/frame of per-enemy engine update overhead" open item with the settled split, and record the replay method in docs/development.md if it needed anything beyond the existing capture section. Do not add new Harmony probes.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
