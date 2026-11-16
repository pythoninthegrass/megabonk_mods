---
id: TASK-080.13.01
title: Make upgrade selection work in the native macOS OpenBonk build
status: In Progress
assignee: []
created_date: '2026-11-16T21:05:00Z'
updated_date: '2026-11-16T21:29:00Z'
labels:
  - native-macos
  - arm64
  - openbonk
  - input
dependencies:
  - TASK-080.13
references:
  - TASK-080.13
  - 'https://github.com/martin2844/OpenBonk'
  - ../open_bonk/unity/OpenBonk/Assets/Scripts/Assembly-CSharp/LevelupScreen.cs
  - ../open_bonk/unity/OpenBonk/Assets/Scripts/Assembly-CSharp/MyButton.cs
documentation:
  - docs/development.md
parent_task_id: TASK-080.13
priority: high
type: bug
ordinal: 283000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The bounded OpenBonk macOS experiment now runs its reconstructed game natively through Unity 2023.2.22f1 IL2CPP and Metal: Forest generation, Fox, keyboard movement/jump, combat and level-one offers are observed. The run cannot continue because neither an OS-injected mouse click nor Enter selects an upgrade. Successful event posting is not successful UI interaction. The cause is not established; do not assume it is only coordinates, focus or a platform define. The experiment has an isolated research profile, OSX entry to the existing recovered map coroutine, repaired localization and Newtonsoft AOT collection coverage. Private artifacts are in the local experiment directory named openbonk-macos-spike-20261116, including EXPERIMENT.md, workspace, input-smoke.swift, input-smoke-02.log, player-06.log and smoke-06 frames; inspect these before reproducing, and treat them as potentially stale. The sibling OpenBonk checkout is the source overlay, not a standalone buildable project. Preserve both repositories' work and all real saves. Scope is desktop upgrade selection and resuming this native reconstruction, not full-game parity, a generic input rewrite or the independent lifted-runtime delivery route. All game-derived assets, sources and binaries remain local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A repeatable native macOS test reproduces the blocked level-up selection and records the actual input/UI outcome; wrong focus or invalid target coordinates are distinguished from a game UI failure.
- [ ] #2 A mouse click on an offered upgrade awards exactly that upgrade once, closes the offer screen and resumes gameplay through the normal UI path, without a direct-handler call or forced unpause substituted for input.
- [ ] #3 Keyboard navigation visibly focuses offers and the configured confirm action awards exactly the selected upgrade once, closes the offer screen and resumes gameplay.
- [ ] #4 A bounded native arm64 run demonstrates both selection paths and at least a subsequent level-up without double awards, stuck pause/input state or gameplay exceptions; the isolated profile survives restart without a reset or bypass.
- [ ] #5 Regression coverage is written first for testable logic, and developer notes document the cause, the required workspace/source adaptations, reproduction evidence and remaining limits without claiming shipped-game parity.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the retained experiment, current source overlay/workspace differences and isolated profile; retain baseline app/profile and existing checkout changes.
2. Add read-only native diagnostics for actual OS focus/input, EventSystem/current module, selected/raycast target, offered-button enabled/interactable/listener state, offer identities and inventory levels. Reproduce the baseline with focus-guarded input against measured targets; do not substitute handler calls for selection.
3. Write failing regression coverage for confirmed testable selection-path defects before applying the smallest desktop fix to local-only source/workspace adaptations. Preserve GUIDs and unrelated Android behaviour; avoid generic input rewrites.
4. Rebuild the isolated IL2CPP/Metal app and verify native ARM64 execution. Exercise real OS mouse and keyboard navigation/confirm separately, recording exactly-one award, screen closure, normal resume and a subsequent level-up. Restart against the unchanged isolated profile.
5. Record cause, reproducible adaptations, evidence and limits in privacy-safe developer notes; run relevant tests and task check. Only finalize criteria and commit after objective validation.

Native validation found the newly created StandaloneInputModule disabled after scene startup. Trace the late initialization/component lifecycle that disables it, add a failing lifecycle regression before changing the adapter, and rerun native mouse/keyboard/subsequent-level checks. Do not treat the passing editor installation fixture as proof of usable runtime input.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial review: parent dependency is Done; both repositories preserve their existing work (main repository initially clean; sibling has only pre-existing untracked instruction files). Prior frame-8 confirms level-one offers remain open. Static inspection finds UpgradeButton.OnClick is empty despite MyButton.Awake registering it on Button.onClick; this is a candidate, not yet a confirmed runtime cause. Prior driver posts mouse and Enter together and uses window-relative estimated coordinates; new evidence must separate paths and log actual input/UI state. Honcho recall failed with connection/session errors; no persistent-memory write claimed.

