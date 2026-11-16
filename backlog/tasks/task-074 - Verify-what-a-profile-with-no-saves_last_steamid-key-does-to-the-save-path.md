---
id: TASK-074
title: Verify what a profile with no saves_last_steamid key does to the save path
status: Done
assignee: []
created_date: '2026-11-15 20:12'
updated_date: '2026-11-15 20:43'
labels:
  - mod
  - offline
dependencies: []
references:
  - docs/development.md
modified_files:
  - docs/development.md
priority: medium
ordinal: 72700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The game resolves its own save folder as persistentDataPath/Saves/CloudDir/<steamId>/, and with the original shim and Steam unable to start it still resolves the real account id, which can only come from the PlayerPrefs key saves_last_steamid (on Windows the Software/<Company>/<Product> registry key of the profile). The branch that has never been observed is the one with no such key: a profile that has never had Steam. Current inference, from the game logging Rewired save path set to: .../Saves/CloudDir/69/ before resolving the real id, is that it falls back to 69 and therefore starts a fresh progression. That inference is load-bearing for the offline multi-machine plan and for onboarding a new machine, so it needs to be observed rather than assumed.

Work: with byte-exact backups of the bottle's user.reg and the whole LocalLow/Ved/Megabonk tree, and with wineserver stopped so the registry edit actually takes, remove the Software/<Company>/<Product> hive and move the Saves tree aside, launch, and record the Rewired save path lines, which CloudDir directories appear, and whether the game writes a fresh saves_last_steamid. Then restore both by hash-verified copy and delete anything the run created.

Safety is the point of this task, not a footnote: a botched restore destroys a real save. Back up before touching anything, hash before and after, restore in a trap so a failed run still restores, and do not run against a live Steam client (use the stub so there is no cloud sync to fight with).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The run observes the no-key branch directly: the hive and the Saves tree are absent at launch, not merely assumed absent
- [x] #2 The log records which Rewired save path the game picks and which CloudDir directories exist afterwards, so the 69 fallback is observed rather than inferred
- [x] #3 Whether a fresh saves_last_steamid is written, and with what value, is recorded
- [x] #4 Both the registry hive and the Saves tree are restored byte-identically, verified by hash, with run-created directories removed and no probe process left running
- [x] #5 docs/development.md states the observed behaviour for a profile with no saves_last_steamid key, replacing the inference
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Observed directly, with the hive and the Saves tree genuinely absent at launch (wineserver stopped first, so the registry edit took).

No-key run: Rewired resolved CloudDir\69\ then CloudDir\0\. No CloudDir directory was created, no saves were written, and no fresh saves_last_steamid appeared in user.reg.

Control run, everything else identical with the hive left in place: CloudDir\69\ then CloudDir\<the real 64-bit account id>\. That also ran against the stub, whose SteamAPI_ISteamUser_GetSteamID returns 0, so the id in the second path cannot come from the client: it comes from the registry key.

Verdict on the inference the task was written to test: 69 is not the no-key fallback, it is simply the first of the two Rewired paths in either configuration. The offline plan loses the assumption that a fresh profile starts a clean new save; what is established is that without the key the game never resolves an account folder at all. Whether a completed run starts a fresh progression under a new folder stays unobserved, because neither run wrote save files (boot, one level load, one kill).

Restore verified by hash: user.reg and userdef.reg byte-identical to the pre-run copies, 8/8 save files matching the manifest against both the moved-aside original and the backup copy, no run-created directories left, no game or wineserver process. One defect in the probe itself surfaced and was repaired: its restore used copytree against a directory that still existed and nested the tree instead of replacing it; the pristine sources were compared first, the run-created tree removed, and the original restored and re-verified. The parked Player.log copy from an earlier task went only after its content was checked against the backup.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
