---
id: TASK-069.07
title: Add a level-selection screen to the installer window
status: To Do
assignee: []
created_date: '2026-11-15 06:00'
labels:
  - installer
dependencies:
  - TASK-069.05
references:
  - go/internal/window/window.go
  - go/internal/ui/ui.go
parent_task_id: TASK-069
priority: high
ordinal: 243000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The audience is non-technical, so the GUI is the primary interface and the CLI is secondary.

Today the MyGo window (`go/internal/window/window.go`) only shows a confirmation, a step checklist and a details log. Add a screen before that flow where the player chooses what to install:
- The detected game folder, with a way to choose a different one.
- A field to paste one or more share codes or level links.
- A button to add `.mblevel.json` files from disk.
- An "Install or update the level editor" checkbox, defaulting to on when the mod is not detected.
- An Install button that continues into the existing confirm and checklist flow.

Arguments and files passed at launch pre-fill the screen.

MyGo v0.7.4 provides:
- text-input primitives, but no ready-made text field. See `examples/text-input/main.go` in the module cache; the field is a custom widget and the main GUI cost.
- file and folder dialogs (`Dialog.Open`).
- launch-file delivery (`fileArgs`).

The window's event loop must own the main goroutine (see `window.Run`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Launching the installer with no arguments shows the selection screen with the detected game folder
- [ ] #2 The player can paste several codes or links separated by spaces, commas or new lines, and invalid entries are flagged before Install
- [ ] #3 The player can add local .mblevel.json files through a file dialog
- [ ] #4 The player can choose a different game folder through a folder dialog
- [ ] #5 The mod checkbox defaults to on when the mod is not installed and off when it is
- [ ] #6 Codes or files passed on the command line pre-fill the screen
- [ ] #7 Pressing Install leads into the existing confirm, checklist and result flow
- [ ] #8 The input parsing is covered by unit tests, and the screen has been checked by hand on Windows, Linux and macOS
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
