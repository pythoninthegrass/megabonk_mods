---
id: TASK-024.01
title: 'Spike: prove a custom mp3 can be decoded and heard in the running game'
status: Done
assignee:
  - agent
created_date: '2026-10-30T00:06:00Z'
updated_date: '2026-11-09 05:26'
labels:
  - music
  - spike
dependencies: []
references:
  - TASK-024
documentation:
  - docs/music.md
  - docs/development.md
parent_task_id: TASK-024
priority: low
ordinal: 120000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Prove that a player-supplied mp3 can be decoded and heard in the running game without Unity authoring or a pack build, and record the output-path decision for TASK-024. This is a diagnostic spike, not folder discovery, level-reference integration or a runtime boombox playlist.

The ordinary managed AudioClip.Create/SetData wrappers fail on stripped Il2Cpp span helpers, and an initial direct native attempt crashed. Investigation therefore tested OnAudioFilterRead first, then corrected native AudioClip bindings. Native clip creation is now proven on the Win64 player under Wine on macOS; native Linux playback remains unverified with the blocker recorded below.

Outcome: NLayer PCM -> real AudioClip -> existing MusicTrack/PlayMusicTrack is the preferred path. The existing bundle music and boombox implementation are unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A pure-managed mp3 decoder decodes the tools/ost mp3s inside the running game and logs sample rate, channel count, sample count and duration for a track
- [x] #2 One output path plays a track audibly in the running game on the Wine/CrossOver macOS setup, confirmed by the maintainer hearing it rather than by log lines alone
- [x] #3 The same output path plays a track audibly on the native Linux install, or the blocker is recorded with the evidence
- [x] #4 The winning path's behaviour with the game's music volume, pause and ducking is observed and stated
- [x] #5 Every candidate tried, including the ones that failed and how they failed, is recorded in docs/music.md so TASK-024 can be built on the outcome without repeating the probe
- [x] #6 The probe is drivable from the dev harness while the game runs, so a candidate can be retried without a new launch where that is possible
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Completed investigation

1. Decode mp3 files with NLayer 1.16.0 under MelonLoader .NET 6 and expose repeatable decode/play/status commands through the development harness.
2. Test both callback signatures: managed float[] fails dispatch; Il2CppStructArray<float> produces audible PCM. Record volume/pause/duck behavior and limitations.
3. Following user approval, investigate native AudioClip creation within an approximately 30-minute/two-crash budget. Inspect the actual Win64 internal-call ABI, validate a short synthetic clip and PCM roundtrip, then audition an mp3 through the normal MusicTrack path. The corrected attempts succeeded without a new crash.
4. Hold pitch and source cutoff after MusicController.Update and confirm persistence with later status reads before asking for listening verdicts. Earlier one-shot setters were being reset and cannot establish callback pitch/filter bypass.
5. Document bindings, failed candidates, listening evidence and limitations in docs/music.md and harness usage in docs/development.md.

## Output decision

Prefer NLayer decode -> AudioClip.Construct_Internal() GC-handle unmarshal -> native clip m_CachedPtr -> runtime-resolved CreateUserSound_Injected/SetData_Injected with pinned pointer+length spans -> MusicTrack/PlayMusicTrack. This preserves the observed native clip processing without a software pitch/duck/filter engine. No hardcoded RVAs are used.

Native Linux ABI inspection and audible verification remain production prerequisites. Keep those open in TASK-024; the spike permits a recorded Linux blocker. Do not extend this probe into the full feature as part of this subtask.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Verification and evidence

- Decoder: in-game Police Truck decode matched host at 44,100 Hz stereo, 12,789,504 samples (6,394,752 frames), peak 1.0414. All 14 original source files decoded on the host; this is not a claim that the newly added Strobe file was tested.
- Callback candidate: Il2CppInterop skipped float[] with an unsupported Single[] parameter warning and zero callbacks. Il2CppStructArray<float> was audible and followed Options Music volume. Source Pause froze callback/frame counters; editor freeze did not. clip=null left callbacks and audio running despite isPlaying=false. Source-volume duck to 0.2 was not heard during resumed gameplay.
- Correction: initial pitch/cutoff tests were one-shot writes subsequently reset by game updates. The earlier no-change listening results are inconclusive for callback pitch/low-pass behavior, not proof of bypass.
- Native binding inspection: Win64 Unity 2023.2.22f1 UnityPlayer.dll still registers the required internal calls. Inspected RVAs: Construct_Internal_Injected 0x1217A0, CreateUserSound_Injected 0x1218A0, SetData_Injected 0x1216F0, GetData_Injected 0x121660. These identify evidence for this binary, not portable constants.
- Native pointer boundary: Construct_Internal() unmarshals a GC handle to an Il2Cpp AudioClip; m_CachedPtr is the injected-call native self. Neither the constructor handle nor Il2Cpp object Pointer is that native self. Creation takes frames; float spans take samples. Name is pinned UTF-16; span layout is pointer+int; native bool return is one byte. The precise cause of the initial crash was not established, but the corrected binding works.
- Native playback: a two-second 44.1 kHz mono tone was audible. The relative Police Truck mp3 became a 145.005-second stereo AudioClip with exact PCM prefix roundtrip (up to 4096 frames). the maintainer confirmed clear playback in THPS, natural menu/item-choice ducking, slower/lower playback at held pitch 0.55, and clear muffling at held source cutoff 400 Hz. Later status reads confirmed held controls persisted. No injected filter was attached. Test overrides were released afterward.
- Environment: Bluetooth device changes left an old Wine process silent; relaunch restored audio. Native Linux's second machine was unavailable, and the maintainer explicitly chose to record the blocker. The native diagnostic currently rejects non-Win64 pending ABI inspection.
- OS audio (waveOut/ALSA) was not attempted because the Unity paths were audible. Filter-chain reordering/software compensation was not needed after native clip success.

## Delivery and completion hygiene

Implementation, regression tests, documentation and investigation records were committed and pushed to origin/main as 36257ac (feat(mod): prove runtime mp3 playback through native audio clips). task check passed: 1310 C# tests, 513 Python tests, mod build and lint.

Process deviation: original exploratory probe/parser code preceded its regression tests, so the test-first Definition of Done item remains unchecked rather than being falsely certified. New native-action parser tests were observed failing before those actions were implemented, then passing. The diagnostic investigation and all acceptance criteria are complete; Linux AC3 is satisfied by its explicitly allowed recorded-blocker outcome. The parent feature remains unfinished.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Proved runtime mp3 playback through a real Unity AudioClip and selected NLayer -> native clip -> existing MusicTrack as the production direction. the maintainer confirmed clear playback, natural menu/item ducking, held pitch/tempo changes and held source low-pass behavior in THPS. Corrected earlier inconclusive one-shot pitch/filter findings.

Delivered harness commands, native binding diagnostics, regression tests and docs in pushed commit 36257ac. task check passed (1310 C# + 513 Python tests, build/lint).

Native Linux remains blocked/unverified. Folder discovery, track references, prefix ordering and boombox integration belong to TASK-024 and are not implemented. Original exploratory code was not test-first; that checklist item remains explicitly unchecked.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
