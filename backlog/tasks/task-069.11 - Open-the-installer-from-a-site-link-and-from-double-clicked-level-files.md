---
id: TASK-069.11
title: Open the installer from a site link and from double-clicked level files
status: To Do
assignee: []
created_date: '2026-11-15 06:00'
labels:
  - installer
dependencies:
  - TASK-069.07
  - TASK-069.10
references:
  - go/internal/window/window.go
parent_task_id: TASK-069
priority: low
ordinal: 247000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
For a truly one-click flow, the site's install button should open the installer with the level already selected, through a URL scheme such as `megabonk://install/<code>`. Double-clicking a `.mblevel.json` should do the same.

MyGo v0.7.4 supports both: `RegisterURLScheme`, `OnOpenURL` and `OnOpenFile`, with file associations (see `deeplink.go` in the module). Registration differs per OS:
- macOS: `Info.plist`.
- Windows: the registry.
- Linux: a `.desktop` file.

Decide whether the installer registers itself on first run or relies on packaging.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Opening a megabonk install link starts the installer with that level pre-selected on Windows, Linux and macOS
- [ ] #2 Double-clicking a .mblevel.json file starts the installer with that file pre-selected
- [ ] #3 How the scheme and file association are registered and removed is documented
- [ ] #4 Link parsing is covered by unit tests
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
