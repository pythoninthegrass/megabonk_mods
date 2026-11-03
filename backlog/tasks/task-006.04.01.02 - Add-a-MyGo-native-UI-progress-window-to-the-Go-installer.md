---
id: TASK-006.04.01.02
title: Add a MyGo native-UI progress window to the Go installer
status: In Progress
assignee: []
created_date: '2026-10-31T08:14:00Z'
updated_date: '2026-11-03 21:26'
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
The Go installer (TASK-006.04.01.01) ships with headless text progress. Add a proper progress window on top of the Go binary using MyGo (egoist/mygo) in native-UI mode - not the webview mode: webview on Linux dlopens WebKitGTK 4.1, a heavyweight dependency most players lack, while native UI needs only GTK 3, which the target desktops already carry. The window shows label, percentage, and a working cancel (cancel must abort between steps and roll back cleanly through the same uninstall path, not kill mid-copy); when MyGo's UI cannot start (no display, missing GTK, ssh), the installer falls back unchanged to the headless text reporter, so nothing ever depends on GTK being installed. DE-specific dialog tools (kdialog-over-D-Bus, zenity, yad) are not part of the Go chain: the MyGo native window is the only GUI path, drawn with GTK 3 on Linux, Metal on macOS, and Direct3D 11 on Windows. MyGo builds multi-platform from one Go module (mygo build -platform ...), needs Go 1.27+, and can emit the .deb/desktop-entry packaging - evaluate but do not couple this task to packaging changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MyGo native-UI (not webview) progress window: title, step label, percentage bar, and a cancel button wired to a clean between-steps abort
- [x] #2 On the AlmaLinux host's KDE session the window appears with only GTK 3 present - no WebKitGTK is loaded (verified against the webview-mode alternative) - and the rest of the binary stays static
- [x] #3 Without a display, without GTK, or with UI disabled, the installer behaves exactly as the headless Go binary: plain text, same lines and exit codes; no DE-specific dialog tool (kdialog, zenity, yad) is used in the Go chain
- [x] #4 The same lifecycle scenarios that the headless Go binary passes produce identical results through the GUI path, and cancelling mid-install leaves the game dir restore via the recorded uninstall
- [x] #5 docs/player-installer.md records the UI selection order (MyGo window, text) and the GTK-only requirement
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [x] #5 task check passes
- [x] #6 Tests written first for ported logic
- [x] #7 Docs updated
- [ ] #8 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

