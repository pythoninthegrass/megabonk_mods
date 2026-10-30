# Music

How Megabonk selects and plays music, and the points a mod can hook to replace it. Class and field names come from `.tools/il2cpp_dump/dump.cs`; call flow comes from the `GameAssembly.dll` decompile in Ghidra (RVA = VA - `0x180000000`, see "Using Ghidra through REA" in `development.md`).

## Engine

Music is plain Unity `AudioSource` and `AudioClip`. There is no FMOD or Wwise. A single `AudioSource` on `MusicController` plays one clip at a time; sound effects use the separate `AudioManager`.

## Classes

| Class | Role |
| --- | --- |
| `MusicController : MonoBehaviour` | Singleton (`Instance`, static slot 0x0) that owns the `AudioSource` and plays tracks |
| `MusicTrack : ScriptableObject` (`Assets.Scripts.Audio.Music`) | One track: optional `intro` clip and a looping `loop` clip |
| `MusicUtility` (`Assets.Scripts.Audio.Music`) | Static helper that picks the track for a run |
| `MusicSelectionUi` | Main-menu jukebox; sets `RunConfig.musicTrackIndex` |
| `MusicPauseZone` | Ducks the music while the player is inside a radius |
| `LowpassController` | Drives the `MusicVolume` and `MusicLowpass` mixer parameters |

`MusicController` fields: `musicSource` 0x20, `lowpassFilter` 0x28, `volumeMultiplier` 0x30, `desiredVolumeMultiplier` 0x34, `desiredVolume` 0x38, `menuMusicTrack` 0x40, `currentTrack` 0x48, `isPlayingIntro` 0x50, `introLength` 0x54, `defaultPitch` 0x58.

`MusicTrack` fields: `isEnabled` 0x18, `isInJukebox` 0x19, `isInRandomPool` 0x1A, `maxStageCompatibility` 0x1C, `category` 0x20 (`MusicCategory`: Forest 0, Desert 1, Other 2, Graveyard 3), `trackName` 0x28, `intro` 0x30, `loop` 0x38. Tracks are named assets; there are no numeric track ids.

## Methods and RVAs

| Method | RVA |
| --- | --- |
| `MusicController.OnStageStarted` | 0x3593D0 |
| `MusicController.PlayStageMusic` | 0x359780 |
| `MusicController.PlayMusicTrack(MusicTrack)` | 0x3595C0 |
| `MusicController.PlayMenuTrack` | 0x359540 |
| `MusicController.OnMainMenu` | 0x359130 |
| `MusicController.StopMusic` | 0x3598E0 |
| `MusicController.Update` | 0x35A110 |
| `MusicUtility.GetMusicTrackToPlay(RunConfig)` | 0x4B40A0 |
| `MusicUtility.GetTracks` / `GetTracksOther` | 0x4B4A40 / 0x4B4770 |
| `MusicTrack.LoadToMemory` / `UnloadFromMemory` | 0x4B3F20 / 0x4B3FD0 |
| `MusicSelectionUi.UpdateTrack` | 0x573F30 |

Each RVA is listed once in the dump, so none is a folded shared stub.

## Selection flow

A stage start reaches the music through two entry points that behave the same way:

1. `OnStageStarted` zeroes `volumeMultiplier`, then returns early when `MapController.isFinalBossStage` (static 0x20) is set. Otherwise it calls `GetMusicTrackToPlay(MapController.runConfig)` and passes the result to `PlayMusicTrack`.
2. `PlayStageMusic` does the same without the final-boss check.

`GetMusicTrackToPlay(runConfig)` is the only function that picks a stage track, and its two callers are the methods above. Its logic:

- On the final boss stage it returns `runConfig.mapData.bossTrack` (`MapData` 0xB8) when that is set.
- When `runConfig.musicTrackIndex` (0x30) is not -1 it returns `GetTracks()[musicTrackIndex]`. This is the jukebox choice.
- Otherwise it picks randomly: about 15% of the time the current character's `themeSong` (`CharacterData` 0x78, subject to `themeTrackPlayedLastRound`) or a `GetTracksOther()` entry, and else the next entry of `mapData.musicTracks` (`MapData` 0xB0), tracked per `EMap` in `mapTrackRotation`.

