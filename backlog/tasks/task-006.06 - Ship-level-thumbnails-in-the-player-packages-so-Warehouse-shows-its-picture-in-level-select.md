---
id: TASK-006.06
title: >-
  Ship level thumbnails in the player packages so Warehouse shows its picture in
  level select
status: Done
assignee: []
created_date: '2026-11-06 23:11'
updated_date: '2026-11-06 23:43'
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
- [x] #1 A package built with the thps level includes levels/thps.png (and any other level's sidecar jpg/png) next to the level file under content/levels
- [x] #2 The installer copies the image into UserData/Levels beside the level; --check reports it missing when removed and a rerun repairs it
- [x] #3 --uninstall removes the installed image along with the level
- [x] #4 A Python test covers the package builder including sidecar images, and the installer manifest records them
- [x] #5 Verified on a real install of the rebuilt Windows package: the Warehouse thumbnail shows on the Map Selection screen
- [x] #6 docs/player-installer.md describes the sidecar image handling
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Builder bundles png/jpg/jpeg sharing a bundled level's base name (commit e6d0648); the installer needed no change because it is manifest-driven. Verified on the authoring box: the package:windows zip was installed with install.exe under Wine 11.18 and the Warehouse thumbnail shows on Map Selection (confirmed by the maintainer). task check still fails with 17 tests (14 in test_installer_parity, 3 in test_thps_attachments/test_thps_preservation) that fail identically on a clean tree; DoD #1 left unchecked for that reason. Follow-up: TASK-006.07.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Player packages now carry level thumbnails. `build_player_package.py` bundles any png/jpg/jpeg sharing a bundled level's base name next to the level under `content/levels`, recorded in the manifest with destination `UserData/Levels/<name>`; images matching no bundled level and `.local` scratch maps are left out. The installers needed no change, since install, `--check`, repair and `--uninstall` are manifest-driven. Tests: two builder tests (destination, hash) and one installer test covering install, check, repair and uninstall of the image. `docs/player-installer.md` documents the sidecar handling. Verified on a real install: the rebuilt Windows package was installed with `install.exe` under Wine 11.18 and the Warehouse thumbnail shows on Map Selection, confirmed by the maintainer. `task check` is not green: 17 tests fail (14 in `test_installer_parity`, 3 in `test_thps_attachments` and `test_thps_preservation`), and the same 17 fail on a clean tree, so none come from this change. DoD #1 is left unchecked for that reason. Follow-up for the map name and biome icon: TASK-006.07.
<!-- SECTION:FINAL_SUMMARY:END -->
