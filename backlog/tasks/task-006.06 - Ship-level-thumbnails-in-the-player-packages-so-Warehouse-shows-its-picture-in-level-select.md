---
id: TASK-006.06
title: >-
  Ship level thumbnails in the player packages so Warehouse shows its picture in
  level select
status: In Progress
assignee: []
created_date: '2026-11-06 23:11'
updated_date: '2026-11-06 23:24'
labels:
  - bug
  - packaging
  - thps-warehouse
dependencies: []
references:
  - TASK-006.05
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
  - scripts/build_player_package.py
parent_task_id: TASK-006
priority: low
type: bug
ordinal: 171000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A playtester who installed the Windows player package (built with `task package:windows` including the `thps` level and pack) found that the Warehouse had no thumbnail on the Map Selection screen. The level otherwise loaded and played end to end.

Level thumbnails are sidecar images: an image named like the level file sits beside it (`levels/thps.png` beside `levels/thps.mblevel.json`; see the player guide and TASK-006.05). The built zip contains `content/levels/thps.mblevel.json` but no image at all, and `scripts/build_player_package.py` has no handling for sidecar images, so the thumbnail never reaches the player's `UserData/Levels/`.

Outcome: a player who installs a package that includes a level sees that level's thumbnail on the Map Selection screen, the same as in the dev environment. This should hold for every platform package (Windows, Linux, macOS), and the installers' `--check` and `--uninstall` should treat the image like the other installed content.

Not yet confirmed: whether the mod's own thumbnail loading works on a player install once the image is present. Verify that rather than assuming it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A package built with the thps level includes levels/thps.png (and any other level's sidecar jpg/png) next to the level file under content/levels
- [ ] #2 The installer copies the image into UserData/Levels beside the level; --check reports it missing when removed and a rerun repairs it
- [ ] #3 --uninstall removes the installed image along with the level
- [ ] #4 A Python test covers the package builder including sidecar images, and the installer manifest records them
- [ ] #5 Verified on a real install of the rebuilt Windows package: the Warehouse thumbnail shows on the Map Selection screen
- [ ] #6 docs/player-installer.md describes the sidecar image handling
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