`PlayMusicTrack(track)`:

1. Calls `UnloadFromMemory` on the previous `currentTrack` when it differs from the new one.
2. Returns without changes when the new track equals `currentTrack` and `volumeMultiplier` is not 0.
3. Stores `currentTrack`, then calls `LoadToMemory`, which calls `AudioClip.LoadAudioData` on `intro` and `loop` when each is non-null.
4. With a non-null `intro`: sets the source clip to `intro`, `loop = false`, `isPlayingIntro = true` and `introLength = intro.length`; `Update` switches to `loop` once the intro ends.
5. With a null `intro`: sets `loop = true`, `isPlayingIntro = false` and the source clip to `loop`.
6. Calls `Play` on the source and sets `volumeMultiplier` to 1.

A track with only a `loop` clip is therefore valid and starts playing immediately.

Other callers of `PlayMusicTrack`: `OnMainMenu`, `PlayMenuTrack` (menu track), `MusicSelectionUi.UpdateTrack` (jukebox preview), and the method at 0x505F90, which plays a boss-room track (`GraveyardBossRoom.musicTrackBoss` 0x60) when its timer elapses. These bypass `GetMusicTrackToPlay`.

## Level music

A level file's optional `music` field (see [level-format.md](level-format.md)) names an `AudioClip` as `bundle:<pack>/<clip>`. The mod replaces the stock stage music with it:

1. `LevelLoaderPatch.StartOnce` calls `LevelMusic.Prepare` before the run starts. It parses the reference (`LevelMusicReference`), asks `PackPrefabs.ResolveClip` for the clip, and builds a `MusicTrack` with `ScriptableObject.CreateInstance` whose `loop` is the clip and whose `intro` stays null.
2. A Harmony prefix on `MusicUtility.GetMusicTrackToPlay` returns that track and skips the original while a custom run is active (`CustomLevelState.IsActive`). A vanilla run, or a level without `music`, passes through to the stock logic.
3. `OnStageStarted` and `PlayStageMusic` then hand the track to `PlayMusicTrack`, which loops the clip.

`PackPrefabs` collects every `AudioClip` in a pack's bundles next to the prefabs when it loads the pack. The clip is looked up by its asset name, which is the file name without extension. A manifest `assets` list filters prefabs only and does not list clips.

Not covered: callers that pass a track straight to `PlayMusicTrack` (main menu, the jukebox preview, the boss-room trigger at 0x505F90) and a final boss stage, where `OnStageStarted` does nothing and the boss room picks its own track.

An editor save writes the loaded `music` value back (`LiveEditPatch.SnapshotLevelFile`). Loading a level file from the editor's load list does not restart the music, the same as it does not re-apply `noGrass`, `playerStart` or `maxSlopeAngle`.

## Radio

The THPS Warehouse places the game's boombox (`interactable/boombox`, `EffectManager.boomboxQuest`) as a radio. While a custom run with a level `music` reference is active, a Harmony patch on `InteractableBoombox.Interact` plays the next clip of the same pack through `MusicController.PlayMusicTrack`, so it replaces the level music everywhere, not just near the boombox. `RadioPlaylist` orders the pack's clips by name (the file names carry the soundtrack order, `01_Police_Truck` through `13_Le_Hot_99`), continues from the level's own clip (`StartAfter`, so the first press after `04_Superman` plays `05_Jerry_Was_A_Race_Car_Driver`) and wraps. Both the level clip and a radio clip are looping clips, so `LevelMusic.Tick` (from `OnUpdate`) watches the music source's playback time and, when it jumps back to the start, plays the next clip instead of letting the same one repeat (`RadioPlaylist.LoopWrapped`). It only follows clips the mod handed to `PlayMusicTrack`; the menu, jukebox and boss tracks are left alone. Each press calls `Next` once, so presses made in quick succession skip clips. The patch skips the stock interaction, which is single-use (it sets the private `done` flag) and throws a `NullReferenceException` when run a second time, so the boombox stays pressable and cycles through the soundtrack. A level without `music`, or a vanilla run, leaves the boombox alone.

