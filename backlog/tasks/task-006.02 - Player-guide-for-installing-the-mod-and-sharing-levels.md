---
id: TASK-006.02
title: Player guide for installing the mod and sharing levels
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
updated_date: '2026-10-31T03:12:00Z'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-006
priority: medium
type: docs
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-006 first for full context.

Write a player-facing (non-technical, not a dev-oriented doc like `docs/modding-setup.md`) guide covering:

- How to install MelonLoader and this mod as an end user (not a contributor building from source) — this likely requires a packaged release artifact and install steps distinct from the `task game:melonloader:install` dev-tooling flow from TASK-001; identify what a non-technical user's install flow should actually look like (a zip to extract into the game folder? an installer script?) and document that, flagging if a packaging/release task is needed that doesn't exist yet.
- How to find the `UserData/Levels/` folder and share a `.mblevel.json` file with someone else (Discord attachment, forum upload, etc.), and how to install a level someone shared with you.
- A plain-language explanation that this is unofficial, third-party, fan-made content with no first-party Steam Workshop integration, so players understand why there's no in-Steam subscribe button.

Link this guide from `docs/modding-setup.md` (TASK-001.04) and from the Map Selection entry's description if there's a natural place to surface a link/hint (optional, see TASK-006.01).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A player-facing guide (distinct from the contributor-facing docs/modding-setup.md) explains installing MelonLoader and the mod as an end user, not a developer building from source
- [ ] #2 The guide explains how to locate UserData/Levels/, share a level file, and install a level someone else shared
- [ ] #3 The guide clearly states this is unofficial, non-Workshop, fan-made content
- [ ] #4 The guide is linked from docs/modding-setup.md
- [ ] #5 If no release/packaging mechanism exists yet for distributing the built mod to non-technical users, that gap is explicitly flagged rather than glossed over
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-10-31T03:12:00Z

---

The packaging gap this task must flag (AC #5) is now tracked rather than open-ended: TASK-006.04 defines the packaged player download and the shared installer contract, with TASK-006.04.01 (Linux), TASK-006.04.02 (Windows) and TASK-006.04.03 (macOS) implementing it per platform. Nothing exists yet, so the guide still documents the manual steps as the working route and links those tasks as the gap rather than glossing over it.

The guide's verification run also feeds those installer tasks: it settles how the .NET 6 runtime reaches MelonLoader under Proton (a runtime directory inside the game folder versus installing into the Proton prefix) and whether a DLL-override launch option is needed. Record both findings in the guide, because the installer tasks depend on them.

---
<!-- COMMENTS:END -->
