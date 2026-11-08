using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json.Nodes;
using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Audio.Music;
using Il2CppInterop.Runtime;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

namespace MegabonkLevels;

// Routes custom stage music and radio through the game's normal MusicTrack path.
public static class LevelMusic
{
    private static MusicTrack _track;
    private static MelonLogger.Instance _logger;
    private static string _pack;
    private static RadioPlaylist _radio;
    private static IntPtr _radioTrack;
    private static bool _playingOurs;
    private static float _lastTime;
    private static CustomMusicLibrary _library = new();
    private static RuntimeMusicSession<RuntimeMusicTrack> _runtime;
    private static MusicTrack _bundleRadioTrack;
    private static bool _runtimeNeedsReload;

    public static void Initialize(MelonLogger.Instance logger)
    {
        _logger = logger;
        _library = CustomMusicLibrary.Discover(Path.Combine(MelonEnvironment.UserDataDirectory, "CustomMusic"), message => logger.Warning(message));
        logger.Msg($"Music: discovered {_library.Names.Count} custom tracks.");
    }

    public static void Clear()
    {
        ReleasePlayback();
        Reference = null;
    }

    private static void ReleasePlayback()
    {
        _playingOurs = false;
        _runtimeNeedsReload = false;
        _radioTrack = IntPtr.Zero;
        _lastTime = 0f;
        var runtime = _runtime;
        _runtime = null;
        if (runtime != null)
        {
            _track = null;
            runtime.Dispose();
            _logger?.Msg("Music: released runtime session and prefetch.");
        }
        else
        {
            ReleaseBundleTrack(_track);
            _track = null;
        }

        ReleaseBundleTrack(_bundleRadioTrack);
        _bundleRadioTrack = null;
        _pack = null;
        _radio = null;
    }

    private static void ReleaseBundleTrack(MusicTrack track)
    {
        if (track == null) return;
        var controller = MusicController.Instance;
        if (controller != null && controller.currentTrack == track)
        {
            controller.musicSource?.Stop();
            if (controller.musicSource != null) controller.musicSource.clip = null;
            controller.currentTrack = null;
        }

        track.loop = null;
        UnityEngine.Object.Destroy(track);
    }

    // The level's music reference as loaded, kept so an editor save writes it back.
    public static string Reference { get; private set; }

    internal static bool RuntimeActive => _runtime != null;

    // Resolves the level's clip and builds the replacement track; any failure warns and leaves the stock music.
    public static void Prepare(string reference, MelonLogger.Instance logger)
    {
        ReleasePlayback();
        Reference = reference;
        _logger = logger;
        if (reference == null)
        {
            return;
        }

        try
        {
            if (!LevelMusicReference.TryParse(reference, out var parsed))
            {
                logger.Warning($"Music: '{reference}' is not a track:<name> or bundle:<pack>/<clip> id; using the stock music.");
                return;
            }

            if (parsed.IsRuntime)
            {
                RuntimeAudioClip.EnsureSupported();
                var owner = new RuntimeMusicOwner<RuntimeMusicTrack>(
                    (path, token) => Mp3Decoder.Decode(path, token),
                    (path, audio) => new RuntimeMusicTrack(Path.GetFileNameWithoutExtension(path), audio),
                    track => track.Dispose());
                _runtime = new RuntimeMusicSession<RuntimeMusicTrack>(_library, owner);
                _runtime.Select(parsed.Asset, track => _track = track.Track);
                logger.Msg($"Music: using runtime track '{_track.trackName}' ({_runtime.Current.Clip.length:F3}s).");
                return;
            }

            var clip = PackPrefabs.ResolveClip(parsed.Pack, parsed.Asset);
            if (clip == null)
            {
                logger.Warning($"Music: no clip '{parsed.Asset}' in pack '{parsed.Pack}'; using the stock music.");
                return;
            }

            _pack = parsed.Pack;
            _radio = new RadioPlaylist(PackPrefabs.ClipNames(parsed.Pack));
            _radio.StartAfter(clip.name);
            _track = BuildTrack(clip);
            logger.Msg($"Music: using clip '{clip.name}' from pack '{parsed.Pack}' ({clip.length:F0}s).");
        }
        catch (Exception ex)
        {
            ReleasePlayback();
            logger.Warning($"Music: could not prepare '{reference}': {ex.Message}; using the stock music.");
        }
    }

