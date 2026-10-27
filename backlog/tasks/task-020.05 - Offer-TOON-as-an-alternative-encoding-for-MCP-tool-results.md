---
id: TASK-020.05
title: Offer TOON as an alternative encoding for MCP tool results
status: Done
assignee:
  - Claude
created_date: '2026-10-27T20:09:00Z'
updated_date: '2026-10-27T20:19:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
references:
  - 'https://github.com/toon-format/toon-python'
  - 'https://github.com/toon-format/toon'
  - >-
    /Users/lance/git/osascript-mcp/backlog/tasks/task-001.13 -
    Add-TOON-output-formatting-option-for-tool-results.md
parent_task_id: TASK-020
priority: low
type: enhancement
ordinal: 85000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The megabonk MCP server returns its structured results (state, paths, list_levels, ui_tree, and the live-object query from TASK-020.01 once it exists) as JSON, which spends tokens on braces, quotes and repeated keys. TOON (Token-Oriented Object Notation) drops that overhead, and it reduces tokens most on uniform arrays of objects such as the object query's rows. Prior art in ~/git/osascript-mcp TASK-001.13 added TOON behind an environment variable and measured it before choosing a default: on a real 13-call capture TOON beat pretty-printed JSON by 46% but minified JSON by only 12.8%, and was worse than minified JSON on small flat arrays. That task also found that an unpinned `toon-format` install resolves to 0.1.0, a stub whose `encode()` raises NotImplementedError; 0.9.0b1 works. This task adds TOON as a selectable encoding here and decides the default from measurements of this server's own payloads, not from the other project's numbers. It does not depend on TASK-020.01; if it lands first, the uniform-rows case is measured later.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All structured MCP tool results pass through one encoding function, and a setting selects the encoding: the current JSON, minified JSON, or TOON
- [x] #2 toon-format is pinned to an exact working version, not a floating range, and a test fails if `encode()` raises NotImplementedError
- [x] #3 Payloads from this server (state, list_levels, ui_tree) are captured from a live session and token counts are recorded for each encoding
- [x] #4 If the TASK-020.01 object query exists when the decision is made, its MapData result is measured too; otherwise the decision records that the uniform-rows case was not measured and should be re-measured once it lands
- [x] #5 The default encoding is chosen by a threshold written down before measuring, and the measured numbers and the threshold are recorded in docs/development.md
- [x] #6 Error messages and values the MCP framework requires as plain text or image content are not re-encoded
- [x] #7 Every encoding round-trips the captured payloads in offline tests, including strings containing quotes, commas, colons and newlines
- [x] #8 With the setting unset the output matches today's results unless the measured decision changes the default, and any change is documented
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
1. Add `_encode(payload)` in scripts/mcp_server.py returning a CallToolResult; every dict-returning tool (paths, relaunch, load, state, editor, freeze, resume, invulnerable, camera, key, mouse, ui_tree, save_level, list_levels, click_widget, type_text, teleport, dismiss_levelup) goes through it. Errors stay ToolError; screenshot (image), log_tail, log_wait and quit (plain text/bool) are untouched.
2. Setting: env var MEGABONK_MCP_ENCODING = json (default) | json-min | toon, read per call. json reproduces today's output (indent-2 text plus structured_content); json-min and toon emit text only, no structured_content, since that duplicate would cancel the saving.
3. Pin toon-format==1.2.0 in the PEP 723 header and the taskfile `--with`; verified encode/decode round-trip on 0.9.0b1, 1.0.0, 1.1.0, 1.2.0 (0.1.0 is the NotImplementedError stub).
4. Tests first (tests/test_mcp_server.py): per-encoding result shape, round-trip of tricky strings (quotes, commas, colons, newlines), default unchanged, invalid setting is a tool error, toon encode() not stubbed.
5. Write the threshold before measuring: switch the default to TOON only if it beats minified JSON by at least 15% in total tokens across the captured state/list_levels/ui_tree payloads and is not worse on any payload by more than 5%. Capture live payloads via the megabonk MCP, count tokens, record numbers and decision in docs/development.md. TASK-020.01 object query is checked for existence at decision time.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `_encode` in scripts/mcp_server.py: every structured tool result goes through it, selected by `MEGABONK_MCP_ENCODING` (json default, json-min, toon). json keeps today's indented text plus structuredContent; the other two send text only. Errors, screenshots, log_tail, log_wait and quit are not re-encoded. toon-format pinned to 1.2.0 in the script header and taskfile; a test guards against the 0.1.0 stub. Live payloads (state, list_levels, ui_tree) are in tests/fixtures/mcp_payloads and round-trip through all three encodings. With the threshold fixed beforehand (total >=15% below minified JSON and no payload >5% worse), TOON saved 27.0% in total (cl100k_base proxy tokens) but was 22.0% worse on state, so the default stays json. The object query (TASK-020.01) does not exist yet; the uniform-rows case is noted in docs/development.md for re-measurement. `task check` passes (247 tests).
<!-- SECTION:FINAL_SUMMARY:END -->
