---
id: TASK-056
title: >-
  Migrate MegabonkLevels from MelonLoader to BepInEx IL2CPP for Thunderstore
  distribution
status: To Do
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-08T23:31:00Z'
labels:
  - bepinex
  - thunderstore
dependencies: []
references:
  - 'https://thunderstore.io/c/megabonk/p/BepInEx/BepInExPack_IL2CPP/'
  - 'https://github.com/Zard-Studios/r2modmac'
  - 'https://wiki.thunderstore.io/mods/creating-a-package'
  - 'https://github.com/thunderstore-io/thunderstore-cli'
documentation:
  - docs/development.md
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The mod currently loads through MelonLoader, which no Thunderstore mod manager installs: r2modmac supports BepInEx but explicitly does not implement MelonLoader install/launch, and the Megabonk community's pinned, manager-installed loader is BepInExPack_IL2CPP (6.0.788). Publishing with one-click manager installs therefore requires moving the mod to BepInEx 6 IL2CPP, which touches the mod runtime, the csproj reference set, the dev harness, and packaging.

Runtime target on macOS: the Windows build under a plain-Wine prefix - Wine is preferred over CrossOver for this work.

Structure: two timeboxed spikes close with a recorded go/no-go before any sure-thing task starts. Both no-go closes the effort with findings; a single no-go re-scopes rather than commits.

Rollback strategy (binding for every subtask):
1. Branch isolation - all port work happens off main; main keeps building and shipping the MelonLoader version until the cutover merge.
2. Game-dir reversibility - the BepInEx install is additive and inventoried (doorstop files plus the BepInEx folder); MelonLoader launch options stay configured throughout; applying the recorded rollback manifest restores the MelonLoader-only launch.
3. Release reversibility - tag the last MelonLoader-only build before cutover; Thunderstore versions are immutable, so existing installs keep working; deprecate an old release only after a soak period, never delete.
4. Decision gate - if a spike no-gos, archive the sure-thing subtasks and close this parent with findings; nothing on main needs reverting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both spike subtasks are closed with a recorded go/no-go before any sure-thing subtask moves to In Progress
- [ ] #2 All sure-thing subtasks are completed and their rollback constraints held throughout
- [ ] #3 Main never stopped building the MelonLoader version before the cutover merge
- [ ] #4 Before the first publish, the last MelonLoader-only build is tagged and the licensing decision for bundled level/pack content is recorded
- [ ] #5 Docs describe the BepInEx install, the supported managers, and how a user or developer reverts to the MelonLoader setup
- [ ] #6 If either spike no-gos, this parent is closed with findings and the sure-thing subtasks are archived without main-branch changes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
