---
id: TASK-014
title: Resolve IL2CPP stack trace logged when the editor closes
status: To Do
assignee: []
created_date: '2026-10-23T17:43:00Z'
labels:
  - editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_mode.cs
priority: low
type: bug
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Closing the in-game editor reportedly prints an IL2CPP stack trace (a `--- BEGIN IL2CPP STACK TRACE ---` block) in MelonLoader's `Latest.log` every time. It has not been reproduced yet: toggling the editor off through the harness with an object selected logged only `EditorMode: exited` and no trace, so the trace may come from a different close path, such as the run ending (quit to menu, death, level reload) while the editor is open. The only IL2CPP trace seen in the log so far is the unrelated startup `DevHarness: 'SteamReady' failed: Steamworks is not initialized`, which is expected under Wine. The first step is to capture the exception text and the close path that triggers it. If it is a real fault, such as touching destroyed Il2Cpp objects during editor cleanup, fix it. If it is harmless noise, suppress it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The close path and exception type that produce the trace are identified and recorded in the task notes
- [ ] #2 If the trace comes from a real fault in the mod, the fault is fixed and closing the editor by that path logs no IL2CPP stack trace
- [ ] #3 If the trace is harmless noise, it is suppressed without hiding other errors, and the reason is documented in docs/*.md
- [ ] #4 A regression test covers the fix where the logic is testable outside the game
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
