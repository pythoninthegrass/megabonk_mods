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

    // The level's music reference as loaded, kept so an editor save writes it back.
    public static string Reference { get; private set; }

    // Resolves the level's clip and builds the replacement track; any failure warns and leaves the stock music.
    public static void Prepare(string reference, MelonLogger.Instance logger)
    {
        Reference = reference;
        _logger = logger;
        _track = null;
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

            _track = ScriptableObject.CreateInstance(Il2CppType.Of<MusicTrack>()).Cast<MusicTrack>();
            _track.hideFlags = HideFlags.HideAndDontSave;
            _track.trackName = clip.name;
            _track.loop = clip;
            logger.Msg($"Music: using clip '{clip.name}' from pack '{parsed.Pack}' ({clip.length:F0}s).");
        }
        catch (Exception ex)
        {
            _track = null;
            logger.Warning($"Music: could not prepare '{reference}': {ex.Message}; using the stock music.");
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
            if (_track == null || musicTrack == null || musicTrack.Pointer != _track.Pointer)
            {
                return;
            }

            var source = __instance.musicSource;
            _logger?.Msg($"Music: handed '{musicTrack.trackName}' to the music source, isPlaying={source.isPlaying}.");
        }
    }
}
