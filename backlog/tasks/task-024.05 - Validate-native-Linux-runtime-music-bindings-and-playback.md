---
id: TASK-024.05
title: Validate runtime music playback on Linux through Windows Proton on fedora
status: Done
assignee: []
created_date: '2026-10-30T02:25:00Z'
updated_date: '2026-11-03 03:13'
labels:
  - music
  - linux
dependencies:
  - TASK-024.04
documentation:
  - docs/music.md
  - docs/development.md
  - docs/gamepadui.md
parent_task_id: TASK-024
ordinal: 124000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate the existing Win64 runtime music path on Linux using the Windows build under Proton on SSH host mf. Lance explicitly chose Windows/Proton for every Linux machine; no Linux box should run the native Linux build. This supersedes the former native-Linux ABI inspection and playback requirement. Do not install or switch to the native Linux depot, remove the native-Linux platform guard, or claim native Linux support. Use docs/gamepadui.md for remote Steam/Proton setup and verify the installed Windows depot and active Proton runtime before testing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Confirm mf is running the Windows build under Proton (Windows depot 3405342 and active prefix/runtime evidence), not the native Linux build.
- [x] #2 A runtime mp3 is audibly confirmed on mf through the normal MusicTrack path under Proton; human listening confirmation is recorded separately from automated source-state checks.
- [x] #3 Stage playback, boombox transitions, wrap, replay and missing/unreadable/undecodable fallback work under Proton on mf without invalid clip lifetime.
- [x] #4 Native Linux remains unsupported and guarded; documentation and the parent task reflect Windows/Proton as the Linux-host target, with any access or verification blockers explicitly recorded.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Platform decision from Lance (2026-11-01): mf is the Linux host; all Linux machines must use the Windows build under Proton, never the native Linux build. Replaced obsolete native-Linux ABI/playback acceptance criteria with Proton validation. No playback verification performed or acceptance criteria completed by this update. Parent TASK-024 still contains superseded native-Linux wording and must be reconciled as part of this task.

Verification run on fedora (2026-11-02): Fedora Linux, Proton Experimental, Megabonk 1.0.69 (build 21750826), MelonLoader 0.7.3, mod HEAD 745ccd7. Lance's platform decision (2026-11-01): all Linux machines use Windows build under Proton, never the native Linux build. Target retitled from mf to fedora to reflect the actual host used.

AC#1 — Windows under Proton confirmed: appmanifest depot 3405342 (Windows), process `Megabonk.exe -force-d3d11`, STEAM_COMPAT_DATA_PATH active prefix, Player.log `Forcing GfxDevice: Direct3D 11` / Intel Arc MTL, dxgi/d3d11 mapped in /proc/maps.

AC#2 — Audible confirmation from Lance: "In the editor. Strobe is playing" and "It's been working for the last dozen or so builds." Automated: `track:14 strobe` (lowercase) → `Music: using runtime track '14 Strobe' (635.872s).`, `Music: handed '14 Strobe' to the music source, isPlaying=True.`, sourceTime advancing in frozen editor.

AC#3 — Four automated groups passed (evidence in /tmp/opencode/t024-fedora/EVIDENCE.md and groupA-D-Latest.log): A: stage selection + boombox wrap + pause/pitch/lowpass/duck + replay-after-takeover; B: four 4s fixtures, five natural endings 5.0s apart, dotted numeric order 00.01→00.02→00.10→ZZ→wrap; C: missing/chmod-000/corrupt each warned and fell back to stock Forest1_Loop with levelLoaded true; D: bundle thps 04_Superman + boombox 05_Jerry→06_01→06_02 + replay after native-tone takeover.

AC#4 — Native Linux remains unsupported and guarded; docs/music.md updated (Linux under Proton added as verified, native guard note updated); docs/gamepadui.md has new "Dev harness on a plain Fedora Steam host" section. Parent TASK-024 reconciled.

New gotchas recorded: offline launch needs SteamAppId/SteamGameId; stale harness queue survives launcher restart (clear manually); Photosensitivity Warning appears every launch (drive KEY_ENTER); interact defaults to nearest, not named — use --type Boombox --force; mise exec -- task mis-resolves lowercase taskfile.yml; menu batch JSON needs a helper script through two SSH shells.

Also fixed: thps_level_tests.cs and thps_editable_level_tests.cs hardcoded "Taskfile.yml" (capital T) instead of "taskfile.yml", causing 11 C# test failures on case-sensitive Linux filesystems.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed Proton validation of TASK-024 runtime music on fedora (Fedora Linux, Proton Experimental, Windows depot 3405342, D3D11, MelonLoader 0.7.3, mod HEAD 745ccd7). Lance's platform decision — all Linux machines run Windows under Proton, never the native build — is reflected throughout.

Four automated verification groups passed: stage selection with case-insensitive track:, boombox wrap, all runtime controls (pause/pitch/lowpass/duck), replay after external takeover, natural-ending ordering, all three fallback paths, and bundle regression. Lance confirmed audible playback: "In the editor. Strobe is playing" / "It's been working for the last dozen or so builds."

docs/music.md updated: native-binding platform note now covers Proton on Linux, production-integration paragraph records the fedora Proton run and Lance's verbatim confirmation. docs/gamepadui.md has a new "Dev harness on a plain Fedora Steam host" section with the four new gotchas. Parent TASK-024 reconciled: AC#7 wording updated to reflect Proton-on-Linux as the Linux verification path and all criteria closed.

Side fix: thps_level_tests.cs / thps_editable_level_tests.cs used "Taskfile.yml" (capital T), failing on case-sensitive Linux; corrected to "taskfile.yml".
<!-- SECTION:FINAL_SUMMARY:END -->
