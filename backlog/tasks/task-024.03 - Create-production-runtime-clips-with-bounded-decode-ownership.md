---
id: TASK-024.03
title: Create production runtime clips with bounded decode ownership
status: Done
assignee:
  - Assistant
created_date: '2026-10-30T02:24:00Z'
updated_date: '2026-10-30T02:53:00Z'
labels:
  - music
dependencies:
  - TASK-024.02
documentation:
  - docs/music.md
parent_task_id: TASK-024
ordinal: 122000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The successful native mp3 probe is diagnostic and retains whole-track PCM. Production playback needs reusable clip creation and bounded lifetime without replacing the game's music processing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The native probe and production playback share the verified native AudioClip creation path with platform guards.
- [x] #2 Current track and one prefetched successor have bounded decode and clip ownership, including limits for oversized or malformed input.
- [x] #3 Track replacement and cancellation release obsolete buffers and Unity objects safely, including rapid switches and leaving a run.
- [x] #4 Testable decode and ownership policies have tests written first; diagnostic commands retain their behavior and documentation is updated.
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
1. Write failing tests for bounded block-based PCM decoding and a generic runtime track owner using fake decode/create/play/destroy delegates. Cover cancellation, malformed dimensions/samples, size limits, failed replacements, prefetch reuse, rapid replacement and disposal.
2. Add PcmAudio/Mp3Decoder using pinned NLayer 1.16.0; retain PCM in fixed blocks to avoid whole-track List<float>/ToArray duplication. Limit compressed input to 64 MiB and decoded PCM to 256 MiB per track, with checks during reads and cancellation between blocks. Long tracks can exceed the earlier rough 50 MB estimate; expose and document actual limits.
3. Add RuntimeMusicOwner<T>: all public calls on game thread, one background managed-only successor decode; cancellation joins the single worker before replacing its request, stale results are discarded, Unity resources created/played/released only by caller. Keep current native resource plus one managed prefetch; creation briefly overlaps old/new native clips. Failed play preserves the old resource. Dispose is idempotent and requires playback already switched away.
4. Extract RuntimeAudioClip factory from the verified native probe. Preserve Win64 guard, GC-handle/native-pointer boundary and PCM readback; upload PCM blocks at frame offsets. Add disposable runtime MusicTrack resource for later integration, without changing LevelMusic yet. Refactor native probe to the shared factory/owner.
5. Run tests and task check, relaunch with default Wine and verify diagnostic tone/mp3 native roundtrip and switches; human hearing remains explicit. Document ownership, threading, limits and remaining integration/platform work. Commit separately.

Implementation refinement: RuntimeMusicTrack.Dispose can safely stop/detach its own still-active source and clear currentTrack before destruction, so explicit shutdown does not require a caller to have switched first. It leaves replacement/menu resources alone. Native probe now uses the shared owner as well as the factory; MusicController.Update releases probe ownership when a different track takes over. Level-run lifecycle wiring remains 024.04. All PCM blocks are read back using a reusable scratch buffer, rather than only the first prefix.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Test-first red: task mod:test failed on missing PcmAudio and RuntimeMusicOwner APIs before implementation. Added pure policy tests, then NLayer adapter integration tests using a tiny generated sine fixture (no copyrighted soundtrack in tests). Tests cover PCM limits, dimensions, empty/nonfinite output, finite >1 peaks, short-read block packing, cancellation, missing/empty/oversized/invalid files, exclusive file reopen, prefetch reuse/cancel/join, ignored late completion, failure cleanup, thread affinity, 50 rapid handoffs with at most two live fake resources, and idempotent disposal. task check passes: 1,346 xUnit and 513 Python tests, mod build/deploy, markdownlint and ruff.

Default Wine verified at ~/.local/share/megabonk/wine, with rebuilt DLL and fresh relaunch. Native-tone: 88,200 frames, 44.1 kHz mono, 2 seconds, full roundtrip max error 0. Police Truck: 6,394,752 frames, 44.1 kHz stereo, 145.005 seconds, full roundtrip error 0. Le Hot '99: 26,992,512 frames, 48 kHz stereo, 562.344 seconds, full roundtrip error 0. Strobe: 28,041,984 frames, 44.1 kHz stereo, 635.872 seconds, full roundtrip error 0. Switches long-track → tone → Police Truck and Le Hot → Strobe succeeded with sourceIsPlaying true, no crash. Le Hot/Strobe were accessed through explicit Wine Z: host paths, not installed/discovered runtime tracks. Strobe left in frozen editor for user listening.

Malformed MPEG input (docs/music.md supplied explicitly to the diagnostic) returned 'Not a valid MPEG file!'; status still reported Police Truck active. A bare '14 Strobe.mp3' lookup correctly reported absent before explicit host-path audition; no source files were copied or packs rebuilt. Fresh human audible confirmation not claimed. Native Linux remains guarded/unverified, and production track: stage/radio/prefetch lifecycle hooks remain for 024.04. Generic disposal/cancellation and native replacement cleanup are verified here; actual level-exit integration will be checked there.

Fresh human listening confirmation after delivery: Lance connected earphones and requested a relaunch. Relaunched default Wine into THPS frozen editor and replayed 14 Strobe through the shared native factory/owner (635.872s, 44.1kHz stereo, full roundtrip error 0, sourceIsPlaying true). Lance confirmed: 'Yes! Works perfectly'. This confirms audible playback on this Wine setup; native Linux and stage/radio integration remain unverified.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added shared guarded native clip creation with block uploads/full PCM readback, bounded NLayer decoding (64 MiB input/256 MiB PCM), a game-thread resource owner with one cancellable managed prefetch, and disposable runtime MusicTrack/AudioClip ownership. Native probe now uses the production primitives; existing diagnostic action names remain intact. Test-first policy coverage plus generated-MP3 integration tests; task check passes 1,346 C# and 513 Python tests, build/deploy and lint. Default Wine tone/44.1 kHz and 48 kHz tracks, long tracks, replacement/replay and malformed-input preservation verified with zero PCM roundtrip error. Commit a68e2ac. Stage/radio integration, actual level-exit lifecycle wiring and production prefetch scheduling remain 024.04; native Linux remains 024.05. Fresh human listening confirmation was not claimed; Strobe left reporting active in frozen editor.
<!-- SECTION:FINAL_SUMMARY:END -->