If the pack holds no clip to play, or playing it throws, the patch logs `Radio: ...; using the boombox's stock audio.` as a warning and the stock interaction runs unchanged.

## Fallback

If `music` is not a two-segment `bundle:` id, the pack is not installed, the pack holds no clip of that name, or creating the track throws, `LevelMusic.Prepare` logs `Music: ...; using the stock music.` as a warning and no track is substituted. Nothing throws out of the patch.

## Audio formats and decoding

Level and radio playback currently use imported clips, not runtime decoding. Audio is imported into the pack in the authoring project and ships as a normal `AudioClip` in the bundle (the clip is held compressed in memory as Vorbis, quality 0.7). Any format the Unity editor imports works as the source, including mp3, ogg and wav. `ThpsPack.SaveSoundtrack` imports every mp3 in `tools/ost` (override the directory with `-musicSource`), naming each clip by its file name with runs of other characters made an underscore; the build skips them with a log line when the directory is absent, so the pack still builds without them. `scripts/transcode.py` can produce an mp3 from a lossless source. Runtime clip creation is proven through the native probe below, despite failures in the ordinary managed wrappers.

The runtime paths that fail, confirmed in the running game:

- `UnityWebRequestMultimedia.GetAudioClip` throws `MissingMethodException` for `DownloadHandlerAudioClip..ctor(String, AudioType)`.
- `AudioClip.Create` throws `MissingMethodException` for `Il2CppSystem.ReadOnlySpan<T>.GetPinnableReference()`, which its name marshalling needs; `SetData` takes the same span path.
- An initial direct `Construct_Internal_Injected` / `CreateUserSound_Injected` attempt with a hand-built span crashed with no managed log. This does not establish that native clip creation is unavailable: the corrected handle/pointer path below succeeds.

## Runtime PCM probe

