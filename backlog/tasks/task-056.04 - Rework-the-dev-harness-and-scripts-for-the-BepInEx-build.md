---
id: TASK-056.04
title: Rework the dev harness and scripts for the BepInEx build
status: Done
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-09 01:26'
labels:
  - bepinex
  - dev-harness
dependencies:
  - TASK-056.03
modified_files:
  - AGENTS.md
  - docs/development.md
  - scripts/game_paths.py
  - scripts/run.py
  - scripts/launch_game.py
  - scripts/mcp_server.py
  - scripts/perf_sweep.py
  - taskfiles/mod.yml
  - taskfiles/game.yml
  - taskfiles/crossover.yml
  - tests/test_game_paths.py
  - tests/test_run.py
  - tests/test_launch_game.py
  - tests/test_mcp_server.py
  - tests/test_perf_sweep.py
parent_task_id: TASK-056
priority: medium
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Development runs through the harness, run.py and the MCP server, which know MelonLoader paths (Latest.log, the Mods deploy folder, log scraping, relaunch detection). Without reworking them the ported mod cannot be built, loaded or verified day-to-day.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 scripts/game_paths.py reports the BepInEx layout (plugins deploy folder, LogOutput.log) and its consumers and tests follow
- [x] #2 run.py relaunch, load and editor-on work against the BepInEx build, with log scraping matching the new log file while the harness markers (DevHarness: enabled, KillFloor: armed) still appear
- [x] #3 task mod:build deploys the plugin and its dependencies into the BepInEx plugins folder
- [x] #4 The MCP server tools (screenshot, state, key, mouse, relaunch, clear_console_log) work against the new layout
- [x] #5 task scripts:test passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved and executed on bepinex-port; main remains untouched.
1. Added test-first path/layout, launch override/argument, startup-failure evidence and perf-consumer coverage; 11 expected failures demonstrated the old implementation.
2. Migrated game_paths output and harness/log consumers to BepInEx/plugins/MegabonkLevels, BepInEx/LogOutput.log and BepInEx/wine-latest.log. Kept legacy path functions for the unchanged installer and retained shared UserData/harness paths. Updated Wine doorstop override and removed legacy loader flags from both macOS launch routes.
3. Verified existing plugin/PDB/NLayer deployment with task mod:build and smoke-tested real-game MCP relaunch/load/editor, prefixed log reads, state, key, mouse, screenshots and console-log clearing through freshly imported server modules. Preserved reversible loader files and left the editor frozen, invulnerable, with spawns off.
4. Updated developer/agent instructions, task descriptions and build props tracking. task scripts:test and task check passed; task lint and git diff --check passed after final documentation edits.
5. Commit implementation conventionally, then record final completion and commit task bookkeeping. Packaging remains the next subtask.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial review: prerequisite runtime port is Done. The csproj already deploys plugin and copy-local dependencies into ModInstanceFolder. Remaining explicit MelonLoader log paths exist in game_paths.py, run.py startup diagnostics, launch_game.py Wine log output and perf_sweep.py; MCP log tool descriptions still name Latest.log. Implementation awaits plan approval.

Test-first verification: 11 expected failures demonstrated legacy paths, Wine overrides/arguments and failure-evidence behavior; implementation then passed focused tests (691) and task scripts:test (1160). game_paths now reports BepInEx/plugin/Wine log paths while retaining legacy helper functions for the unchanged installer. run.py failure diagnostics, launch_game.py, perf_sweep and MCP log descriptions consume the new layout. Plain Wine uses winhttp instead of version and no MelonLoader CLI flag.

task mod:build passed with zero warnings/errors; plugin, symbols and NLayer verified in BepInEx/plugins/MegabonkLevels. Fresh in-memory MCP Client against the real game successfully executed relaunch/example-forest/editor, observing BepInEx log readiness and returning editor=true, frozen=true, killFloorArmed=true. Spawns disabled and invulnerability enabled afterward. Existing connected server retains old imported modules; fresh server paths reports LogOutput.log. Documenting restart requirement.

Full task check passed: mod build, installer checks, 2781 C# tests, 1160 Python tests, markdownlint and ruff. Existing test-project nullable/xUnit warnings and pytest fixture-scope deprecation remain; no C# changes or new warnings introduced. Ruff normalized the extended run.py import. Final task lint and git diff --check passed.

Real-game fresh MCP smoke also verified severity-prefixed DevHarness/KillFloor/editor log reads, BackQuote opening/closing the rendered console, mouse move/clear, state and full-frame screenshots. Evidence: .tools/evidence/bepinex-harness-console.png and bepinex-harness-editor.png (gitignored). Console help created persisted history; fresh MCP clear_console_log returned removed=true. Final state: editor/frozen/invulnerable true, spawnsOff true, edits count 0. winhttp.dll/doorstop_config.ini active, version.dll absent and version.dll.bak preserved. Existing connected MCP server needs restart to reload changed modules; documented and verified via fresh Client.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Migrated the development harness script layer to BepInEx on bepinex-port (implementation commit 6d78839), leaving main and the reversible legacy loader installation untouched. game_paths reports BepInEx/plugins/MegabonkLevels, LogOutput.log and the Wine launch log; relaunch/readiness checks, failure-evidence collection, MCP log helpers and performance sweeps follow these paths. Plain Wine now requests the winhttp doorstop override instead of version, and both macOS launch routes omit the legacy loader flag. Existing plugin/PDB/NLayer deployment was verified; build task descriptions and props tracking were corrected. Legacy installer helper functions and shared UserData/harness paths remain compatible. Developer and agent instructions document current paths and restarting an already-connected MCP server.

Verification: tests updated first produced 11 expected failures, then all 1160 Python tests passed. task check passed, including build, installer checks, 2781 C# tests and lint; final task lint and git diff --check passed. The mod build has zero warnings/errors; pre-existing test warnings remain. Fresh MCP handlers against the real Wine-hosted game passed relaunch/load/editor, BepInEx-prefixed log reads, state, key, mouse, screenshot and console-log deletion. Screenshots are in gitignored .tools/evidence/bepinex-harness-{console,editor}.png. Final game state is frozen editor with spawns off and invulnerability enabled; version.dll.bak remains parked and doorstop active. Packaging and manager verification remain the next subtask.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
