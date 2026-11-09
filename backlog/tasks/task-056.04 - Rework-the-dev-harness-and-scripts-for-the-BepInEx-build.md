---
id: TASK-056.04
title: Rework the dev harness and scripts for the BepInEx build
status: To Do
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-08T23:31:00Z'
labels:
  - bepinex
  - dev-harness
dependencies:
  - TASK-056.03
modified_files:
  - scripts/game_paths.py
  - scripts/run.py
parent_task_id: TASK-056
priority: medium
type: task
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Development runs through the harness, run.py and the MCP server, which know MelonLoader paths (Latest.log, the Mods deploy folder, log scraping, relaunch detection). Without reworking them the ported mod cannot be built, loaded or verified day-to-day.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scripts/game_paths.py reports the BepInEx layout (plugins deploy folder, LogOutput.log) and its consumers and tests follow
- [ ] #2 run.py relaunch, load and editor-on work against the BepInEx build, with log scraping matching the new log file while the harness markers (DevHarness: enabled, KillFloor: armed) still appear
- [ ] #3 task mod:build deploys the plugin and its dependencies into the BepInEx plugins folder
- [ ] #4 The MCP server tools (screenshot, state, key, mouse, relaunch, clear_console_log) work against the new layout
- [ ] #5 task scripts:test passes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
