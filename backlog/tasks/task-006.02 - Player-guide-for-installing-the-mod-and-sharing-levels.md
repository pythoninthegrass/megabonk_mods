---
id: TASK-006.02
title: Player guide for installing the mod and sharing levels
status: Done
assignee: []
created_date: '2026-10-06 21:44'
updated_date: '2026-11-04 20:07'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-006
priority: medium
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
- [x] #1 A player-facing guide (distinct from the contributor-facing docs/modding-setup.md) explains installing MelonLoader and the mod as an end user, not a developer building from source
- [x] #2 The guide explains how to locate UserData/Levels/, share a level file, and install a level someone else shared
- [x] #3 The guide clearly states this is unofficial, non-Workshop, fan-made content
- [x] #4 The guide is linked from docs/modding-setup.md
- [x] #5 If no release/packaging mechanism exists yet for distributing the built mod to non-technical users, that gap is explicitly flagged rather than glossed over
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved approach. Write docs/player-guide.md in plain language: install with the packaged installer per platform (manual steps as fallback), find UserData/Levels, share a .mblevel.json (Discord or forum attachment), install a shared level, and state that this is unofficial fan-made content with no Steam Workshop integration. Flag that no published download URL exists yet. Link the guide from docs/modding-setup.md and README.md.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added docs/player-guide.md in plain language: install through the packaged installer per platform with a pointer to the manual fallback, finding UserData/Levels, playing and sharing a level, missing asset packs, and a statement that the mod is unofficial, fan-made and not Steam Workshop. The guide flags that no public download URL exists yet and that the Windows installer has only been tested in a VM. Linked from README.md and docs/modding-setup.md, which gained an "Installing by hand (for players)" section.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
