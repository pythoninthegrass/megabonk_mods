---
id: TASK-006.04.01.02
title: Add a MyGo native-UI progress window to the Go installer
status: To Do
assignee: []
created_date: '2026-10-31T08:14:00Z'
labels:
  - tooling
dependencies:
  - TASK-006.04.01.01
references:
  - 'https://github.com/egoist/mygo'
  - docs/player-installer.md
documentation:
  - docs/player-installer.md
modified_files:
  - go/
  - docs/player-installer.md
parent_task_id: TASK-006.04.01
priority: low
type: feature
ordinal: 129000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Go installer (TASK-006.04.01.01) ships with headless text progress; the Python installer's desktop story is a kdialog driven over D-Bus, which needs KDE's kdialog and qdbus present. On top of the Go binary, add a proper progress window using MyGo (egoist/mygo) in native-UI mode - not the webview mode: webview on Linux dlopens WebKitGTK 4.1, a heavyweight dependency most players lack, while native UI needs only GTK 3, which the target KDE desktops already carry. The window shows label, percentage, and a working cancel (cancel must abort between steps and roll back cleanly through the same uninstall path, not kill mid-copy); when MyGo's UI cannot start (no display, missing GTK, ssh), the installer falls back unchanged to kdialog-over-D-Bus and then to text, so nothing ever depends on GTK being installed. MyGo builds multi-platform from one Go module (mygo build -platform ...), needs Go 1.27+, and can emit the .deb/desktop-entry packaging - evaluate but do not couple this task to packaging changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 MyGo native-UI (not webview) progress window: title, step label, percentage bar, and a cancel button wired to a clean between-steps abort
- [ ] #2 On the AlmaLinux host's KDE session the window appears with only GTK 3 present - no WebKitGTK is loaded (verified against the webview-mode alternative) - and the rest of the binary stays static
- [ ] #3 Without a display, without GTK, or with UI disabled, the installer behaves exactly as the headless Go binary: kdialog-over-D-Bus when its prerequisites exist, plain text otherwise
- [ ] #4 The same lifecycle scenarios that the headless Go binary passes produce identical results through the GUI path, and cancelling mid-install leaves the game dir restore via the recorded uninstall
- [ ] #5 docs/player-installer.md records the UI selection order (MyGo window, kdialog, text) and the GTK-only requirement
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