Diagnostic build 08 succeeds with the same three reported preparation errors as build 07; no selection logic changed. Preserved baseline app as working-build-07.app and backed up isolated profile as profile-before-upgrade-task. Private MacUpgradeProbe.cs logs OS input, focus, EventSystem selection/current module, raycasts and measured offer targets; upgrade-input.swift guards focus and uses the measured target plus content/title bounds. First run died before producing an offer target (driver failed on missing target, then was corrected to refuse missing targets); this is not a reproduced UI selection result. Its logs do show currentInputModule=null throughout menu/gameplay despite EventSystem focus. Serialized scenes already bind Button.onClick to SelectUpgrade, so the empty OnClick is not sufficient evidence and must not be blindly filled (would risk double awards). A second baseline is running. Added a Unity editor regression check for module installation/idempotence/binding preservation before changing the compatibility installer; its red run is underway. All additions remain private in the existing experiment directory.

Confirmed baseline reproduction in upgrade-baseline-04 using diagnostic build 08: Unity logs focus=True, mouse down/up at (640,492), offer center (640,491.67), raycast hits resolving to UpgradeButton, enabled/interactable=True and original persistent SelectUpgrade listener. Down and Enter also arrive, but currentInputModule=null and no MAC_UPGRADE_CLICK is emitted; offers remain open. Coordinate guard was corrected for the observed centered letterbox (saved video mode overrides windowed launch request), with Unity position/raycast confirming the corrected target. Unrelated additional OS mouse events in the log are not attributed to the driver.
Regression upgrade-input-test-red.log fails on missing input module; after the minimal private compatibility change, upgrade-input-test-green.log passes module creation, legacy-axis defaults, idempotence and existing binding preservation. Build 09 succeeds with three reported preparation errors; build 10 adds longer optional bounded smoke and read-only inventory/offer-generation diagnostics for subsequent-level verification. No reconstructed selection handler changed, no direct-handler/forced-unpause substitute added. Native combined mouse/subsequent-keyboard run upgrade-fixed-01 is underway. task check passed: 2,211 Python tests, one skipped, plus remaining repository checks; private log upgrade-repository-check.log. Developer notes describe the confirmed baseline cause and explicitly leave native fix validation pending.

Baseline input/UI reproduction is now verified independently of focus and estimated coordinates (upgrade-baseline-04). Native post-fix verification is still running; no award/resume or subsequent-level criteria are checked yet. Native sample was captured during upgrade-fixed-01. Focused markdownlint passes after developer-note edits.

Latest native validation update: build 10 reports Succeeded with three existing preparation errors; upgrade-fixed-01-native.txt confirms Code Type ARM64. The candidate is NOT verified as a working fix. During upgrade-fixed-01, focused Unity mouse input reaches the measured first-offer center and raycasts resolve to that enabled/interactable offer, but currentInputModule remains null. Diagnostics now expose StandaloneInputModule:False:True (present, disabled, supported). At approximately 138 seconds, the same level-one offers are still open, MyTime.paused=True, stageTime remains 21.6371, and all three tracked upgrade inventory levels remain 0. No MAC_UPGRADE_CLICK or successful award/resume is recorded in the inspected output. The driver has not yet written its terminal summary in the inspected snapshot. Keyboard events visible in this combined run do not establish the intended subsequent-offer path. AC2–4 remain unchecked.
The editor red/green regression validates installation, idempotence and binding preservation only; it misses a later runtime disable. Next investigation is the component/scene initialization lifecycle, not another click-handler binding or a claimed successful native fix. AC1 remains verified; full task completion, final documentation and commit remain outstanding.

The bounded upgrade-fixed-01 run has now completed normally: MAC_RESEARCH_COMPLETE and driver exit=0. No MAC_UPGRADE_CLICK or gameplay exception appears in the final log. The driver records its focused first-offer mouse click, but never reaches the subsequent-offer keyboard action. This confirms the candidate still blocks selection rather than leaving native verification running. Next step remains tracing the later disable of the standard input module.

Expanded docs/development.md's native OpenBonk section with the failed candidate outcome, private artifact map, bounded driver invocation, test-precondition caveats and lifecycle investigation checklist. Corrected the earlier adapter description so it is not presented as a working fix. Important precision: the observed native state is a present, supported but disabled module after startup; a later disabling write is only one hypothesis. Callback coverage, persistent/different EventSystem identity and initialization order must be distinguished before naming a writer. Focused markdownlint and git diff --check pass. No new game run or implementation change in this documentation update.
<!-- SECTION:NOTES:END -->
