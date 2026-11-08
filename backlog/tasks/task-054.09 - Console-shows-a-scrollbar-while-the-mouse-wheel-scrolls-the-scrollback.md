---
id: TASK-054.09
title: Console shows a scrollbar while the mouse wheel scrolls the scrollback
status: To Do
assignee: []
created_date: '2026-11-08T17:15:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/console_scrollback.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: low
type: feature
ordinal: 200000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a scrollbar to the in-game console scrollback. It appears only when the mouse wheel scrolls the scrollback and disappears 2 seconds after the last wheel event; it is hidden otherwise, including while PageUp/PageDown scroll. The thumb reflects the current scroll position and the visible fraction of the scrollback. Timing and thumb geometry go in Unity-free logic so they are unit tested. Document the behavior under "Console overlay" in docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Mouse wheel scrolling over the console shows a scrollbar whose thumb position and size match the scroll offset and visible fraction
- [ ] #2 The scrollbar disappears 2 seconds after the last wheel event, and each further wheel event restarts the 2 second timer
- [ ] #3 The scrollbar is not shown at rest, when the scrollback fits on screen, or for PageUp/PageDown scrolling
- [ ] #4 Visibility timing and thumb geometry are covered by unit tests written first
- [ ] #5 Confirmed in the running game by harness screenshots showing the bar visible and then hidden
- [ ] #6 Behavior documented in docs/development.md under the console overlay section
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
