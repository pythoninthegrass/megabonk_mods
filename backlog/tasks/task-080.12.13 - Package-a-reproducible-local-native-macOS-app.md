---
id: TASK-080.12.13
title: Package a reproducible local native macOS app
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.11
  - TASK-080.12.12
references:
  - TASK-048.02
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: feature
ordinal: 280000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The deliverable is a working local arm64 app for Apple silicon, not a collection of probe commands or a public redistribution of the game's binaries. This task assembles the verified runtime, player, graphics, device support and editor-mod artifacts into a reproducible local build using the user's legitimately installed game content. Public release hosting, notarization and broad installer redesign are not implied by this task. Do not require disabling system security globally to launch the package.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented build/package entry point produces a launchable arm64 macOS app from pinned prerequisites and local game content, without Wine, CrossOver or Rosetta.
- [ ] #2 The packaged app passes native menu/gameplay/save and level-editor round-trip smoke checks on the target Apple silicon machine, with all required resources included.
- [ ] #3 The workflow handles local signing and runtime library/resource paths, reports missing or mismatched inputs, and is repeatable from clean output without damaging the source game installation.
- [ ] #4 Build identity, prerequisites and known limits are documented; automated checks prevent proprietary content and host-specific secrets/paths from entering tracked or public artifacts.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
