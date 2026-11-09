---
id: TASK-048.02
title: Enforce the public release content and local-only asset boundary
status: To Do
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07 01:57'
labels:
  - onboarding
dependencies:
  - TASK-047
documentation:
  - docs/player-installer.md
  - docs/asset-bundles.md
  - docs/music.md
parent_task_id: TASK-048
priority: high
type: enhancement
ordinal: 178000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Public releases must contain only reviewed distributable inputs. Keep THPS source/extracted content, OST MP3s, proprietary-derived packs, game binaries and locally generated game-reference assemblies local. Mod compilation currently depends on local game references; this is not authorization to publish those references. Optional local pack creation remains explicit opt-in and functional without soundtrack files. Review project and dependency redistribution permissions; local handling alone is not a legal-rights determination.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented explicit allowlist defines releasable files and required third-party notices, with unresolved redistribution rights blocking publication of affected content.
- [ ] #2 Public package validation rejects unapproved extra files, game references and proprietary or proprietary-derived optional content, including disguised or unexpectedly staged inputs.
- [ ] #3 Public build/upload/cache inputs exclude local-only assets and generated game references; regression checks demonstrate rejection of representative forbidden inputs.
- [ ] #4 Optional local THPS/OST workflows require deliberate user input, do not upload their inputs or outputs, and absence of those inputs does not break the public starter experience.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