    private static MusicTrack BuildTrack(AudioClip clip)
    {
        var track = ScriptableObject.CreateInstance(Il2CppType.Of<MusicTrack>()).Cast<MusicTrack>();
        track.hideFlags = HideFlags.HideAndDontSave;
        track.trackName = clip.name;
        track.loop = clip;
        return track;
    }

    private static bool PlayNext() => PlayStep(MusicActions.Next, 0);

    // Plays the playlist's next, previous or numbered clip as the level music; false when there is nothing to play.
    private static bool PlayStep(string action, int number)
    {
        if (_runtime != null)
        {
            Action<RuntimeMusicTrack> play = track =>
            {
                _radioTrack = track.Track.Pointer;
                track.Play();
            };
            switch (action)
            {
                case MusicActions.Prev:
                    _runtime.PlayPrevious(play);
                    break;
                case MusicActions.Track:
                    _runtime.PlayTrack(number, play);
                    break;
                default:
                    _runtime.PlayNext(play);
                    break;
            }

            _track = _runtime.Current.Track;
            _lastTime = 0f;
            _logger?.Msg($"Radio: playing runtime '{_track.trackName}'.");
            return true;
        }

        var name = action switch
        {
            MusicActions.Prev => _radio.Previous(),
            MusicActions.Track => _radio.Select(number),
            _ => _radio.Next(),
        };
        var clip = name == null ? null : PackPrefabs.ResolveClip(_pack, name);
        if (clip == null)
        {
            _logger?.Warning($"Radio: no playable clip '{name}' in pack '{_pack}'.");
            return false;
        }

        var track = BuildTrack(clip);
        _radioTrack = track.Pointer;
        try
        {
            MusicController.Instance.PlayMusicTrack(track);
        }
        catch
        {
            ReleaseBundleTrack(track);
            throw;
        }

        ReleaseBundleTrack(_bundleRadioTrack);
        _bundleRadioTrack = track;
        _lastTime = 0f;
        _logger?.Msg($"Radio: playing '{clip.name}'.");
        return true;
    }

    private static bool HasPlaylist => (_radio != null || _runtime != null) && CustomLevelState.IsActive;

    private static IReadOnlyList<string> PlaylistNames => _runtime != null ? _runtime.Names : _radio.Names;

    private static int CurrentNumber => _runtime != null ? _runtime.CurrentNumber : _radio.CurrentNumber;

    // Runs one console or harness music request; the result's message is what the console prints.
    public static JsonObject Transport(MusicArgs args)
    {
        if (args.Action is MusicActions.Play or MusicActions.Pause)
        {
            var source = MusicController.Instance?.musicSource ?? throw new InvalidOperationException("no music source in the scene");
            var wasPlaying = source.isPlaying;
            string reply;
            if (args.Action == MusicActions.Pause)
            {
                if (wasPlaying)
                {
                    source.Pause();
                }

                reply = MusicTransportReply.Pause(wasPlaying);
            }
            else
            {
                if (!wasPlaying)
                {
                    source.UnPause();
                }

                reply = MusicTransportReply.Resume(wasPlaying, source.isPlaying);
            }

            _logger?.Msg($"Music: {reply}.");
            return new JsonObject { ["message"] = reply, ["playlist"] = HasPlaylist };
        }

        if (!HasPlaylist)
        {
            return new JsonObject { ["message"] = MusicTransportReply.NoPlaylist, ["playlist"] = false };
        }

        var names = PlaylistNames;
        string message;
        switch (args.Action)
        {
            case MusicActions.List:
                message = MusicTransportReply.List(names, CurrentNumber);
                break;
            case MusicActions.Now:
                message = MusicTransportReply.Now(names, CurrentNumber);
                break;
            default:
                if (args.Action == MusicActions.Track && args.Track > names.Count)
                {
                    throw new ArgumentException(MusicTransportReply.OutOfRange(args.Track, names.Count));
                }

                if (!PlayStep(args.Action, args.Track))
                {
                    throw new InvalidOperationException("the chosen track could not be played; see the log");
                }

                message = MusicTransportReply.Changed(names, CurrentNumber);
                break;
        }

        var tracks = new JsonArray();
        foreach (var name in names)
        {
            tracks.Add(name);
        }

        return new JsonObject { ["message"] = message, ["playlist"] = true, ["count"] = names.Count, ["current"] = CurrentNumber, ["tracks"] = tracks };
    }

