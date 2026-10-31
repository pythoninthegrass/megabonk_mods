---
id: TASK-006.04.01.01
title: Port the player installer to a single static Go binary
status: To Do
assignee: []
created_date: '2026-10-31T08:14:00Z'
labels:
  - tooling
dependencies: []
references:
  - 'https://github.com/bitfield/script'
  - docs/player-installer.md
documentation:
  - docs/player-installer.md
modified_files:
  - go/
  - taskfiles/package.yml
  - docs/player-installer.md
parent_task_id: TASK-006.04.01
priority: medium
type: feature
ordinal: 128000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Python installer works but still asks the player for an interpreter: the 3.11 floor is met by a system python3 on current distros, not on older ones, and install.sh exists only to pick and gate it. A single static binary - CGO_ENABLED=0, cross-compiled - removes the interpreter problem entirely: the player downloads one file and runs it. Keep the package/manifest contract exactly as docs/player-installer.md defines it (megabonk-player-package/1, the install record, exit codes 0/1/2/3/4/10) so existing packages install unmodified and the Windows and macOS ports can inherit the same shape. Use bitfield/script only where its pipeline sugar genuinely beats os/exec; everything else is stdlib (archive/zip, encoding/json, os, path/filepath). The Python installer stays the reference implementation: port module by module (vdf, steam, gamebuild, manifest, content, proton, plan, ui, cli), compare against it on the same synthetic fixtures, and do not make Go the default path until the binary reproduces the live checks on the AlmaLinux host (discovery of the relocated Flatpak root, native-build refusal with exit 4, full install/check/uninstall, headless text progress).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A clean checkout cross-compiles with CGO_ENABLED=0 to one static binary per target (at least linux/amd64 and linux/arm64); file/ldd confirm no dynamic dependency beyond libc-not-at-all, and the binary runs on a host with no Go and no Python
- [ ] #2 The manifest contract is byte-compatible: load of megabonk-player-package/1, refusal of every malformed manifest the Python loader refuses (naming the same bad key), and vendor kind lookup behave identically
- [ ] #3 Full lifecycle on the synthetic Windows-layout trees the Python tests use - install, --check no-drift, drift repair naming exactly the missing files with exit 10, uninstall - matches the Python installer's behaviour and exit codes 0/1/2/3/4/10
- [ ] #4 On the AlmaLinux host's real layout: the relocated Flatpak root is found through its grant, the unmounted library is skipped, and the native-Linux build is refused with exit 4 and the Windows-build steps
- [ ] #5 Headless runs print the same numbered plain-text progress as the Python TextProgress; GUI dialogs are out of scope here (TASK-006.04.01.02)
- [ ] #6 Third-party Go dependencies are limited to what is justified in writing: bitfield/script only where pipeline sugar beats stdlib, with the final dependency list recorded in the task
- [ ] #7 Parity tests run the Go binary and the Python installer against identical fixtures and compare stdout, the install record, and exit codes; Python remains the reference until the Go binary reproduces the live host checks, and no docs advertise Go as the default before then
- [ ] #8 docs/player-installer.md gains the Go section (build targets, contract inheritance) and taskfiles produce the binary alongside the zip
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 task check passes
- [ ] #6 Tests written first for ported logic
- [ ] #7 Docs updated
- [ ] #8 Conventional commit with no attribution
<!-- DOD:END -->
