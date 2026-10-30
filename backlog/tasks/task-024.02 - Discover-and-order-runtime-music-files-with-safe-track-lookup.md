---
id: TASK-024.02
title: Discover and order runtime music files with safe track lookup
status: Done
assignee:
  - Assistant
created_date: '2026-10-30T02:24:00Z'
updated_date: '2026-10-30T02:30:00Z'
labels:
  - music
dependencies: []
documentation:
  - docs/music.md
parent_task_id: TASK-024
ordinal: 121000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Runtime music needs a deterministic cross-platform catalog without Unity or a pack build. Use the global UserData/CustomMusic folder; tools/ost is source material only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Top-level mp3 discovery is case-insensitive by extension and handles an absent or unreadable folder without throwing.
- [x] #2 Leading integer components sort numerically, including dotted prefixes; unprefixed files sort last with deterministic ties.
- [x] #3 Track lookup preserves spaces and dots, is case-insensitive, and cannot resolve outside discovered files; case-colliding names are handled deterministically.
- [x] #4 Runtime playlists preserve supplied order, continue after the current track and wrap; existing pack playlist sorting is unchanged.
- [x] #5 Tests are written first and docs/music.md describes catalog and ordering rules.
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
1. Add failing xUnit tests for ASCII integer-component filename ordering (arbitrarily large components, leading zeros, shorter prefixes first, ordinal ties, unprefixed last), top-level case-insensitive mp3 discovery, case-insensitive lookup, ambiguous case collisions and traversal rejection. Cover absent folders and IO failure warnings.
2. Implement pure TrackFileName comparer and CustomMusicLibrary snapshot. Resolve only catalog entries; exclude symlink files and ambiguous case-insensitive names with warnings. Do not decode or hook game startup yet; integration is TASK-024.04.
3. Add explicit preserve-order RadioPlaylist factory while retaining existing constructor sorting and equality. Tests cover StartAfter and wrap.
4. Document exact ordering/catalog rules and note production playback is not integrated yet. Run focused tests then task check and commit this subtask separately.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Test-first red: task mod:test failed for absent TrackFileName, CustomMusicLibrary and PreserveOrder APIs before implementation. Green: task check passes (mod builds/deploys, 1,324 xUnit tests, 513 Python tests, markdownlint and ruff). Catalog tests exercise permission-denied folder, missing folder, file-as-folder, nested/non-mp3 exclusion, symlinks, case-insensitive lookup, path traversal, overflow-sized numeric components and dotted ordering. Case collisions are tested on candidate snapshots in both enumeration orders so coverage does not depend on filesystem case sensitivity. Startup/Prepare integration and actual audio remain deliberately deferred to 024.04; no parent playback criteria checked.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented a pure runtime music catalog with numeric dotted-prefix ordering, case-insensitive safe lookup, deterministic ambiguous-name rejection, top-level mp3 filtering and guarded filesystem discovery. Added an explicit preserve-order playlist factory without changing pack ordering, plus documentation and test-first coverage. task check passes: 1,324 xUnit and 513 Python tests, build/deploy and lint. Commit 8486699. Playback/startup integration remains for 024.04; no in-game audio behavior changed.
<!-- SECTION:FINAL_SUMMARY:END -->
