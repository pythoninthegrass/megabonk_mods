---
id: TASK-027
title: Diagnose Linux Warehouse startup stall and Forest flash
status: Done
assignee: []
created_date: '2026-10-31T18:43:00Z'
updated_date: '2026-10-31T18:47:00Z'
labels: []
dependencies: []
type: spike
ordinal: 132000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Calcium appears suspended near the Warehouse upper half-pipe for roughly five seconds at startup on Linux under Proton. Forest appears for one to two seconds first. Establish whether spawn correction fights motion or another startup condition is responsible before changing behavior. User authorized restarting the running Linux game for an instrumented test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Capture startup position, velocity and spawn-correction timing without changing spawn behavior.
- [x] #2 Distinguish base-map generation/edit timing from any repeated relocation using runtime evidence.
- [x] #3 Record diagnosis, limitations and recommended fix; restore temporary instrumentation and input-device/harness settings after testing.
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
1. Keep spawn behavior unchanged. Add temporary harness-gated logs for startup body position/velocity, movement state and each watchdog correction. Build/deploy on Linux after checking clean source status; save the installed DLL first.
2. Enable harness, stop the authorized existing game, launch through Steam and exercise Calcium/Warehouse startup without player input using maintained menu tooling or a controlled harness load. Capture logs/screenshots and compare correction timing with movement.
3. Record findings and a narrowly scoped fix recommendation. Remove temporary source instrumentation, restore original installed DLL/harness marker and stop owned input devices; do not silently implement a behavior change under test-only authorization.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced through stock main menu -> mouse-select Calcium -> Confirm -> Warehouse -> Confirm. No movement input, no developer load-level, no altered spawn/gameplay behavior. Temporary harness-gated logs sampled body/velocity, grounded/frozen/teleporting/paused every 0.1s for 9s and logged every watchdog correction. Evidence: local .tools/startup-probe/calcium-stock-start.log; remote .tools/startup-probe/calcium-stock-start.log; screenshots .tools/startup-character.png, startup-map-selected.png, startup-launch.png, startup-settled.png.

First placement at monotonic t=43.420: from body (120,2.43,0) to feet target (109,36.08,-116). Normal fall reaches body (109,30.65,-114.89), velocity (0,-3.44,6.92), then watchdog resets it at t=44.262,45.096,45.947,46.780,47.615. Every repeat follows the same physical ramp slide, not a return to Forest. Once five-second watch expires, player settles at body (109,29.75,-112.40) without movement input. Samples show frozen=False, paused=False, teleporting=False. This conclusively explains the repeated airborne/reset appearance; code's single existing log line concealed repeated corrections.

Forest generation completed at 13:45:42.360; 1241 edits completed at 13:45:44.044 (1.684s); first authored-start correction at 13:45:44.119. Forest is the underlying generated map being replaced; there is one generation and no repeated cross-area load in the trace. Early screenshot landed on loading/black, so actual Forest visibility duration was not independently measured by frames. The runtime edit interval matches the reported flash.

Recommended fix: replace distance-based five-second enforcement with lifecycle-aware authored placement that permits normal falling/sliding immediately after success, while still handling any late vanilla Spawn call. Also keep the transition/loading presentation covering baseline generation through custom edits and placement. Do not merely shorten the timeout or change the half-pipe collision. Authored start is above the ramp (body initially ~38, settles ~29.75); that drop is independent of the repeated resets. Linux specificity is not established: the faulty policy is shared code and macOS was not tested in this session.

Cleanup verified: original installed DLL restored byte-for-byte from backup, temporary source instrumentation removed locally and remotely, remote source tree clean, harness marker restored disabled, owned virtual-input service stopped/socket removed, instrumented game quit. No production behavior change remains; only this investigation task is untracked locally. No full test suite run because no production code remains changed. Initial remote build lacked gitignored Directory.Build.props, fixed for this test by passing explicit MelonLoader/Il2Cpp/game/deploy MSBuild properties; diagnostic build succeeded with 0 warnings/errors. Game left stopped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Confirmed the startup stall is the authored-start watchdog repeatedly resetting normal half-pipe falling/sliding during its five-second window. Stock Calcium/Warehouse startup produced initial placement plus five repeat corrections ~0.84s apart; player settled normally without input after expiry. No physics freeze or alternating map reload observed. Forest baseline generation preceded completed Warehouse edits by 1.684s, consistent with the reported flash, though frame visibility duration was not measured. Recommended lifecycle-aware one-time placement and covering the entire custom-level setup with the loading transition. No behavior fix applied under diagnostic-test authorization. Instrumentation removed, original DLL restored, harness disabled, input devices cleaned up, game stopped. Evidence and exact timings are recorded in notes.
<!-- SECTION:FINAL_SUMMARY:END -->