1. go.mod: go 1.24 -> 1.27 (matches .tool-versions golang 1.27.0; MyGo needs 1.27+); add github.com/egoist/mygo as the first external dependency.
2. taskfiles/installer.yml verify-static: keep CGO_ENABLED=0 + static-link checks; relax the "go list -m all == 1" module-count check to allow the mygo module and its transitive deps (the real guarantees - static, cgo-free, no runtime deps - stay checked).
3. go/internal/window (new): MyGo native-UI progress window (title, step label, ui.Progress bar, Cancel button). mygo.App.Run must own the main goroutine, so the window driver runs work on a worker goroutine and pumps events on the caller; the whole GUI attempt returns "started=false" when the app cannot launch (no display, missing GTK, ssh), leaving the caller to run the unchanged headless path. Every mygo call is goroutine-safe; window updates go through Window.Update.
4. go/internal/ui: keep Progress as-is; add Cancellable (Cancelled() bool) implemented only by the window progress. Selection order: MyGo window -> plain text. Gates unchanged (NoGUI/NonInteractive/AsJSON/HasDisplay/HasTTY + --no-ui). DialogSkipNote reworded from the zenity/yad/kdialog advice to the window's real requirement (display + GTK 3). No kdialog/zenity/yad backends are ported to Go (maintainer decision: native windows over DE-specific abstractions); the Python reference keeps its dialog story.
5. go/internal/plan ApplyPlan: poll Cancellable between actions; on cancel write a partial install record of completed actions, run the existing record-driven Uninstall, report cancelled+rolled-back. Uninstall: cancel stops between steps (no rollback of a partial uninstall).
6. go/internal/cli: run install/uninstall through the driver seam (seam injectable for tests, like PickProgress).
7. Tests first: ui.NewTester-based view tests (label/percentage/cancel), selection-order table tests, plan cancel->partial-record->rollback restoring the fixture tree, parity untouched (headless never opens a window; add DISPLAY-set/no-GTK fallback case).
8. Verification: mf KDE session (AC #2: window on GTK3 only, no WebKitGTK in process maps, verify-static green), then live runs on fedora (GNOME Wayland), mbp (macOS), and the Windows container (this round's targets).
9. docs/player-installer.md: UI selection order, GTK-3-only requirement, cancel/rollback semantics, mygo build/-platform packaging evaluated-but-not-adopted note.

## Risks
- mygo App.Run error path on missing GTK must be prompt so fallback output stays identical to headless.
- Cross-compile: mygo is cgo-free, so plain go build keeps working for darwin/arm64, linux/amd64, windows/amd64.
- Windows container GUI needs the interactive desktop session (noVNC), not SSH.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Live runs 2026-11-03 (fake Windows-build game dir, Linux player package, window path via a pty): mf (KDE/Xwayland) and fedora (GNOME Wayland): LD_DEBUG=libs shows libgtk-3 and libgdk-3 initialised, zero webkit references even though libwebkit2gtk-4.1 is installed on mf; install completed, exit 0, no per-step text lines (window path). verify-static green for darwin/arm64, linux/amd64, windows/amd64. mini (macOS arm64): window path, install completed. Windows container (SSH session, not the interactive desktop): window path ran with mygo software drawing, exit 0.

Not yet verified: a visible window and a real Cancel click on any host (the install finishes in under a second, so nothing was screenshotted); cancel->rollback is covered by plan/cancel_test.go only. Windows container interactive-desktop run via noVNC still open.

Observations: (1) mygo writes 'drawing without the GPU: d3d11 ... 0x887a0022' lines to stderr on Windows, so stderr is not identical to headless there. (2) The window is gated on HasTTY, so a double-click launch with no controlling terminal gets text only; decide whether that gate should stay for the GUI path. (3) Windows container SSH is reachable on the LAN address, not localhost, from mf.

Gate change (maintainer direction): the HasTTY gate is removed (tty_unix.go/tty_windows.go deleted). The window now opens on a confirm prompt ('Install Megabonk Levels?' / 'Uninstall ...') with Yes and Cancel; nothing is touched until Yes. Declining or closing exits 1 with 'cancelled - nothing was changed'. Opt-out is --no-gui, --non-interactive, MEGABONK_NON_INTERACTIVE=1, --json, or no display. ui.Confirmer interface; window.Progress.Confirm; tests written first in window_test.go, cli_test.go, ui_test.go.

Live over noVNC on the Windows container (interactive desktop session, launched through a scheduled task): the window is visible with the prompt; Yes click installed (6 steps, Mods dll present, exit 0); Cancel click at the prompt left no Mods/MelonLoader, printed 'nothing was changed', exit 1. Still unverified live: a Cancel click after Yes mid-run (install finishes too fast to click; covered by plan/cancel_test.go) and the Linux/macOS prompts (no click automation on mf/fedora/mini).

mf live check (2026-11-03): headless sway (WLR_BACKENDS=headless, from the neo_snake parity setup: sway, wtype, grim in /usr/local/bin) on wayland-1 with DISPLAY unset. Real GTK 3 window rendered via mygo with title, bold heading and the prompt, Yes and Cancel buttons; screenshot read back. The headless seat has no pointer (swaymsg cursor press does nothing), so input is a long-lived `wtype -s` virtual keyboard: Tab focuses Yes, Tab Tab focuses Cancel, Return activates. Yes: install completed, exit 0. Tab Tab Return: 'cancelled - nothing was changed', exit 1, game dir untouched. --uninstall + Tab Return: removed 9 items, game dir back to its original tree, exit 0. A one-shot wtype before the long-lived keyboard exists loses the race and does nothing.

mini: the osascript MCP in .mcp.json runs on mf through uvx, where there is no osascript binary, so every call fails ('No such file or directory: <path>'). Over ssh the installer window opened on the mini (process listed as a foreground app, blocked at the prompt) but screencapture ('could not create image from display') and System Events keystrokes ('osascript is not allowed assistive access') are denied for ssh/Terminal-launched processes, so the macOS prompt is not yet seen or clicked.

mini live check (macOS arm64, after Screen Recording was granted to Terminal): the installer is launched through a .command file via `open` so it lands in the GUI session, screenshots by screencapture from a .command, keystrokes by System Events `key code` (48 Tab, 36 Return) from a .command after setting the installer process frontmost. The Metal-drawn window renders with title, heading, prompt, Yes and Cancel (screenshot read back; Tab shows the focus ring on Yes). Yes: install completed, exit 0, Mods dll present. Tab Tab Return: 'cancelled - nothing was changed', exit 1, game dir untouched. --uninstall + Tab Return: removed 9 items, tree restored, exit 0. Linux (mf, GTK 3), macOS (Metal) and Windows (D3D11) now each have a rendered window with Yes/Cancel/uninstall confirmed live; the only unclicked path is a Cancel after Yes mid-run (covered by plan/cancel_test.go).

Mid-run cancel verified live on mf (headless sway, MEGABONK_UI_STEP_DELAY=2s added as a documented test hook, test written first): running window shows 'install MegabonkLevels dev ...', '3/6 NLayer.dll -> ...', a 50% bar and Cancel; Tab Return on Cancel printed 'install cancelled - files already placed were rolled back', exit 1, and the game tree diffed identical to the pre-install tree.
<!-- SECTION:NOTES:END -->
