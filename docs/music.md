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

The THPS Warehouse places the game's boombox (`interactable/boombox`, `EffectManager.boomboxQuest`) as a radio. While a custom run with a level `music` reference is active, a Harmony patch on `InteractableBoombox.Interact` plays the next clip of the same pack through `MusicController.PlayMusicTrack`, so it replaces the level music everywhere, not just near the boombox. `RadioPlaylist` orders the pack's clips by name (the file names carry the soundtrack order, `01_Police_Truck` through `13_Le_Hot_99`), starts at the first clip and wraps. The patch skips the stock interaction, which is single-use (it sets the private `done` flag) and throws a `NullReferenceException` when run a second time, so the boombox stays pressable and cycles through the soundtrack. A level without `music`, or a vanilla run, leaves the boombox alone.

If the pack holds no clip to play, or playing it throws, the patch logs `Radio: ...; using the boombox's stock audio.` as a warning and the stock interaction runs unchanged.

## Fallback

If `music` is not a two-segment `bundle:` id, the pack is not installed, the pack holds no clip of that name, or creating the track throws, `LevelMusic.Prepare` logs `Music: ...; using the stock music.` as a warning and no track is substituted. Nothing throws out of the patch.

## Audio formats and decoding

The mod does not decode audio at runtime. Unity's runtime decode and clip-creation paths do not work in this build, so the audio is imported into the pack in the authoring project and ships as a normal `AudioClip` in the bundle (the clip is held compressed in memory as Vorbis, quality 0.7). Any format the Unity editor imports works as the source, including mp3, ogg and wav. `ThpsPack.SaveSoundtrack` imports every mp3 in `tools/ost` (override the directory with `-musicSource`), naming each clip by its file name with runs of other characters made an underscore; the build skips them with a log line when the directory is absent, so the pack still builds without them. `scripts/transcode.py` can produce an mp3 from a lossless source.

The runtime paths that fail, confirmed in the running game:

- `UnityWebRequestMultimedia.GetAudioClip` throws `MissingMethodException` for `DownloadHandlerAudioClip..ctor(String, AudioType)`.
- `AudioClip.Create` throws `MissingMethodException` for `Il2CppSystem.ReadOnlySpan<T>.GetPinnableReference()`, which its name marshalling needs; `SetData` takes the same span path.
- Calling `AudioClip.Construct_Internal_Injected` then `CreateUserSound_Injected` with a hand-built `ManagedSpanWrapper` crashes the game with no managed log.

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
