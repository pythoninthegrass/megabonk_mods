---
id: TASK-084.01
title: Boot a native VitaSDK test VPK on the PCH-2000
status: Done
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T09:06:00Z'
labels:
  - ps-vita
  - vita-spike
dependencies: []
documentation:
  - .agents/skills/vita-port/references/toolchain.md
  - .agents/skills/vita-port/references/runtime.md
  - docs/vita-smoke.md
modified_files:
  - taskfile.yml
  - taskfiles/vita.yml
  - docs/vita-smoke.md
  - tests/test_vita_smoke.py
  - vita/smoke/CMakeLists.txt
  - vita/smoke/livearea.xml
  - vita/smoke/main.c
  - vita/smoke/metrics.h
  - vita/smoke/test_metrics.c
parent_task_id: TASK-084
type: task
ordinal: 286000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish a repeatable hardware bring-up and measurement baseline independent of Unity and the macOS lift.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reproducibly built, validated VPK installs and boots on a physical PCH-2000 at stock clocks with no required plugins.
- [x] #2 Both physical sticks are observed in-app; frame timing and peak MAIN/CDRAM use are recorded.
- [x] #3 Build, deploy and validation steps name hardware, firmware, clocks and toolchain.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify local ignore rules, record the console connection and safe install notes in the local-only fleet file, and inventory the existing VitaSDK and device access without changing the console.
2. Build a standalone native smoke VPK without game assets, Unity, clock overrides, or required plugins. Test the host-testable stick and metrics logic before implementation. Pin the toolchain and add reproducible build and package-validation commands.
3. Install and launch on the physical PCH-2000. Confirm firmware and stock clocks, exercise both physical sticks, and capture frame timings and peak MAIN/CDRAM usage with explicit measurement conditions. Document the procedure and evidence without exposing private machine or network details.

Add a labeled LiveArea template using the same layout as the development SSH app. Verify the template and packaged metadata, then reinstall the smoke app through the updated VitaSSHd third-party installer.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Recorded console access and the safe USB install fallback in globally ignored local notes. Verified VitaSDK 2026.08, arm-vita-eabi GCC 15.2.0, and the VPK packaging tools on the build host. The console SSH port answered; no firmware, clocks, VPK behavior, input, or performance have been verified yet.

Built the standalone smoke VPK with VitaSDK 2026.08/GCC 15.2.0. The validator reported zero errors and warnings; two build directories produced byte-identical payloads for all six package entries (ZIP timestamps differ). The host metrics test went red before implementation and passed after it; task check passed. The installed development SSH updater only accepts its own title, SSH did not establish a staging session, and no Vita USB volume was mounted. Next: install in VitaShell, exercise both physical sticks at stock clocks, and collect the report. No on-device acceptance criteria are claimed.

Staged the validated VPK under the console downloads directory via SFTP. The live VitaSSHd could list all six entries, but its vpk install command explicitly rejected the smoke title ID because it only accepts the server title. The staged package is ready for VitaShell installation.

The maintainer reports that the smoke app booted on the physical Vita after VitaSSHd was refactored to support third-party VPKs, and that both physical sticks exercised their respective four-quadrant displays. The hardware telemetry report was not present at the expected path when queried; firmware, clocks, timing, and memory remain unverified.

Retrieved the physical PCH-2000 report on firmware 3.74: both sticks passed, 253 vblank-paced intervals measured 16.635/16.683/16.729 ms min/mean/max, and sampled additional MAIN/CDRAM use was 0 bytes/4 MiB after the initial in-process baseline (1 MiB newlib separately reserved). Observed ARM/bus/GPU/crossbar clocks were 333/222/41/111 MHz. The report does not establish whether any external clock overrides were disabled; stock-clock verification stays open.

Read the console's taiHEN configuration without modifying it. PSVshell is configured under *KERNEL, but its profile directory contains neither the upstream global fallback profile nor a profile for the smoke app. No saved PSVshell override for the app was found; a plugin-free boot or live default-mode check has not been performed.

Pulled the second physical report: 1,435 vblank intervals, 16.611/16.683/16.756 ms min/mean/max, both sticks passed, and memory readings matched the first report. The maintainer confirmed all four clock readings were white (Default) in PSVshell, matching the report, so the live check found no PSVshell clock override. The run included an overlay check; a boot with optional plugins disabled has not been observed.

Added the smoke app title and subtitle to a psmobile LiveArea template. Bumped the package to 01.01, validated its metadata, and installed it over the prior copy via VitaSSHd's third-party reinstall command. Read back the installed LiveArea XML and verified byte equality with the source. Physical rendering of the label has not been observed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Add a standalone VitaSDK smoke VPK and a repeatable build, install, and measurement procedure. Two builds of the final package produced identical entry contents, and package validation passed. The physical PCH-2000 (firmware 3.74) booted the smoke app at default clocks, both sticks passed, and 1,435 frame intervals averaged 16.683 ms. Sampled additional MAIN/CDRAM use was 0 bytes/4 MiB after the in-process baseline, with a separate 1 MiB newlib reservation. The app imports no plugin APIs; VitaSSHd and PSVshell were used only for installation and inspection. The labeled package was reinstalled and its LiveArea XML verified by readback. The host tests were written first and task check passed on the isolated release baseline.
<!-- SECTION:FINAL_SUMMARY:END -->
