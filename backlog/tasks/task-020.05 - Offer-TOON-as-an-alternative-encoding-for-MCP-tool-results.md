---
id: TASK-020.05
title: Offer TOON as an alternative encoding for MCP tool results
status: To Do
assignee: []
created_date: '2026-10-27T20:09:00Z'
updated_date: '2026-10-27T20:11:00Z'
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
- [ ] #1 All structured MCP tool results pass through one encoding function, and a setting selects the encoding: the current JSON, minified JSON, or TOON
- [ ] #2 toon-format is pinned to an exact working version, not a floating range, and a test fails if `encode()` raises NotImplementedError
- [ ] #3 Payloads from this server (state, list_levels, ui_tree) are captured from a live session and token counts are recorded for each encoding
- [ ] #4 If the TASK-020.01 object query exists when the decision is made, its MapData result is measured too; otherwise the decision records that the uniform-rows case was not measured and should be re-measured once it lands
- [ ] #5 The default encoding is chosen by a threshold written down before measuring, and the measured numbers and the threshold are recorded in docs/development.md
- [ ] #6 Error messages and values the MCP framework requires as plain text or image content are not re-encoded
- [ ] #7 Every encoding round-trips the captured payloads in offline tests, including strings containing quotes, commas, colons and newlines
- [ ] #8 With the setting unset the output matches today's results unless the measured decision changes the default, and any change is documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
