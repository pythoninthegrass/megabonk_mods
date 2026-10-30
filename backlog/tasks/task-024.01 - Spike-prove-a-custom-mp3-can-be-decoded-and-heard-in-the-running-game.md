---
id: TASK-024.01
title: 'Spike: prove a custom mp3 can be decoded and heard in the running game'
status: In Progress
assignee:
  - agent
created_date: '2026-10-30T00:06:00Z'
updated_date: '2026-10-30T01:16:00Z'
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
TASK-024 wants a player to drop mp3 files into a folder and hear them as stage music and on the boombox radio with no Unity install and no pack build. The only way to get a clip into the game today is importing it into an AssetBundle, so the runtime path is unproven and is the main risk in that task; this spike settles it before the feature work starts, on both the Wine/CrossOver macOS setup and the native Linux install.

What the game's build allows is not recoverable from the repo's own code, so it is recorded here. In .tools/il2cpp_dump/dump.cs the AudioClip type exposes only length, loadState, LoadAudioData and UnloadAudioData: AudioClip.Create, SetData and GetData were stripped from the managed metadata by Unity, which is why docs/music.md records MissingMethodException from those calls in the running game, and why hand-built span wrappers over AudioClip's internal constructors crashed the game. VideoPlayer survives only as its native callback bridges with no usable public API, and DownloadHandlerAudioClip is absent. So decoding mp3 to PCM is the easy half (a mod runs as real managed code under MelonLoader's .NET 6 and can use a pure-managed decoder) and delivering PCM to the audio device without a Unity AudioClip is the open question. Two candidate paths are worth trying, in the order Lance prefers: injecting samples through OnAudioFilterRead on a mod-defined component attached to the game's music AudioSource, which would keep the game's mixer, volume and ducking, and P/Invoking the OS audio APIs (waveOut on Windows/Wine, ALSA on Linux), which bypasses the mixer entirely.

The spike needs to end with a decision and its evidence, not a feature.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A pure-managed mp3 decoder decodes the tools/ost mp3s inside the running game and logs sample rate, channel count, sample count and duration for a track
- [x] #2 One output path plays a track audibly in the running game on the Wine/CrossOver macOS setup, confirmed by Lance hearing it rather than by log lines alone
- [x] #3 The same output path plays a track audibly on the native Linux install, or the blocker is recorded with the evidence
- [x] #4 The winning path's behaviour with the game's music volume, pause and ducking is observed and stated
- [x] #5 Every candidate tried, including the ones that failed and how they failed, is recorded in docs/music.md so TASK-024 can be built on the outcome without repeating the probe
- [x] #6 The probe is drivable from the dev harness while the game runs, so a candidate can be retried without a new launch where that is possible
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Probe design

A new dev-harness command `music-probe` drives everything, so a candidate can be retried without relaunching: `{"command":"music-probe","action":"decode|play|stop|status","path":"<mp3>"}`. It returns a JSON result and logs a line per phase. Files land in `<game>/harness/commands`, the same channel scripts/run.py and the MCP server already use.

## Steps

1. **Decoder**: Nuget `NLayer` 1.16.0 (pure managed mp3 to float PCM, restores clean) as a PackageReference in `src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj`; deploy `NLayer.dll` next to the mod DLL so MelonLoader resolves it (Mods first, UserLibs if that fails). `action=decode` opens the file and logs sample rate, channels, length and decoded sample count: acceptance criterion #1.
2. **Candidate A, OnAudioFilterRead** (Lance's preference, keeps the game's mixer): register a mod-defined MonoBehaviour through `ClassInjector.RegisterTypeInIl2Cpp<T>()` (present in this Il2CppInterop), attach it to the GameObject that holds `MusicController.Instance.musicSource`, and overwrite the filter buffer with PCM from a background decode. The callback keeps no Unity calls and logs nothing; it only advances counters that `action=status` reads (callback count, samples consumed, peak). Pass means callbacks fire, samples flow and Lance hears the track with the stock music replaced by ours.
3. **Candidate B, OS audio**, only if A fails: P/Invoke `winmm` waveOut on the Wine/Windows install and ALSA `libasound` on the native Linux install, fed by the same decoded PCM. Record how A failed first.
4. **Mixer behaviour**: read `musicSource.volume`, `MusicController.volumeMultiplier` and the `MusicVolume` mixer parameter around playback, and note whether a MusicPauseZone ducks the injected audio: acceptance criterion #4.
5. **Record**: write the outcome, the failed candidates and the caveats into `docs/music.md`.

## Risks

- The Unity audio thread may not be attached to the CoreCLR MelonLoader hosts, so the first managed call in the filter could crash with no managed log; keep the callback minimal and be ready to prove the crash with a counter taken before and after.
- Il2CppInterop's injected type may not get `OnAudioFilterRead` dispatched at all (nothing in the game implements it, so there is no precedent in the dump).
- Unity may apply the source volume before the filter, in which case the injected samples are attenuated by the game's own music volume; observe rather than assume.

## Environment

Wine prefix install at `~/.local/share/megabonk/wine` on this Mac; the native Linux install is a second machine, so criterion #3 may end as a recorded blocker.