The development harness can decode mp3 files and audition either native `AudioClip` playback or buffer injection. This is a diagnostic probe, not a level or radio playback implementation; `bundle:` playback remains unchanged. See [development.md](development.md#runtime-music-probe) for commands.

### Decoder and output decision

NLayer 1.16.0 decodes mp3 files as managed float PCM under MelonLoader's .NET 6. The mod build copies `NLayer.dll` into both `Mods` and `UserLibs`; `CopyLocalLockFileAssemblies` is needed to get the dependency into the build output. A complete in-game decode of `01 Police Truck.mp3` produced 44,100 Hz stereo, 12,789,504 samples (6,394,752 frames), and peak 1.0414, matching the host decode. The 14 source files include both 44.1 and 48 kHz material and decoded successfully on the host; decoder peaks can exceed 1.0.

**Prefer a real native `AudioClip`**, populated with NLayer PCM and passed to the existing `MusicTrack` path. The native probe created a two-second 44.1 kHz tone and then a 145.005-second stereo clip from the relative file `01 Police Truck.mp3`. Native `GetData_Injected` returned an exact match for the checked PCM prefix (up to 4,096 frames). Lance heard the tone and the song, and verified the modulation behavior below in THPS. No crash occurred in the corrected native attempts. The OS-audio fallback was not needed.

### Native binding details

The verified player is Win64 Unity 2023.2.22f1, running under Wine on macOS. `UnityPlayer.dll` still registers the relevant internal calls even though their managed methods were stripped. Resolve them by name with `IL2CPP.il2cpp_resolve_icall`, not hardcoded addresses. The inspected RVAs were `Construct_Internal_Injected` 0x1217A0, `CreateUserSound_Injected` 0x1218A0, `SetData_Injected` 0x1216F0 and `GetData_Injected` 0x121660; these are evidence for this binary, not portable constants.

The important boundary is **GC handle → Il2Cpp object → native Unity object**:

1. Use `AudioClip.Construct_Internal()`, whose generated wrapper calls `Unmarshal.UnmarshalUnityObject<AudioClip>` on the handle returned by `Construct_Internal_Injected`. Do not wrap that handle with `new AudioClip(handle)` or treat it as a native pointer.
2. Read the resulting clip's `m_CachedPtr`. This native pointer, not the Il2Cpp object's `Pointer`, is the `self` argument for the injected creation/data calls.
3. Call `CreateUserSound_Injected` with a pinned UTF-16 name described by a blittable `{ IntPtr begin; int length; }` span, frame count, channels, source rate and a zero streaming byte. This avoids the stripped Il2Cpp span marshalling helper.
4. Pin the managed float PCM and pass a span of **sample count**, not frame count, to `SetData_Injected`. The call is synchronous; unpin after it returns. The native boolean return is one byte. Verify a prefix through `GetData_Injected` before playback.
5. Keep the clip and `MusicTrack` alive, set `track.loop = clip`, and use `MusicController.PlayMusicTrack`. No audio-thread injection or software resampling is needed for this path; Unity samples a clip at its declared source rate.

Native Linux playback remains unverified: the second machine was not reachable, and Lance chose to record that blocker. The native probe currently rejects non-Win64 execution until its ABI has been inspected there. Do not assume the Windows ABI or addresses apply to Linux.

### Observed signal behavior

| Control | Observed result with the native mp3 clip |
| --- | --- |
| Normal playback | Police Truck clearly audible in THPS with no injected filter attached |
| Menus and item choices | Lance confirmed the game's natural ducking works |
| Source pitch held at 0.55 | Later status confirmed the value persisted; Lance heard slower tempo and lower pitch |
| Source low-pass held at 400 Hz | Later status confirmed the cutoff persisted; Lance heard clear muffling |

Release test overrides afterward: `music-probe pitch` and `music-probe lowpass` without `--value` return control to the game. The native clip enters the same playback path as a pack clip; these tests establish the key observed behaviors, not exhaustive parity across every game state or platform. The separate mixer `MusicLowpass` parameter was not independently forced.

### Buffer-injection alternative

An injected `MonoBehaviour.OnAudioFilterRead(Il2CppStructArray<float>, int)` also produces audible audio on the music source's GameObject. `AsSpan()` views Unity's buffer without copying it. The managed `float[]` signature failed: Il2CppInterop logged `has unsupported parameter Single[] data of type System.Single[]`, skipped the method, and its callback count stayed zero.

Lance confirmed injected music follows the Options Music slider, but heard no duck when the source volume read 0.2 during resumed gameplay. Source `Pause()` stops callback/frame counters; frozen editor gameplay does not. Setting `clip = null` leaves `isPlaying` false but callbacks and audible injected music continue. Attaching to a playing source does not require a restart.

Earlier one-shot pitch and low-pass tests reported no audible change, but later readings exposed the game resetting those properties. Those tests are **inconclusive**, not proof the processing is bypassed; held-control tests were subsequently performed on native clips only. Component/filter ordering would also need checking before using injection for parity.

The injection probe copies one source frame per output frame without resampling. A 24.21-second measurement consumed about 48,047 frames/second, so 44.1 kHz material advances about 8.95% too fast on that output path, although Lance did not notice the speed difference by ear. Callback copy cost was in the tens of microseconds, versus about 21 ms for 1,024 frames at 48 kHz; this is diagnostic timing, not a production benchmark.

### Implications for runtime playback

Build runtime playback around native clip creation and the existing `MusicTrack` pipeline. There is no need to reproduce the game's pitch, ducking or low-pass in a custom callback on the verified player. Remaining work includes bounded decoding/memory, track discovery and ordering, clip ownership across switches, graceful fallback, and native Linux verification. The platform guard is deliberate: inspect and validate Linux bindings before enabling them.

The probe decodes a whole track synchronously into memory and loops it. It does not implement streaming, prefetched tracks, `track:` references or playlists. Switching native probe clips releases the previous probe track and clip after playback switches; relaunch returns to a clean stock baseline.

If both stock and injected music are silent while callbacks advance, first verify host audio with a native player and relaunch the game. In the test, an old Wine process was silent even with the probe detached; a fresh launch on the current Bluetooth output restored stock and injected audio. This is consistent with a stale output-device handle, not evidence that PCM injection failed.

## THPS soundtrack sources

The original PlayStation Tony Hawk's Pro Skater soundtrack has 14 tracks. Screamer and Nothing to Me are one file in the game. Ain't Got Time to Waste, Blue Thunder and Le Hot '99 are exclusive to the European release (titled Tony Hawk's Skateboarding); the first of those was dropped from the European Dreamcast and N64 ports. Albums and positions come from Discogs and MusicBrainz listings.

