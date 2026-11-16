---
id: TASK-080.13.01
title: Make upgrade selection work in the native macOS OpenBonk build
status: To Do
assignee: []
created_date: '2026-11-16T21:05:00Z'
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
- [ ] #1 A repeatable native macOS test reproduces the blocked level-up selection and records the actual input/UI outcome; wrong focus or invalid target coordinates are distinguished from a game UI failure.
- [ ] #2 A mouse click on an offered upgrade awards exactly that upgrade once, closes the offer screen and resumes gameplay through the normal UI path, without a direct-handler call or forced unpause substituted for input.
- [ ] #3 Keyboard navigation visibly focuses offers and the configured confirm action awards exactly the selected upgrade once, closes the offer screen and resumes gameplay.
- [ ] #4 A bounded native arm64 run demonstrates both selection paths and at least a subsequent level-up without double awards, stuck pause/input state or gameplay exceptions; the isolated profile survives restart without a reset or bypass.
- [ ] #5 Regression coverage is written first for testable logic, and developer notes document the cause, the required workspace/source adaptations, reproduction evidence and remaining limits without claiming shipped-game parity.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