    // Moves on to the next clip when the looping level or radio clip wraps round to its start.
    public static void Tick()
    {
        if (!CustomLevelState.IsActive)
        {
            if (_track != null || _runtime != null) Clear();
            return;
        }

        if ((_radio == null && _runtime == null) || !_playingOurs)
        {
            return;
        }

        try
        {
            var source = MusicController.Instance?.musicSource;
            if (source == null || !source.isPlaying)
            {
                return;
            }

            var time = source.time;
            var wrapped = RadioPlaylist.LoopWrapped(_lastTime, time);
            _lastTime = time;
            if (wrapped)
            {
                _logger?.Msg("Radio: clip ended, moving to the next.");
                PlayNext();
            }
        }
        catch (Exception ex)
        {
            FallBack(ex);
        }
    }

    private static void FallBack(Exception ex)
    {
        ReleasePlayback();
        _logger?.Warning($"Music: playback failed: {ex.Message}; using the stock music.");
        try
        {
            MusicController.Instance?.PlayStageMusic();
        }
        catch (Exception stockError)
        {
            _logger?.Warning($"Music: could not resume stock music: {stockError.Message}.");
        }
    }

    // The stock interaction is single-use; custom playlists must remain pressable.
    [HarmonyPatch(typeof(InteractableBoombox), nameof(InteractableBoombox.Interact))]
    private static class BoomboxInteractPrefix
    {
        private static bool Prefix(ref bool __result)
        {
            if ((_radio == null && _runtime == null) || !CustomLevelState.IsActive)
            {
                return true;
            }

            try
            {
                if (!PlayNext())
                {
                    return true;
                }

                __result = true;
                return false;
            }
            catch (Exception ex)
            {
                if (_runtime != null)
                {
                    FallBack(ex);
                    __result = true;
                    return false;
                }

                _logger?.Warning($"Radio: could not play the next clip: {ex.Message}; using the stock audio.");
                return true;
            }
        }
    }

    [HarmonyPatch(typeof(MusicController), nameof(MusicController.OnMainMenu))]
    private static class OnMainMenuPrefix
    {
        private static void Prefix() => Clear();
    }

    [HarmonyPatch(typeof(MusicUtility), nameof(MusicUtility.GetMusicTrackToPlay))]
    private static class GetMusicTrackToPlayPrefix
    {
        private static bool Prefix(ref MusicTrack __result)
        {
            if (_track == null || !CustomLevelState.IsActive)
            {
                return true;
            }

            if (_runtime != null && _runtimeNeedsReload)
            {
                try
                {
                    var name = _track.trackName;
                    _runtime.Select(name, track => _track = track.Track);
                    _radioTrack = IntPtr.Zero;
                    _runtimeNeedsReload = false;
                    _logger?.Msg($"Music: rebuilt runtime track '{name}' after external playback.");
                }
                catch (Exception ex)
                {
                    ReleasePlayback();
                    _logger?.Warning($"Music: could not rebuild runtime track: {ex.Message}; using the stock music.");
                    return true;
                }
            }

            __result = _track;
            return false;
        }
    }

    [HarmonyPatch(typeof(MusicController), nameof(MusicController.PlayMusicTrack))]
    private static class PlayMusicTrackPostfix
    {
        private static void Postfix(MusicController __instance, MusicTrack musicTrack)
        {
            _playingOurs = _track != null && musicTrack != null && (musicTrack.Pointer == _track.Pointer || musicTrack.Pointer == _radioTrack);
            if (_runtime != null) _runtimeNeedsReload = !_playingOurs;
            _lastTime = 0f;
            if (!_playingOurs || musicTrack.Pointer != _track.Pointer)
            {
                return;
            }

            var source = __instance.musicSource;
            _logger?.Msg($"Music: handed '{musicTrack.trackName}' to the music source, isPlaying={source.isPlaying}.");
        }
    }
}
