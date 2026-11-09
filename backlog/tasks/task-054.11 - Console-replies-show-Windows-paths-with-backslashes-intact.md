---
id: TASK-054.11
title: Console replies show Windows paths with backslashes intact
status: Done
assignee: []
created_date: '2026-11-08T20:05:00Z'
updated_date: '2026-11-08T20:12:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_state.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
documentation:
  - docs/development.md
modified_files:
  - src/MegabonkLevels.Mod/console_overlay.cs
  - tests/MegabonkLevels.Tests/console_state_tests.cs
  - tests/test_console_rendering.py
  - docs/development.md
parent_task_id: TASK-054
priority: low
type: bug
ordinal: 202000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A console reply that contains a Windows path with backslashes prints garbled. After `debug.screenshot tony.png` under Wine on macOS the reply should read `screenshot: Z:\<repo>\.tools\evidence\tony.png`, but the `\t` where the folder meets a file name starting with `t` is lost or shown as a tab, so the console prints `evidenceony.png` or `evidence     ony.png` instead of `evidence\tony.png`. Latest.log records the correct path, so the file lands in the right place and only the text the console shows is wrong. The reply is the main way to learn where a screenshot or saved level went, so a garbled path defeats it. Other replies that carry a path or any backslash (for example a saved-level path) are likely affected the same way but have not been checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A console reply containing a backslash path (for example the debug.screenshot reply for a relative name) prints the path exactly as the game wrote it, with no characters dropped and no tab inserted
- [x] #2 Any other console reply that carries a path or backslash text is checked, and each affected one is fixed or recorded as unaffected
- [x] #3 A test written first reproduces the garbled reply and fails before the fix
- [x] #4 Verified in the running game by running debug.screenshot with a relative name and reading the printed path against Latest.log
- [x] #5 docs/development.md notes the behavior if it changes how results are reported
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
1. Trace reply formatting, scrollback/persistence and TMP label setup; audit all path-bearing reply producers.
2. Before the fix, add a failing rendering-configuration regression guard and path-preservation unit coverage, and capture the live debug.screenshot corruption. The Unity-free test project cannot execute TMP, so verify the actual glyph rendering in-game.
3. Disable TMP backslash control-sequence parsing on console output labels without changing stored text or finder rich-text highlighting; document literal backslashes.
4. Build/deploy, clear persisted console output and relaunch, compare a relative screenshot reply with Latest.log, exercise other path/error replies and history search. Run task check and finalize with a conventional commit if all gates pass.

The same TMP default also affects the console input field and history-finder rows. Disable it on the input label too; finder rows share the output labels and keep rich-text highlighting enabled.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Red before fix: uv run pytest tests/test_console_rendering.py -q -n 0 failed both output/input TMP-configuration guards. Four new C# path-preservation cases passed before the fix, isolating corruption to rendering rather than formatting/wrapping. Live before image .tools/evidence/task05411-before-ui.png shows evidence05411-before.png; Latest.log retained evidence\t05411-before.png. The automated red test guards rendering wiring, not TMP glyph execution (which requires Unity).

Applied parseCtrlCharacters=false only to console output/input labels. task check passed: build, installer smoke test, 2770 C# tests, 1150 Python tests, markdownlint and ruff (ruff sorted the new test imports). After relaunch, .tools/evidence/task05411-after-ui.png shows the screenshot path and duplicate-file error with intact \t; both agree with Latest.log. level.save t05411-path-check renders its path as proper JSON with doubled backslashes, not TMP-interpreted escapes.

Path-reply audit: debug.screenshot success and generic error replies were affected and now share corrected output labels. level.save, level.new and level.list emit structured path/directory fields through ReplyFor's JSON fallback; JSON escaping is unchanged and now displayed literally. level.load's harness success is ok (no path); editor-load messages carry a name rather than a resolved path, and failures still use the common error path. Music messages and arbitrary query/material/shader strings also use those same labels; no per-producer escaping is necessary.

History search and the input field verified in .tools/evidence/task05411-finder-ui.png and task05411-input-ui.png: a recalled Windows-path command keeps its backslashes, and amber fuzzy highlighting still works. Removed only the temporary t05411-path-check.mblevel.json created for live save verification. Evidence screenshots remain gitignored. All acceptance criteria verified; the failing-before-fix automated coverage is explicitly a TMP configuration guard, supplemented by live glyph-level before/after reproduction.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Disabled TMP backslash control parsing on console output and input labels, preserving Windows paths in replies, errors, history and recalled input without changing JSON or persisted text. Added test-first TMP wiring guards and four path-preservation unit cases; documented literal-backslash behavior. Verified before/after in the running Wine game against Latest.log, including relative screenshot success, existing-file error, saved-level JSON, history highlighting and input recall. task check passed (2770 C# tests, 1150 Python tests, build, installer smoke test and lint). Conventional fix commit created; finalized task record included with it.
<!-- SECTION:FINAL_SUMMARY:END -->
