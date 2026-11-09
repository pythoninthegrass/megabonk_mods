---
id: TASK-062.01
title: Add log-capture and launch guidance to the Thunderstore package README
status: To Do
assignee: []
created_date: '2026-11-09T23:55:00Z'
labels:
  - docs
  - thunderstore
dependencies: []
documentation:
  - pkg/README.md
  - docs/thunderstore.md
  - AGENTS.md
parent_task_id: TASK-062
priority: medium
type: docs
ordinal: 214000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The README shown on the Thunderstore package page is the first place a player looks when the mod does not load, and it does not help with the failure seen in support. Install step 3 says only "Start the modded game", which does not say to launch through the mod manager. The troubleshooting paragraph says that no BepInEx log "usually means the loader/runtime or Wine override is missing", which is Wine-specific and misses the common Windows case: a profile-based manager keeps BepInEx in the profile folder, so a plain Steam launch boots the vanilla game and writes no BepInEx log. The README also never mentions Unity's Player.log or how to get the log out of r2modman or Thunderstore Mod Manager. The page README is separate from the downloadable ZIP and is changed through the authenticated Thunderstore markdown README update endpoint described in AGENTS.md, which does not upload a package or bump the version. The manager menu names and profile paths used must be confirmed on a real install of each manager, as in the parent task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Install step 3 in pkg/README.md says to launch through the mod manager's modded launch, and says a direct Steam launch only works when the BepInEx files are also in the game folder
- [ ] #2 The troubleshooting section covers the Windows case of no BepInEx log because the game was started outside the manager, alongside the existing Wine and runtime cause
- [ ] #3 The troubleshooting section tells players how to get the profile's BepInEx LogOutput.log from r2modman and from Thunderstore Mod Manager, and where Unity's Player.log is on Windows and under Wine or Proton
- [ ] #4 The new text follows the parent task's confirmed manager menu names and paths, with anything unconfirmed marked as such, and uses no personal paths or identifiers
- [ ] #5 pkg/README.md renders correctly in Thunderstore's Markdown Preview tool, and the markdown passes the repository's markdownlint configuration
- [ ] #6 The live package page README matches pkg/README.md after the README-only update, with no package upload or version bump, and the token is read from the environment and never printed or placed in command arguments
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
