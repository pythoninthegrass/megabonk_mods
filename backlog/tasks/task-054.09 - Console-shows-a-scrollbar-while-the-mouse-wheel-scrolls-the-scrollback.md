---
id: TASK-054.09
title: Console shows a scrollbar while the mouse wheel scrolls the scrollback
status: Done
assignee: []
created_date: '2026-11-08T17:15:00Z'
updated_date: '2026-11-09 05:26'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/console_scrollback.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: low
ordinal: 200000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a scrollbar to the in-game console scrollback. It appears only when the mouse wheel scrolls the scrollback and disappears 2 seconds after the last wheel event; it is hidden otherwise, including while PageUp/PageDown scroll. The thumb reflects the current scroll position and the visible fraction of the scrollback. Timing and thumb geometry go in Unity-free logic so they are unit tested. Document the behavior under "Console overlay" in docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Mouse wheel scrolling over the console shows a scrollbar whose thumb position and size match the scroll offset and visible fraction
- [x] #2 The scrollbar disappears 2 seconds after the last wheel event, and each further wheel event restarts the 2 second timer
- [x] #3 The scrollbar is not shown at rest, when the scrollback fits on screen, or for PageUp/PageDown scrolling
- [x] #4 Visibility timing and thumb geometry are covered by unit tests written first
- [x] #5 Confirmed in the running game by harness screenshots showing the bar visible and then hidden
- [x] #6 Behavior documented in docs/development.md under the console overlay section
- [x] #7 The harness can inject a mouse wheel event (InjectedInputQueue, harness command, run.py and MCP tool), covered by unit tests written first
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Unity-free logic: ConsoleScrollbar (visibility timer, thumb geometry) and ConsoleScrollback.ScrollBy/Offset/Viewport, tests first (done, green).
2. Overlay: ReadWheel in ConsoleOverlay.ReadInput scrolls 3 lines per notch while the pointer is over the panel and restarts the 2 s timer; a thumb Image under the scrollback is placed from ConsoleScrollbar.Thumb and hidden unless Visible (done, builds).
3. Harness wheel injection (scope added with the maintainer's approval): scroll event in InjectedInputQueue read by EditorInput.MouseScrollDelta, a harness command, run.py verb and MCP tool, tests first.
4. Relaunch, open the console, fill scrollback, inject wheel, screenshot at 0 s and after 2 s.
5. Document under "Console overlay" in docs/development.md, run task check, commit.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a console scrollbar that shows only while the mouse wheel scrolls the scrollback and hides 2 seconds after the last wheel event. Timing and thumb geometry live in the Unity-free ConsoleScrollbar (console_scrollbar.cs); ConsoleScrollback gained Offset, Viewport and ScrollBy. ConsoleOverlay reads the wheel (3 lines per notch, pointer over the panel, finder closed) and places a thumb image. Because the harness could not inject a wheel, the mouse command gained a scroll action with a delta field (InjectedInputQueue.EnqueueScroll, harness parser, run.py mouse scroll --delta, MCP mouse delta). Verified in the running game: no bar at rest, bar plus 6 scrolled lines 0.5 s after a 2-notch wheel event, no bar 2.5 s later, no bar after PageUp. Evidence PNGs are in .tools/evidence (scrollbar-rest, -visible, -hidden, -pageup). Documented under Console overlay and the mouse command docs in docs/development.md. The running MCP server predates the mcp_server.py change, so it needs a restart before its mouse tool accepts scroll.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
