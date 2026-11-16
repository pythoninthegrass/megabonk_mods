---
id: TASK-080.13.01
title: Make upgrade selection work in the native macOS OpenBonk build
status: In Progress
assignee: []
created_date: '2026-11-16T21:05:00Z'
updated_date: '2026-11-16T21:52:00Z'
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
- [x] #2 A mouse click on an offered upgrade awards exactly that upgrade once, closes the offer screen and resumes gameplay through the normal UI path, without a direct-handler call or forced unpause substituted for input.
- [x] #3 Keyboard navigation visibly focuses offers and the configured confirm action awards exactly the selected upgrade once, closes the offer screen and resumes gameplay.
- [x] #4 A bounded native arm64 run demonstrates both selection paths and at least a subsequent level-up without double awards, stuck pause/input state or gameplay exceptions; the isolated profile survives restart without a reset or bypass.
- [x] #5 Regression coverage is written first for testable logic, and developer notes document the cause, the required workspace/source adaptations, reproduction evidence and remaining limits without claiming shipped-game parity.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
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

Continuation: preserve build 10 and first add callback/install-state diagnostics (scene, current EventSystem/module identities and before/after enabled/active states), without changing selection behaviour. Reproduce once natively to distinguish missed/persistent EventSystem coverage from later disable; write a failing lifecycle regression for the measured cause before the next adapter change. Then rebuild and re-run bounded OS-input verification.

Clean native rerun: the same-profile restart now demonstrates keyboard-first and mouse-second awards, but the read-only probe queries stale inventory after a later return to MainMenu. Add a failing return-to-menu probe regression and guard the observation lifecycle, then repeat the combined bounded sequence and restart without resets. No gameplay handler changes are needed.

Validated final private adapter: discover all loaded EventSystems (including inactive/persistent), preserve or add standard module and enable on scene load only. All installation, persistent lifecycle and probe-cleanup regressions pass. Clean native mouse-first/subsequent-keyboard sequence plus prior keyboard-first restart complete; only conventional commit/final task closure remain.
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

Build 11 diagnostic-only native run upgrade-lifecycle-01 completed. Callback executes, but the active EventSystem (36444, module 41034) already lives in DontDestroyOnLoad before MainMenu sceneLoaded, remains disabled before/after, and is skipped by the scene-root scan. On GeneratedMap load the adapter instead enables a different inactive scene EventSystem (74702/module 80466), leaving the persistent current one unchanged. This establishes missed persistent coverage, not a later disabling writer. AlwaysManager.Awake calls DontDestroyOnLoad before activating its EventSystem.

Added private MacUpgradeInputLifecycleCheck.cs: real editor Play Mode moves a disabled EventSystem with existing custom submit binding to DontDestroyOnLoad before invoking scene-loaded installation. upgrade-lifecycle-test-red.log fails precisely on persistent module still disabled; changing discovery from scene roots to all loaded EventSystems (including inactive) makes upgrade-lifecycle-test-green.log pass enabled/binding/idempotence checks. No selection handler or per-frame re-enable changed. Build 12 is running for native validation. Both repositories' prior work and all baseline apps/profiles preserved.

Build 12 upgrade-fixed-02 completes with one MAC_UPGRADE_CLICK offer=0. Focused measured click selects Firestaff once (level 1 -> 2); Silver Tome/Chunkers remain 0, offers close, MyTime.paused becomes False, and stageTime advances from 29.23187 to 38.93661 before ordinary player death. ARM64 verified in upgrade-fixed-02-native.txt. No gameplay exception observed. AC2 verified; death prevents reaching the subsequent keyboard offer, so AC3–4 remain open. Restarted same app/profile as upgrade-fixed-03 with keyboard-first order and an OS-only movement sequence between offers; no invulnerability or award/pause bypass. Original installation regression still passes (upgrade-input-test-green-02.log). task check passes again: 2,211 Python tests, one skipped plus remaining checks (upgrade-repository-check-02.log).

upgrade-fixed-03 (ARM64, same-profile restart) dispatches exactly two clicks: keyboard offer 1 then subsequent mouse offer 0. Down changes selected offer from Firestaff to Projectile Speed Tome; its hover scale reaches 1.03 and input-3983.png visibly outlines that second offer. Enter awards Projectile Speed Tome 0 -> 1 once (others unchanged), closes offers and resumes time. At stageTime 38.33709 a subsequent offer opens; mouse awards Golden Tome 0 -> 1 once, closes/resumes to stageTime 48.35848 before ordinary death. Driver records both requested actions and exit 0. AC3 verified. Later OS input not attributable to this driver returns the death screen to MainMenu around t145; MacUpgradeProbe's stale WeaponData.GetLevel observation then throws repeatedly. These are probe stack traces, not selection-handler failures. AC4 left open for a clean rerun after a test-first probe lifecycle guard; no unrelated game logic will be changed.

Probe lifecycle regression upgrade-probe-test-red.log reproduces WeaponData.GetLevel -> MacUpgradeProbe.Update failure without a player inventory. The private guard drops stale observations when GameManager/player inventory is gone; upgrade-probe-test-green.log passes. Build 13 succeeds with the same three preparation errors and changes only that observation guard relative to build 12. Preserved candidate-build-12.app. Same-profile mouse-first/subsequent-keyboard clean native rerun upgrade-fixed-04 is running.

Clean build-13 upgrade-fixed-04 completes normally with no logged exceptions; measured Code Type ARM64. Same isolated profile loads without reset after the prior runs. Mouse dispatches offer 0 once, Damage Tome 0 -> 1 at stageTime 17.3509; later Down visibly focuses offer 1 (input-5024.png), Enter dispatches it once, Firestaff 1 -> 2 at stageTime 35.30441. Unselected tracked levels stay unchanged. Both offers close, paused=False, stageTime advances to 57.85915 and a third level-up opens. The two-action driver intentionally leaves that third offer unselected; this is not a stuck pause/input state. Driver records both requested actions and exit 0; player records MAC_RESEARCH_COMPLETE. AC4–5 verified. Developer notes and private EXPERIMENT.md now document cause, exact lifecycle, reproduction, evidence, probe correction and remaining parity/build limits. Final markdownlint and git diff --check pass. Sibling overlay remains untouched apart from its pre-existing untracked instruction files; no game-derived files staged.
<!-- SECTION:NOTES:END -->
