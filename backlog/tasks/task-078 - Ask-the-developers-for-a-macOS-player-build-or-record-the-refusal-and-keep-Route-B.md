---
id: TASK-078
title: >-
  Ask the developers for a macOS player build, or record the refusal and keep
  Route B
status: Done
assignee: []
created_date: '2026-11-15 23:53'
updated_date: '2026-11-16 00:24'
labels: []
dependencies: []
references:
  - docs/development.md
modified_files:
  - docs/development.md
priority: low
ordinal: 251000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The cheapest thing that deletes the largest Route B blocker: the developers already ship Linux and Windows player builds, so a macOS build is a build-pipeline change and not a port. With one, the shader translation pass becomes unnecessary because the game ships its own Metal shaders, and the macOS-native artifact stops depending on a locally rebuilt probe player.

This is an external request, so the task is to make it and record the answer either way. The docs already carry it as standing blocker 2; this makes it trackable and gives the refusal a place to live so the route notes do not keep re-asking.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A concrete request reaches the developers with the measured evidence already gathered
- [ ] #2 The response is recorded in docs/development.md whether it is yes, no or silence
- [ ] #3 If the answer is yes the Route B notes say which blockers the build removes
- [ ] #4 If the answer is no the notes name what replaces this ask rather than leaving it open
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Closed: there is no upstream to ask

The request was never made, because the premise for making it turned out to be false. Steam's news API for appid 3405340 returns no developer announcement after **v1.0.64, published 2026-01-25** — 294 days of silence as of 2026-11-16 — and the maintainer reports no work on the game since then. A macOS player build is not coming, so this is not a pending ask with an unknown answer; it is a closed question.

## What this replaces it with

- The locally rebuilt Unity 2023.2.22f1 probe player is a **permanent** fixture of the macOS legs, not a stopgap until upstream helps. Documented as such in docs/development.md.
- An arm64-native artifact can only come from this project. Route C's build-for-macOS path and Route A's (needs a fork of the archived McSema) are the only candidates, which is now recorded as the open question instead of an upstream dependency.
- The stale upkeep figures that this ask was ranked against are corrected in "Cost per game update": the 15-depot-pushes-a-month rate predates the freeze and no longer applies, the Unity-version-bump cliff is gone, and Route C's per-patch re-port cost that made it untenable is a one-time cost now.

## Acceptance criteria outcome

None of the four criteria were met as written, and none can be: they assumed an addressable maintainer. The intent behind them — the route notes must stop re-asking, and the answer must be recorded either way — is satisfied by this summary and the docs change. No request was sent, so no reply exists to record.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
<!-- DOD:END -->