| Track | Artist | Source release |
| --- | --- | --- |
| Police Truck | Dead Kennedys | *Give Me Convenience or Give Me Death* (1987 compilation); first issued in 1980 as the B-side of the "Holiday in Cambodia" single |
| Here & Now | The Ernies | *Meson Ray* (1999) |
| Vilified | Even Rude | *Superabsorbent* (1998), track 12 |
| Superman | Goldfinger | *Hang-Ups* (1997), track 1 |
| Jerry Was a Race Car Driver | Primus | *Sailing the Seas of Cheese* (1991), track 5 |
| Screamer / Nothing to Me | Speedealer (credited REO Speedealer) | *REO Speedealer* (1998), tracks 2 and 11 of 15; reissued as *Speedealer* (2001) |
| Cyco Vision | Suicidal Tendencies | *Freedumb* (1999), track 5 |
| New Girl | The Suicide Machines | *Destruction by Definition* (1996), track 1 |
| Committed | Unsane | *Occupational Hazard* (1998, Relapse Records), track 1 |
| Euro-Barge | The Vandals | *Hitler Bad, Vandals Good* (1998), track 10 |
| Ain't Got Time to Waste | Aim feat. YZ | *Cold Water Music* (1999, ATIC Records), track 6; ripper metadata often dates it 2007, the year of a later reissue |
| Blue Thunder | Aquasky | *Bodyshock* (1999), disc 1 track 3 of 8 (a two-disc set) |
| Le Hot '99 | Grand Unified | *Skinful Vol. 3* (1999, Second Skin compilation), track 12 of 12; a remix of the 1998 12" EP *Le Hot*, also on the *Skinful Vol. 3 Sampler* 12" |

Two of these are widely misattributed. Cyco Vision is not on *Suicidal for Life* (1994), despite circulating under that album in soundtrack listings; the recording is from *Freedumb*. Committed is not on *Scattered, Smothered & Covered* (1995) either, which does not contain it.

Discogs also lists unofficial vinyl pressings of the game soundtrack, including the three European tracks, as an alternative to buying each release. The mp3s live under `tools/ost/`, which is gitignored along with the rest of `tools/`. Filenames carry the in-game running order (`06.01` and `06.02` are the two halves of the one file the game ships for Screamer / Nothing to Me); the ID3 tags describe the source album instead, holding the artist, album, year and position on that album rather than a soundtrack numbering, so a rip can be checked against its release. Tags are ID3 v2.3 with latin1 text and no comments, lyrics or attached images.

## Open questions

- What `Update` does with a null intro beyond `isPlayingIntro = false`; the track-switch path above does not set `introLength` for it, so it is expected to leave the loop alone.
- Whether `MusicTrack.UnloadFromMemory` (`AudioClip.UnloadAudioData`) on a pack clip, when another track replaces it, leaves the clip playable on the next stage; confirm in game.
- Which mix of Le Hot '99 the game uses: the rip runs 9:23 against the 6:47 *Skinful Vol. 3* cut, so it looks like an extended version of the 12" rather than the compilation track.
