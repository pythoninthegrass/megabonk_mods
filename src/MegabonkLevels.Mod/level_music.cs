using System;
using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Audio.Music;
using Il2CppInterop.Runtime;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Replaces the stock stage music with the level's pack AudioClip for custom runs; see docs/music.md.
public static class LevelMusic
{
    private static MusicTrack _track;
    private static MelonLogger.Instance _logger;
    private static string _pack;
    private static RadioPlaylist _radio;
    private static IntPtr _radioTrack;
    private static bool _playingOurs;
    private static float _lastTime;

    // The level's music reference as loaded, kept so an editor save writes it back.
    public static string Reference { get; private set; }

    // Resolves the level's clip and builds the replacement track; any failure warns and leaves the stock music.
    public static void Prepare(string reference, MelonLogger.Instance logger)
    {
        Reference = reference;
        _logger = logger;
        _track = null;
        _pack = null;
        _radio = null;
        if (reference == null)
        {
            return;
        }

        try
        {
            if (!LevelMusicReference.TryParse(reference, out var parsed))
            {
                logger.Warning($"Music: '{reference}' is not a bundle:<pack>/<clip> id; using the stock music.");
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
            _track = null;
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

    // Plays the next soundtrack clip as the level music; false when there is nothing to play.
    private static bool PlayNext()
    {
        var name = _radio.Next();
        var clip = name == null ? null : PackPrefabs.ResolveClip(_pack, name);
        if (clip == null)
        {
            _logger?.Warning($"Radio: no playable clip '{name}' in pack '{_pack}'.");
            return false;
        }

        var track = BuildTrack(clip);
        _radioTrack = track.Pointer;
        MusicController.Instance.PlayMusicTrack(track);
        _lastTime = 0f;
        _logger?.Msg($"Radio: playing '{clip.name}'.");
        return true;
    }

    // Moves on to the next clip when the looping level or radio clip wraps round to its start.
    public static void Tick()
    {
        if (_radio == null || !_playingOurs || !CustomLevelState.IsActive)
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
            _playingOurs = false;
            _logger?.Warning($"Radio: could not follow the clip's end: {ex.Message}.");
        }
    }

    // Replaces the stock boombox interaction, which is single-use and throws when repeated, with playing the next soundtrack clip as the level music; any failure runs the stock interaction.
    [HarmonyPatch(typeof(InteractableBoombox), nameof(InteractableBoombox.Interact))]
    private static class BoomboxInteractPrefix
    {
        private static bool Prefix(ref bool __result)
        {
            if (_radio == null || !CustomLevelState.IsActive)
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
                _logger?.Warning($"Radio: could not play the next clip: {ex.Message}; using the stock audio.");
                return true;
            }
        }
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
