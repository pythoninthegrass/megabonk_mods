---
id: TASK-056.02
title: Prove a minimal BepInEx IL2CPP plugin loads and patches Megabonk under Wine
status: To Do
assignee: []
created_date: '2026-11-08T23:31:00Z'
labels:
  - bepinex
dependencies: []
references:
  - 'https://github.com/BepInEx/BepInEx'
  - 'https://docs.bepinex.dev/articles/dev_guide/plugin_tutorial/index.html'
parent_task_id: TASK-056
priority: medium
type: spike
ordinal: 1200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Before committing to the port, prove the runtime model: a BepInEx 6 IL2CPP BasePlugin plus a per-frame tick component loads in Megabonk, logs, and one small Harmony patch applies against BepInEx-generated interop assemblies. This retires the port's biggest technical risk in a scratch project without touching the main mod source or the working MelonLoader setup. Timebox: one working session; ends with a recorded go/no-go.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A scratch plugin project separate from the main mod source builds against BepInEx 6 IL2CPP references and the game's interop assemblies
- [ ] #2 The plugin loads: its startup lines appear in BepInEx/LogOutput.log during a launch of the Windows build under Wine
- [ ] #3 A per-frame tick callback demonstrably runs (repeated log lines) and one small Harmony patch on a game method applies without breaking the game
- [ ] #4 The MelonLoader launch still works afterward (loaders coexist or BepInEx is disabled per the rollback manifest; state recorded)
- [ ] #5 Go/no-go decision recorded on this task within the timebox of one working session
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
