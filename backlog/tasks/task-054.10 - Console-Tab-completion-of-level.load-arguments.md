---
id: TASK-054.10
title: Console Tab completion of level.load arguments
status: Done
assignee: []
created_date: '2026-11-08T18:31:00Z'
updated_date: '2026-11-08T19:00:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_command_registry.cs
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/console_command_tokenizer.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: feature
ordinal: 201000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Console Tab completion only covers the first word, the verb name. `ConsoleCommandRegistry.Complete(prefix)` matches verbs and aliases, and `ConsoleOverlay.Complete()` only runs while the verb is being typed. Extend completion to the argument of `level.load` so a typed prefix of a level title completes from the levels the console already knows (the `levels` list passed to `Bind`).

Design so other verbs can supply their own candidates later, for example `music.track` completing playlist track names, without reworking the completion API. Level titles can contain spaces, so completion must work with whatever quoting the tokenizer supports, and must insert a form that `level.load` then accepts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Complete takes the whole input line and completes the last word against the candidates of the verb in the first word; verb-name completion behaves as before
- [x] #2 level.load <prefix> + Tab completes a level title; repeated Tab cycles the matches and wraps, as verb completion does
- [x] #3 A completed title containing spaces is inserted in a form level.load accepts when submitted
- [x] #4 No matches, an unknown verb, or a verb with no candidates leaves the line unchanged
- [x] #5 The overlay supplies the live level list, and the completion logic is Unity-free with tests written first
- [x] #6 Verified in the running game by typing level.load with a prefix and pressing Tab; docs/development.md console section documents argument completion
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
- [x] #5 task check passes
- [x] #6 Tests written first for testable logic
- [x] #7 Docs updated
- [x] #8 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (tests/MegabonkLevels.Tests/console_command_registry_tests.cs): Complete(line, levels) for verb names (unchanged), level.load argument (stem prefix, cycle and wrap, quoted insert for titles with spaces, inside an open quote, no match / unknown verb / verb with no candidates / second argument unchanged), and an inserted line that binds back through Bind.
2. ConsoleVerb gets an optional candidate provider (argument index + levels -> candidates); level.load supplies level stems. Other verbs can add one later (music.track) with no API change.
3. ConsoleCommandRegistry.Complete takes the whole line: finds the last word quote-aware, completes word 0 against verb names and later words against the verb's candidates. ConsoleCompletion carries the full replacement line per match so the caller never re-quotes.
4. ConsoleOverlay.Complete passes the line up to the caret and the live level list (SafeLevelList), and keeps the active completion so a repeat Tab on an unchanged line cycles via Next().
5. docs/development.md console section: argument completion. Verify in the running game with the megabonk MCP (relaunch, type level.load th, Tab).
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Console Tab completion now covers the argument of level.load. ConsoleCommandRegistry.Complete(line, levels) completes the last word of the whole line, quote-aware: the first word against verb names and aliases as before, later words against the candidates of the verb in the first word. Verbs supply candidates through ConsoleVerb.WithCandidates(argumentIndex, levels), so music.track can add a provider later without an API change. level.load and its alias offer level titles (file names without .mblevel.json) for the first argument only; a title with whitespace is inserted in double quotes. ConsoleCompletion carries the whole replacement line per match (Line), so the overlay does not re-quote. ConsoleOverlay passes the line up to the caret and SafeLevelList(), and keeps the last completion so a repeat Tab on the unedited line calls Next(), which cycles and wraps. The tokenizer gained LastWord for the quote-aware split. docs/development.md documents argument completion and the Tab key behavior.

Evidence: unit tests written first (compile failure on the missing API), then green; they cover prefix completion, alias, empty prefix, case-insensitivity, cycle and wrap, quoted insert, completion inside an open quote, a Bind round trip of the inserted line, and unchanged lines for no match, unknown verb, a verb with no provider and a second argument. task check exits 0 (2707 .NET tests, 1144 Python tests, lint). In the running game (relaunch, console open): level.load th + Tab produced level.load thps; with an empty prefix repeated Tab produced bramblecrown-seeded-check, scratch-minimal, thps, then wrapped to bramblecrown-seeded-check. Not exercised in game: a title containing a space, because no level in the levels folder has one; the quoted form is covered by the unit tests, including the Bind round trip.

Commit d42982b.
<!-- SECTION:FINAL_SUMMARY:END -->
