---
id: TASK-086.03.10
title: Stand up a Killing Floor 1 oracle on the Windows GPU guest
status: To Do
assignee: []
created_date: '2026-11-28T06:34:00Z'
labels:
  - level
  - kf1
dependencies: []
references:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086.03
priority: high
type: spike
ordinal: 315000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Fidelity work on the Mountain Pass port has no ground truth for how KF1 renders; reference frames come from the KF2 footage. Run the original KF1 on real Windows with a real GPU and capture screenshots at fixed poses to compare against the port. Use the GPU-passthrough Windows 11 guest, not Wine: gamma, fog and alpha-test behavior are what the port keeps getting wrong, and a translation layer would add its own differences. Findings so far: KF1 is not installed in the CrossOver Steam bottle on the second Mac or in the plain-Wine prefix on the authoring Mac; the Linux box that exports assets has the copied game files (Textures, Maps, StaticMeshes, System) but no Architecture_T or Architecture_T2 package; the guest was not readable because SSH from the authoring Mac fails host-key verification (copy the already-verified known_hosts line from a box that trusts it instead of accepting the key blindly). Steam allows one game session per account, so installing through Steam can disconnect another box; copying the files from the asset box avoids a login, if KF1 launches with Steam offline (unconfirmed). Camera placement and screenshots would use the UE2 console (ghost, shot) but the accepted commands are unverified; Looking Glass is the fallback. First step, no oracle needed: read the map package's import table to name the package files that supply Architecture_T.Rooftops.concreteroof and Architecture_T2.Plaster.Stucco_1480_colored (674 brush faces still untextured).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The map package import table names the package files that supply the Architecture_T and Architecture_T2 textures, recorded in docs/kf1-mountain-pass.md
- [ ] #2 The authoring Mac can SSH to the Windows GPU guest without accepting an unverified host key
- [ ] #3 KF1 launches on the guest and loads KF-MountainPass, with the install route (Steam or copied files) and any Steam-offline requirement recorded
- [ ] #4 A documented, repeatable way places the camera at a given pose and saves a screenshot, or Looking Glass is recorded as the fallback with the reason
- [ ] #5 At least six reference poses (spawn, a road, a building exterior, a building interior, a trader pod, the lake) are captured and stored under the gitignored .tools tree with their coordinates
- [ ] #6 The reference poses are compared with the port at the same poses and the differences are logged on the open fidelity tasks
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
