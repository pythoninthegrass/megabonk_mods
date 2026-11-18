---
id: TASK-084.02
title: Make the core combat and upgrade loop playable on Vita
status: Done
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T09:29:00Z'
labels:
  - ps-vita
  - vita-spike
dependencies:
  - TASK-084.01
documentation:
  - .agents/skills/vita-port/SKILL.md
  - docs/development.md#openbonk-reconstruction-on-native-macos
  - docs/vita-combat.md
modified_files:
  - taskfiles/vita.yml
  - docs/vita-combat.md
  - tests/test_vita_combat.py
  - vita/combat/CMakeLists.txt
  - vita/combat/combat.c
  - vita/combat/combat.h
  - vita/combat/livearea.xml
  - vita/combat/main.c
  - vita/combat/render.c
  - vita/combat/render.h
  - vita/combat/test_combat.c
parent_task_id: TASK-084
type: spike
ordinal: 287000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Keep the feasibility build small enough to test the feel of Megabonk without committing to the original engine, full asset pipeline or all content. Use original placeholders and a Forest-style graybox.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 On the PCH-2000, one character moves and aims with the physical controls, fights a swarm with one automatic weapon, picks up XP and earns an upgrade.
- [x] #2 Selecting an upgrade through the normal UI applies it once and resumes combat.
- [x] #3 A repeatable benchmark scenario can vary live enemy count and place equally sized groups in gathered and scattered layouts, with no bypass in ordinary play.
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
1. Keep the smoke application intact. Add a separate native VitaSDK combat VPK with original placeholder assets, no Unity, no proprietary data, no runtime plugins, and no clock overrides. Confirm the graybox rendering approach before implementation so the next task measures a representative workload.
2. Write host tests first for fixed-step movement and aim, automatic weapon hits, XP drops and pickup, and an upgrade choice that applies once and resumes simulation. Exercise the same simulation from the Vita frontend with both physical sticks and button-edge input for the normal upgrade UI.
3. Provide a separate explicitly selected benchmark mode sharing ordinary enemy update and render paths. Test deterministic gathered and scattered placements at matching selectable live counts; isolate benchmark controls from ordinary play.
4. Validate the VPK and run task check. Install only the combat app on the PCH-2000, verify the physical control and upgrade sequence, verify repeatable matched-count layouts, and document the procedure. Leave the performance threshold and GO/NO-GO decision to the follow-up task.

Approved presentation: minimal 3D Forest graybox. Use GPU-rendered solid geometry, a portable fixed-step combat core, and a separate combat VPK. Reuse neither proprietary assets nor the smoke app title ID.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started in a dedicated worktree based on the merged hardware smoke baseline. VitaSDK compiler is installed; the home-network console answered a read-only SSH command with the system client and default configuration bypassed. No console changes made.

Host simulation tests failed before the combat core existed and passed afterward. Builds validated both the original smoke VPK and the separate combat VPK. The Vita installer reported success for MBVK00002 on the PCH-2000, and its eboot and sce_sys directory are present. LiveArea launch, depth-tested rendering, physical input, and the on-device upgrade and matched-count benchmark flows still need verification.

Repository task check passed: 2,858 .NET tests passed; Python reported 2,359 passed, 112 skipped, and 1 expected failure; Markdown, Ruff, and site lint checks passed. The VPK validator reported zero errors and warnings.

The maintainer reports running the benchmark on the physical console, confirming the app launched and reached benchmark mode. SSH verified the installed title. This build has no telemetry writer; there is no timing report to retrieve. Matched counts, reset behavior, and the ordinary play and upgrade flow are not yet confirmed.

The maintainer confirmed the documented physical play and benchmark checks and noticed no performance dips. Enemy count was not reported. This is qualitative hardware feedback, not timing or memory evidence.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Add a standalone VitaSDK Forest graybox with a host-tested combat core, physical twin-stick controls, automatic combat, XP pickups, and a one-time upgrade choice that resumes play. Confirm the ordinary loop and both resettable benchmark layouts on a physical PCH-2000. The host tests cover matched counts through 240, deterministic starting positions, and replenishment in benchmark mode only. Task check and VPK validation passed. The playtester noticed no dips; no frame-time or memory telemetry was collected, so the performance gate remains open.
<!-- SECTION:FINAL_SUMMARY:END -->
