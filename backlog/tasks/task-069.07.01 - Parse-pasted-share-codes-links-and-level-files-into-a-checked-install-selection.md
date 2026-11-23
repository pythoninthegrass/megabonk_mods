---
id: TASK-069.07.01
title: >-
  Parse pasted share codes, links and level files into a checked install
  selection
status: To Do
assignee: []
created_date: '2026-11-23T06:52:00Z'
updated_date: '2026-11-23T06:52:00Z'
labels:
  - installer
dependencies: []
references:
  - go/internal/site/site.go
  - go/internal/plan/plan.go
  - go/internal/site/site_test.go
documentation:
  - docs/player-installer.md
parent_task_id: TASK-069.07
priority: high
type: enhancement
ordinal: 298000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The installer's level-selection screen lets a non-technical player paste several share codes or level links in one field. The screen cannot flag a bad entry before Install, or pre-fill from launch arguments, until the text is turned into a checked list of entries by logic that does not depend on the window. This is the testable, GUI-free part of the selection screen: a pure function the window will call later. It reuses the installer's existing share-code and link normalization, so the selection screen and the command line accept exactly the same inputs and cannot drift apart.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pasted text containing several entries separated by spaces, commas, semicolons or new lines, in any mix, yields one entry per item in the order given; blank items and repeated separators produce nothing
- [ ] #2 A double-quoted span is one entry whatever it contains, so a local file path with spaces can be pasted as "C:\My Levels\a.mblevel.json"; an unterminated quote is flagged invalid rather than swallowing the rest of the text
- [ ] #3 Each entry reports its original text, whether it is valid, and for a valid share code or site level link the canonical share code; an invalid entry carries a message that names the entry the player typed
- [ ] #4 Whether a code or link entry is valid uses the same rules as the command line, so a code, a code without dashes, lower case, and a megabonkmod.party level link are valid, and a link to another host, a malformed code or free text are flagged invalid; a bare level name is flagged invalid here, because looking one up needs the network
- [ ] #5 A path to a local .mblevel.json file is recognized as a file entry, not flagged as an invalid code; this logic only classifies the text and never reads the disk or the network
- [ ] #6 The same level named twice, as a code and as a link to it, or as a code in two spellings, appears once in the selection and the duplicate is reported rather than silently dropped
- [ ] #7 Launch arguments are accepted through the same function, so a code, link or file path passed on the command line pre-fills the selection identically to pasted text
- [ ] #8 Tests were written first and cover mixed separators, quoting, empty input, each invalid kind, duplicates and file paths; the function lives beside the installer's other input handling and adds no GUI or network dependency
- [ ] #9 docs/player-installer.md states which pasted inputs the installer accepts, how to paste a path with spaces, and how invalid entries are reported
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
