---
id: TASK-062
title: >-
  Document how to capture BepInEx and Player.log logs from r2modman and
  Thunderstore Mod Manager
status: To Do
assignee: []
created_date: '2026-11-09T23:52:00Z'
updated_date: '2026-11-09T23:56:00Z'
labels:
  - docs
  - site
  - thunderstore
dependencies: []
documentation:
  - docs/player-guide.md
  - docs/thunderstore.md
  - docs/website.md
  - .github/ISSUE_TEMPLATE/bug_report.yml
priority: medium
type: docs
ordinal: 213000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A Windows player who migrated from the legacy MelonLoader installer to the Thunderstore package could not load the editor or the custom Warehouse level, and support took several round trips to find out why. The game folder had no BepInEx tree, because the mod manager keeps BepInEx inside its profile folder and the player launched from Steam rather than the manager's modded launch, so the game booted vanilla. Nothing in the bug template, docs or site tells a player which log to send or where each manager keeps it. Mod managers already expose log access, so players need pointing at it; the mod does not need its own capture feature. Players should be told to launch through the manager, find the profile's BepInEx log through the manager's own log options, and attach Unity's Player.log. The manager labels and profile paths below are recalled, not verified against current releases, so confirm them on a real install of each manager before publishing. Wiki content under site/ is generated from the docs/ allowlist, so edit docs/ and not the generated copies.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The Logs field in .github/ISSUE_TEMPLATE/bug_report.yml names, for both r2modman and Thunderstore Mod Manager, where to get the profile's BepInEx LogOutput.log, and keeps asking for Player.log and Player-prev.log
- [ ] #2 The bug template asks whether the game was started through the manager's modded launch or directly from Steam, and tells the reporter that a missing BepInEx folder in the game folder is worth stating
- [ ] #3 docs/player-guide.md has an 'If it does not load' section covering launching through the manager, finding and sharing the BepInEx log, and attaching Player.log from the Windows and the Wine or Proton locations
- [ ] #4 The docs state that profile-based managers keep BepInEx in the profile folder, and that launching from Steam only works when the BepInEx files are also in the game folder
- [ ] #5 The manager menu names and profile paths in every edited file match what was observed on a real install of each manager, with unverified items stated as such
- [ ] #6 docs/thunderstore.md carries the same log-capture guidance, or links to the one authoritative section, so the guidance is not duplicated and cannot drift; the package README is covered by TASK-062.01
- [ ] #7 The showcase and wiki in site/ show the log-capture steps through the existing docs allowlist, and the site checks described in docs/website.md pass
- [ ] #8 No file contains personal paths, usernames, tokens or machine identifiers, and the edited markdown follows the repository's markdownlint configuration
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
