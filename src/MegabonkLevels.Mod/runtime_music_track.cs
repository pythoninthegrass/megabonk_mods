using System;
using Assets.Scripts.Audio.Music;
using Il2CppInterop.Runtime;
using UnityEngine;

namespace MegabonkLevels;

// Owns runtime-created objects only; construct, play and dispose on the game thread.
internal sealed class RuntimeMusicTrack : IDisposable
{
    internal AudioClip Clip { get; private set; }
    internal MusicTrack Track { get; private set; }
    internal int Channels { get; }
    internal int SampleRate { get; }
    internal int Frames { get; }
    internal float RoundtripMaxError { get; }

    internal RuntimeMusicTrack(string name, PcmAudio audio)
    {
        Channels = audio.Channels;
        SampleRate = audio.SampleRate;
        Frames = audio.Frames;
        Clip = RuntimeAudioClip.Create(name, audio, out var error);
        RoundtripMaxError = error;
        try
        {
            Track = ScriptableObject.CreateInstance(Il2CppType.Of<MusicTrack>()).Cast<MusicTrack>();
            Track.hideFlags = HideFlags.HideAndDontSave;
            Track.trackName = name;
            Track.loop = Clip;
        }
        catch
        {
            Dispose();
            throw;
        }
    }

    internal void Play()
    {
        if (Track == null)
        {
            throw new ObjectDisposedException(nameof(RuntimeMusicTrack));
        }

        var controller = MusicController.Instance;
        if (controller?.musicSource == null)
        {
            throw new InvalidOperationException("No MusicController music source in the scene.");
        }

        controller.PlayMusicTrack(Track);
    }

    public void Dispose()
    {
        var controller = MusicController.Instance;
        var source = controller?.musicSource;
        if (Clip != null && source != null && source.clip == Clip)
        {
            source.Stop();
            source.clip = null;
        }

        if (Track != null && controller != null && controller.currentTrack == Track)
        {
            controller.currentTrack = null;
        }

        if (Track != null)
        {
            Track.loop = null;
            UnityEngine.Object.Destroy(Track);
            Track = null;
        }

        if (Clip != null)
        {
            UnityEngine.Object.Destroy(Clip);
            Clip = null;
        }
    }
}
