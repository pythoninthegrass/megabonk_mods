---
id: TASK-054.07
title: >-
  Console fzf-style fuzzy history search on Ctrl-R, Enter runs the selection and
  Esc cancels
status: To Do
assignee: []
created_date: '2026-11-08T16:49:00Z'
updated_date: '2026-11-08T16:51:00Z'
labels: []
dependencies: []
references:
  - tools/videos/fzf.mkv
  - tools/videos/fzf.mp4
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/console_history.cs
  - 'https://github.com/junegunn/fzf'
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: feature
ordinal: 198000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add an fzf-style fuzzy finder to the in-game console, over the remembered command history (200 entries, restored from `console_log.jsonl`). The behaviour follows the fzf walkthrough in `tools/videos/fzf.mkv` (about 69s to 195s) and the maintainer's own shell history finder in `tools/videos/fzf.mp4`, with the fzf docs (junegunn/fzf README, man page and the shell key-bindings wiki) as the reference for syntax.

Behaviour to reproduce:
- Ctrl-R opens the finder over the history list (confirmed trigger). The query is typed in the console input line and the list filters on every keystroke.
- The list is drawn above the prompt with the newest entry nearest the prompt (fzf's default layout), the selected row is highlighted with a marker in the gutter, and the characters that matched the query are highlighted inside each row.
- An info line shows `matched/total` (e.g. `46/259`) and `+S`. Results stay in chronological order, not sorted by relevance, as in fzf.mp4 (confirmed).
- Up/Down (and Ctrl-P/Ctrl-N) move the selection, clamped at the ends. The list scrolls to keep the selection visible.
- Search syntax is fzf's extended-search mode, space-separated terms ANDed: `sbtrkt` fuzzy, `'wild` exact, `^music` prefix, `.mp3$` suffix, `!fire` inverse exact, `!^music` and `!.mp3$` inverse prefix and suffix, and a lone `|` as OR (`^core go$ | rb$ | py$`). Matching is smart-case: case-insensitive unless the query contains an uppercase letter.
- **Enter accepts the selected entry and executes it** as if it had been typed and submitted: it is echoed to scrollback, run through the same bind and plan path as `Submit`, and recorded in history. This is the part fzf.mp4 did not show: the recording ended without running the selection.
- **Esc cancels the finder and returns to the normal input line with the cursor where it was and the line unchanged.** Nothing is run, nothing is added to history, and the console stays open (Esc outside the finder still closes the console).
- With zero matches Enter does nothing.

Out of scope: Tab/Shift-Tab multi-select, preview windows, `--bind` customisation, toggling relevance sort, and fuzzy completion over verbs (Tab completion already covers verbs).

Implementation notes: the matcher, query parser and filtering are Unity-free pure logic that belongs next to `console_history.cs` and `console_command_tokenizer.cs`, linked into `tests/MegabonkLevels.Tests` and unit tested there. The overlay only reads input and draws rows through `EditorInput`, so it stays drivable through the harness `key` and `type` commands. Scrollback rows must stay taller than the font line (see "Text rows must be taller than the font's line" in `docs/development.md`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A pure fuzzy matcher and extended-search query parser implement fzf's term types (fuzzy, 'exact, ^prefix, suffix$, !inverse, !^ and !$ forms, | OR, space AND) with smart-case, covered by unit tests written first
- [ ] #2 Matching returns the matched character positions so the overlay can highlight them, covered by unit tests
- [ ] #3 Ctrl-R opens the finder over the remembered history; typing filters the list live and an info line shows matched/total
- [ ] #4 Up/Down and Ctrl-P/Ctrl-N move a highlighted selection that scrolls with the list and clamps at the ends
- [ ] #5 Enter executes the selected entry through the normal submit path (echoed, run, recorded in history) and closes the finder; with zero matches Enter does nothing
- [ ] #6 Esc cancels the finder and restores the input line and caret exactly as they were before Ctrl-R, running nothing and adding no history entry; the console stays open
- [ ] #7 Matched characters are highlighted in each row and the selected row is visibly marked, confirmed by harness screenshot in the running game
- [ ] #8 The behaviour, key bindings and search syntax are documented in docs/development.md under the console overlay section
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