Runtime findings revise the initial mixer assumption: use the Il2CppStructArray callback as the viable output candidate, but source gain/duck, pitch/tempo and source low-pass are bypassed in the tested arrangement. Feature work must address those explicitly; it is not implemented by this spike. Probe decoding is synchronous whole-track decoding, not the originally proposed background path. Native Linux is recorded as blocked per Lance's choice.

Approved follow-on investigation: spend at most approximately 30 minutes and two crash-producing native attempts investigating real AudioClip creation from decoded relative mp3 files, before considering callback filter reordering/software compensation. Inspect Unity version, generated interop and native call ABI before executing. Add an explicit harness-only native probe; first validate construction/PCM write on a short synthetic clip, then audition mp3 through normal MusicTrack. Record exact evidence and stop at the bound; do not implement the full runtime feature. Native Linux remains unverified.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: NLayer in-game decode of Police Truck matched host: 44,100 Hz stereo, 12,789,504 samples, peak 1.0414. Lance heard Screamer replace stock music and confirmed Options Music volume works. Managed float[] callback was skipped by Il2CppInterop as unsupported; Il2CppStructArray<float> callback produces audible PCM. waveOut/ALSA was not tried.

Signal tests: source Pause freezes counters; editor freeze does not. Removing the stock clip leaves isPlaying false but callbacks and audible custom music continue. Resumed gameplay confirmed sourceVolume=0.2 from duck multipliers, but Lance heard no attenuation. sourcePitch=0.55 also made no audible difference. This continuation tested a confirmed clear 22,000 Hz baseline then held source low-pass cutoff at 400 Hz; Lance reported no change. This only proves the source-filter arrangement, not the separate mixer MusicLowpass parameter.

Native Linux blocker (AC3's allowed alternate outcome): second machine unavailable for playback verification; Lance explicitly chose 'Record it as blocked'. No claim of native Linux playback success.

docs/music.md records candidates, behavior, timing/rate evidence, limitations and output decision; docs/development.md documents reproducible music-probe commands. Added C# parser and Python CLI regression coverage (including the action/subcommand destination collision). Fixed per-variant registration and reset timing totals on play/restart. task check passes: 1307 C# tests, 510 Python tests, lint and mod build. Fresh relaunch restored the example forest in frozen editor mode with no probe attached.

All spike acceptance criteria have evidence, including recorded Linux blocker. Kept In Progress pending completion hygiene: changes remain uncommitted; tests were added after the exploratory implementation, so 'tests written first' cannot truthfully be checked. No production runtime music feature implemented. Do not close the parent task.

Follow-on native probe SUCCEEDED, superseding the earlier callback recommendation. Inspected the player's UnityPlayer.dll (Unity 2023.2.22f1 Win64) and live-resolved internal calls: Construct_Internal_Injected RVA 0x1217A0, CreateUserSound_Injected 0x1218A0, SetData_Injected 0x1216F0, GetData_Injected 0x121660. These are evidence, not hardcoded bindings. No new native crash occurred.

Correct binding path: AudioClip.Construct_Internal() unmarshals the constructor's GC handle into an Il2Cpp AudioClip; clip.m_CachedPtr is the native self pointer. Pass pinned UTF-16 name / float PCM via a blittable pointer+int span to runtime-resolved injected calls. PCM spans count samples, creation counts frames; bool return is one byte. Using the GC handle or the Il2Cpp object pointer as native self is invalid. The exact cause of the earlier crash is not proven, but correct handle conversion plus native pointer/span binding now works.

Behavior evidence: native-tone created 2 seconds of 44.1 kHz mono, roundtrip error 0, audible steady tone confirmed by Lance after a requested Bluetooth-device relaunch. native-play loaded relative '01 Police Truck.mp3' into a 145.005-second 44.1 kHz stereo AudioClip; checked prefix up to 4096 frames had roundtrip error 0. On THPS, Lance confirmed song clear, and separately volunteered that menu/item-choice ducking works correctly. With explicit controls held after MusicController.Update and verified in later status reads, Lance confirmed pitch 0.55 makes it slower/lower and source cutoff 400 Hz makes it clearly muffled. No OnAudioFilterRead component was attached. Overrides subsequently released; THPS and native mp3 remain loaded.

Correction to earlier evidence: one-shot pitch/cutoff setters were being reset by the game (later pitch read 1, cutoff alternated 600/22000). Therefore previous 'no change' responses do NOT prove callback pitch/low-pass bypass. docs/music.md now labels those tests inconclusive. The held-control tests above were performed on native clips only.

Implementation: music_native_probe.cs adds harness-only native-info/native-tone/native-play; native probe rejects non-Win64 until ABI inspection on that platform. Prefix PCM roundtrip verifies writes before PlayMusicTrack. New action parser tests were observed failing before implementation, then passed. task check now passes 1310 C# tests and 513 Python tests, plus build/lint. Documentation updated with native binding details, corrected observations, platform restriction and command/control lifecycle. Still uncommitted; original test-first DoD remains unchecked because earlier exploratory code predates its tests.
<!-- SECTION:NOTES:END -->
