---
id: TASK-026
title: Launch and control the Wine game from SSH on macOS
status: Done
assignee: []
created_date: '2026-10-30T21:11:00Z'
updated_date: '2026-10-30T23:12:00Z'
labels: []
dependencies: []
type: bug
ordinal: 127000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Launching from the logged-in desktop succeeds while the same task from SSH exits before graphics initialization. Captured exit stack and UnityPlayer disassembly identify Failed to create window; winemac.drv loads and unloads without initializing. Wine refuses sessions without macOS graphical access. Remote development needs the existing game:editor and harness commands to work from SSH without manual desktop-terminal launches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Plain-Wine game and Steam launches from a non-graphical macOS session run in the logged-in GUI session without sudo or a debugger.
- [x] #2 Desktop launches preserve their existing behavior and launch environment; unrelated SSH credentials are not persisted.
- [x] #3 Missing GUI sessions and failed handoffs report actionable errors without silently launching headless or killing an existing game.
- [x] #4 Tests cover session detection, GUI handoff, environment forwarding, stale jobs and handoff failures; documentation describes SSH use and prerequisites.
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
Detect macOS graphical access via Security.SessionGetInfo rather than SSH environment flags. Preserve the existing direct spawn when graphical access is available. For non-graphical callers, build a private, explicitly bootstrapped RunAtLoad LaunchAgent in gui/<uid> using the resolved watcher/Steam argv, cwd and an allowlisted runtime environment; do not install login autostart or pass shell credentials. Reuse a prefix/target-scoped label only after checking the prior service has no running PID; refuse rather than terminate a live launch. Report missing GUI domains and launchctl errors clearly. Write tests before implementation, then verify a harmless session probe through launchd (no game loop), document SSH commands and correct the prior native-crash claims. Full tests and lint before commit; leave end-to-end SSH game verification to the user if no SSH execution context is available.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented automatic Security.SessionGetInfo detection and one-shot gui/<uid> LaunchAgent bootstrap for plain-Wine game and Steam in scripts/launch_game.py. Private plist, allowlisted runtime environment, prefix/target label, flock, live/pending-job refusal, stopped-job reuse, actionable launchctl errors. Tests written first (13 expected failures), now 653 Python tests pass; task lint and git diff --check pass. Live harmless LaunchAgent probe twice reported graphical_access=True, preserving watcher output and proving stale-job reuse; removed its test service afterward. No game launched, no mod rebuild/deployment. Corrected docs and diagnostic docstring that had asserted an unsupported native-crash explanation.

Awaiting user end-to-end verification with ordinary task game:editor from SSH. Attempt to test SSH via localhost was blocked by an existing changed-host-key warning; did not bypass verification or alter known_hosts. Full task check not run because it rebuilds/deploys the mod into the shared game installation while another worktree may be using it. Changes are not yet committed pending SSH runtime verification.

User confirmed ordinary task game:editor now works over SSH. Subsequent music/manual-grind concern was traced to the pre-existing in-editor edits-only loader and a stale installed level copy, not the SSH fix; launching levels/thps.mblevel.json directly restored both and user confirmed. That separate loader issue was not changed.

Final task check passed: mod build/deployment, 1,441 C# tests, 653 Python tests, markdownlint and ruff. Existing C# nullable warnings and pytest asyncio deprecation warnings remain non-fatal. Commit 23db694 contains the implementation, tests and docs. Game SSH runtime verified by user; Steam handoff covered by tests, not a live Steam login.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Plain-Wine launches now detect macOS graphical-session access and automatically bootstrap a private one-shot GUI LaunchAgent for SSH callers. Desktop spawning is unchanged. Resolved argv, cwd and allowlisted runtime environment are preserved without copying unrelated SSH credentials. Running/pending jobs are refused, stopped jobs can be reused, and missing GUI sessions/bootstrap errors are actionable. Documented prerequisites and corrected unsupported native-crash claims. Verified with a live harmless GUI probe, user-confirmed SSH game launch, 1,441 C# tests, 653 Python tests and full task check. The existing in-editor metadata-loading issue is separate and unchanged.
<!-- SECTION:FINAL_SUMMARY:END -->
