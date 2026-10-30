using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json.Nodes;
using System.Threading;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime.Injection;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;
using MelonLoader.Utils;
using NLayer;
using UnityEngine;

namespace MegabonkLevels;

// TASK-024.01 spike: decode an mp3 with a managed decoder and push its PCM through the game's music AudioSource.
public static class MusicProbe
{
    private static readonly float[] ReadBuffer = new float[8192];

    private static float[] _pcm;
    private static int _sourceChannels = 2;
    private static int _sourceRate;
    private static long _frames;
    private static long _frame;
    private static long _fillCalls;
    private static long _fillTicks;
    private static volatile bool _playing;
    private static string _loaded;
    private static string _error;
    private static int _decodeMs;
    private static float _peak;
    private static bool _structRegistered;
    private static bool _managedRegistered;
    private static bool _attached;
    private static bool _useStructArray = true;
    private static MonoBehaviour _filter;
    private static float? _heldPitch;
    private static float? _heldCutoff;

    public static JsonObject Run(string action, string path, string variant, float? value, MelonLogger.Instance logger)
    {
        _useStructArray = variant != "managed";
        switch (action)
        {
            case "decode":
                return Decode(path, logger);
            case "native-info":
                return MusicNativeProbe.Inspect();
            case "native-tone":
                Detach(logger);
                return MusicNativeProbe.PlayTone(logger);
            case "native-play":
                Detach(logger);
                return Play(path, logger, native: true);
            case "play":
                return Play(path, logger);
            case "stop":
                _playing = false;
                logger.Msg("MusicProbe: playback stopped, the stock clip plays again.");
                return Status();
            case "restart":
                return Restart(path, logger);
            case "duck":
                return SetDuck(logger, value);
            case "unduck":
                return SetDuck(logger, 1f);
            case "pause":
                return SetSourcePaused(true, logger);
            case "unpause":
                return SetSourcePaused(false, logger);
            case "pitch":
                return SetSourcePitch(value, logger);
            case "lowpass":
                return SetLowpass(value, logger);
            case "mute":
                return SetStockMuted(true, logger);
            case "unmute":
                return SetStockMuted(false, logger);
            case "clip-null":
                return ClearStockClip(logger);
            case "detach":
                return Detach(logger);
            default:
                return Status();
        }
    }

    // Reads the whole file to float PCM on the calling thread and reports what the decoder saw.
    private static JsonObject Decode(string path, MelonLogger.Instance logger)
    {
        var file = Resolve(path);
        if (file == null)
        {
            return Fail($"no readable mp3 at '{path}'");
        }

        var watch = Stopwatch.StartNew();
        try
        {
            using var mpeg = new MpegFile(file);
            var samples = 0L;
            var peak = 0f;
            while (true)
            {
                var read = mpeg.ReadSamples(ReadBuffer, 0, ReadBuffer.Length);
                if (read <= 0)
                {
                    break;
                }

                for (var i = 0; i < read; i++)
                {
                    var magnitude = Math.Abs(ReadBuffer[i]);
                    if (magnitude > peak)
                    {
                        peak = magnitude;
                    }
                }

                samples += read;
            }

            watch.Stop();
            logger.Msg($"MusicProbe: decoded '{Path.GetFileName(file)}': {mpeg.SampleRate} Hz, {mpeg.Channels} ch, {samples} samples, {mpeg.Duration.TotalSeconds:F1}s in {watch.ElapsedMilliseconds} ms, peak {peak:F3}.");
            return new JsonObject
            {
                { "action", "decode" },
                { "file", Path.GetFileName(file) },
                { "sampleRate", mpeg.SampleRate },
                { "channels", mpeg.Channels },
                { "samples", samples },
                { "durationSec", Math.Round(mpeg.Duration.TotalSeconds, 2) },
                { "decodeMs", (int)watch.ElapsedMilliseconds },
                { "peak", Math.Round(peak, 4) },
            };
        }
        catch (Exception ex)
        {
            logger.Warning($"MusicProbe: decode of '{file}' failed: {ex.GetType().Name}: {ex.Message}");
            return Fail($"decode failed: {ex.GetType().Name}: {ex.Message}");
        }
    }

    private static JsonObject Play(string path, MelonLogger.Instance logger, bool native = false)
    {
        var file = Resolve(path ?? _loaded);
        if (file == null)
        {
            return Fail($"no readable mp3 at '{path}'");
        }

        if (native)
        {
            var decodeWatch = Stopwatch.StartNew();
            var result = MusicNativeProbe.PlayFile(file, logger);
            _error = result["error"]?.GetValue<string>();
            if (_error == null)
            {
                _loaded = file;
                _pcm = null;
                _sourceChannels = result["channels"].GetValue<int>();
                _sourceRate = result["sampleRate"].GetValue<int>();
                _frames = result["frames"].GetValue<int>();
                _decodeMs = (int)decodeWatch.ElapsedMilliseconds;
            }

            return result;
        }

        float[] pcm;
        int channels;
        int rate;
        var watch = Stopwatch.StartNew();
        try
        {
            using var mpeg = new MpegFile(file);
            channels = mpeg.Channels;
            rate = mpeg.SampleRate;
            var collected = new List<float>();
            while (true)
            {
                var read = mpeg.ReadSamples(ReadBuffer, 0, ReadBuffer.Length);
                if (read <= 0)
                {
                    break;
                }

                for (var i = 0; i < read; i++)
                {
                    collected.Add(ReadBuffer[i]);
                }
            }

            pcm = collected.ToArray();
        }
        catch (Exception ex)
        {
            _error = $"decode failed: {ex.GetType().Name}: {ex.Message}";
            logger.Warning($"MusicProbe: {_error} for '{file}'");
            return Fail(_error);
        }

        watch.Stop();
        if (channels <= 0 || pcm.Length % channels != 0)
        {
            return Fail($"decoder produced {pcm.Length} samples for {channels} channel(s)");
        }

        _pcm = pcm;
        _sourceChannels = channels;
        _sourceRate = rate;
        _frames = pcm.Length / channels;
        _decodeMs = (int)watch.ElapsedMilliseconds;
        _loaded = file;
        _error = null;

        if (!Attach(logger))
        {
            return Fail("no MusicController music source in the scene to attach to");
        }

        _frame = 0;
        _fillCalls = 0;
        _fillTicks = 0;
        _peak = 0f;
        _playing = true;
        logger.Msg($"MusicProbe: playing '{Path.GetFileName(file)}' through OnAudioFilterRead ({rate} Hz, {channels} ch, {_frames} frames, decoded in {_decodeMs} ms).");
        return Status();
    }

    // Forces the game's own duck value, which MusicPauseZone drives, to see whether it reaches the injected samples.
    private static JsonObject SetDuck(MelonLogger.Instance logger, float? value = null)
    {
        var controller = MusicController.Instance;
        if (controller == null)
        {
            return Fail("no MusicController in the scene");
        }

        try
        {
            controller.desiredVolumeMultiplier = value ?? 0.2f;
            controller.volumeMultiplier = value ?? 0.2f;
        }
        catch (Exception ex)
        {
            return Fail($"duck threw: {ex.GetType().Name}: {ex.Message}");
        }

        logger.Msg($"MusicProbe: music duck set to {value ?? 0.2f}.");
        return Status();
    }

    private static JsonObject SetSourcePaused(bool paused, MelonLogger.Instance logger)
    {
        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            return Fail("no MusicController music source in the scene");
        }

        try
        {
            if (paused)
            {
                source.Pause();
            }
            else
            {
                source.UnPause();
            }
        }
        catch (Exception ex)
        {
            return Fail($"{(paused ? "Pause" : "UnPause")} threw: {ex.GetType().Name}: {ex.Message}");
        }

        logger.Msg($"MusicProbe: music source {(paused ? "paused" : "unpaused")}.");
        return Status();
    }

    // Restarts the stock clip for comparison; attaching the filter does not require a restart.
    private static JsonObject Restart(string path, MelonLogger.Instance logger)
    {
        if (path != null)
        {
            var played = Play(path, logger);
            if (played["error"] != null)
            {
                return played;
            }
        }

        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            return Fail("no MusicController music source in the scene");
        }

        if (!Attach(logger))
        {
            return Fail("no MusicController music source in the scene to attach to");
        }

        try
        {
            source.Stop();
            source.Play();
        }
        catch (Exception ex)
        {
            logger.Warning($"MusicProbe: restarting the music source threw: {ex.Message}");
            return Fail($"restart threw: {ex.GetType().Name}: {ex.Message}");
        }

        _frame = 0;
        _fillCalls = 0;
        _fillTicks = 0;
        _peak = 0f;
        _playing = true;
        logger.Msg("MusicProbe: music source restarted with the filter attached.");
        return Status();
    }

    private static JsonObject SetStockMuted(bool muted, MelonLogger.Instance logger)
    {
        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            return Fail("no MusicController music source in the scene");
        }

        try
        {
            source.mute = muted;
        }
        catch (Exception ex)
        {
            return Fail($"mute threw: {ex.GetType().Name}: {ex.Message}");
        }

        logger.Msg($"MusicProbe: stock music source mute set to {muted}.");
        return Status();
    }

    private static JsonObject ClearStockClip(MelonLogger.Instance logger)
    {
        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            return Fail("no MusicController music source in the scene");
        }

        try
        {
            source.clip = null;
        }
        catch (Exception ex)
        {
            return Fail($"clearing the clip threw: {ex.GetType().Name}: {ex.Message}");
        }

        logger.Msg("MusicProbe: stock music clip cleared.");
        return Status();
    }

    // Holds the requested pitch after the game's update; omit the value to release the override.
    private static JsonObject SetSourcePitch(float? pitch, MelonLogger.Instance logger)
    {
        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            return Fail("no MusicController music source in the scene");
        }

        var target = pitch ?? 1f;
        try
        {
            _heldPitch = pitch;
            source.pitch = target;
        }
        catch (Exception ex)
        {
            return Fail($"setting pitch threw: {ex.GetType().Name}: {ex.Message}");
        }

        logger.Msg($"MusicProbe: music source pitch set to {target}.");
        return Status();
    }

    // Holds the source filter independently of the mixer's low-pass parameter; omit the value to release it.
    private static JsonObject SetLowpass(float? cutoff, MelonLogger.Instance logger)
    {
        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            return Fail("no MusicController music source in the scene");
        }

        AudioLowPassFilter filter;
        try
        {
            filter = source.gameObject.GetComponent<AudioLowPassFilter>();
        }
        catch (Exception ex)
        {
            return Fail($"looking up the lowpass filter threw: {ex.GetType().Name}: {ex.Message}");
        }

        if (filter == null)
        {
            return Fail("the music source object has no AudioLowPassFilter");
        }

        var target = cutoff ?? 22000f;
        try
        {
            _heldCutoff = cutoff;
            filter.cutoffFrequency = target;
        }
        catch (Exception ex)
        {
            return Fail($"setting cutoffFrequency threw: {ex.GetType().Name}: {ex.Message}");
        }

        logger.Msg($"MusicProbe: music lowpass cutoff set to {target} Hz.");
        return Status();
    }

    private static bool Attach(MelonLogger.Instance logger)
    {
        if (_attached && _filter != null)
        {
            return true;
        }

        var source = MusicController.Instance?.musicSource;
        if (source == null)
        {
            logger.Warning("MusicProbe: MusicController has no music source; start a run first.");
            return false;
        }

        if (_useStructArray ? !_structRegistered : !_managedRegistered)
        {
            if (_useStructArray)
            {
                ClassInjector.RegisterTypeInIl2Cpp<MusicFilterStruct>();
                _structRegistered = true;
            }
            else
            {
                ClassInjector.RegisterTypeInIl2Cpp<MusicFilter>();
                _managedRegistered = true;
            }

            logger.Msg($"MusicProbe: registered {(_useStructArray ? "MusicFilterStruct (Il2CppStructArray<float>)" : "MusicFilter (float[])")} with Il2CppInterop.");
        }

        _filter = _useStructArray
            ? source.gameObject.AddComponent<MusicFilterStruct>()
            : source.gameObject.AddComponent<MusicFilter>();
        _attached = _filter != null;
        if (!_attached)
        {
            logger.Warning("MusicProbe: AddComponent<MusicFilter> returned null.");
        }

        return _attached;
    }

    private static JsonObject Detach(MelonLogger.Instance logger)
    {
        _playing = false;
        _heldPitch = null;
        _heldCutoff = null;
        if (_filter != null)
        {
            try
            {
                UnityEngine.Object.Destroy(_filter);
            }
            catch (Exception ex)
            {
                logger.Warning($"MusicProbe: detaching the filter threw: {ex.Message}");
            }

            _filter = null;
        }

        _attached = false;
        logger.Msg("MusicProbe: filter detached.");
        return Status();
    }

    [HarmonyPatch(typeof(MusicController), nameof(MusicController.Update))]
    private static class HeldControlsPatch
    {
        private static void Postfix(MusicController __instance)
        {
            MusicNativeProbe.ReleaseIfInactive();
            if (_heldPitch.HasValue && __instance.musicSource != null)
            {
                __instance.musicSource.pitch = _heldPitch.Value;
            }

            if (_heldCutoff.HasValue && __instance.lowpassFilter != null)
            {
                __instance.lowpassFilter.cutoffFrequency = _heldCutoff.Value;
            }
        }
    }

    private static JsonObject Status()
    {
        var status = new JsonObject
        {
            { "action", "status" },
            { "playing", _playing },
            { "attached", _attached },
            { "file", _loaded == null ? null : Path.GetFileName(_loaded) },
            { "sampleRate", _sourceRate },
            { "channels", _sourceChannels },
            { "frames", _frames },
            { "frame", Interlocked.Read(ref _frame) },
            { "fillCalls", Interlocked.Read(ref _fillCalls) },
            { "fillMicrosecondsPerCall", FillMicrosecondsPerCall() },
            { "peak", Math.Round(_peak, 4) },
            { "decodeMs", _decodeMs },
            { "error", _error },
        };

        try
        {
            var controller = MusicController.Instance;
            var source = controller?.musicSource;
            if (source != null)
            {
                status["sourceVolume"] = Math.Round(source.volume, 3);
                status["sourceIsPlaying"] = source.isPlaying;
                status["sourcePitch"] = Math.Round(source.pitch, 3);
                status["heldPitch"] = _heldPitch;
                status["heldCutoff"] = _heldCutoff;
                status["sourceTime"] = Math.Round(source.time, 2);
                status["sourceMute"] = source.mute;
                status["sourceClip"] = source.clip?.name;
                status["volumeMultiplier"] = Math.Round(controller.volumeMultiplier, 3);
                status["desiredVolumeMultiplier"] = Math.Round(controller.desiredVolumeMultiplier, 3);
                status["stockTrack"] = controller.currentTrack?.trackName;
                var lowpass = source.gameObject.GetComponent<AudioLowPassFilter>();
                if (lowpass != null)
                {
                    status["lowpassCutoff"] = Math.Round(lowpass.cutoffFrequency, 1);
                }

                var components = new JsonArray();
                foreach (var component in source.gameObject.GetComponents<Component>())
                {
                    components.Add(component ? component.GetType().Name : null);
                }

                status["components"] = components;
            }
        }
        catch (Exception ex)
        {
            status["probeWarning"] = ex.Message;
        }

        return status;
    }

    // Average time the audio-thread copy takes, against the ~21 ms budget of a 1024-frame buffer at 48 kHz.
    private static double FillMicrosecondsPerCall()
    {
        var calls = Interlocked.Read(ref _fillCalls);
        if (calls == 0)
        {
            return 0d;
        }

        return Math.Round(Interlocked.Read(ref _fillTicks) * 1_000_000d / calls / Stopwatch.Frequency, 1);
    }

    // Runs on Unity's audio thread: no Unity APIs, no logging, only a bounded copy and counters.
    public static void Fill(float[] data, int channels)
    {
        Interlocked.Increment(ref _fillCalls);
        FillSpan(data, channels);
    }

    // Same, for the Il2CppStructArray signature Il2CppInterop can bridge; AsSpan is a zero-copy view of Unity's buffer.
    public static void Fill(Il2CppStructArray<float> data, int channels)
    {
        Interlocked.Increment(ref _fillCalls);
        FillSpan(data.AsSpan(), channels);
    }

    private static void FillSpan(Span<float> data, int channels)
    {
        var pcm = _pcm;
        if (!_playing || pcm == null || channels <= 0 || _frames <= 0)
        {
            return;
        }

        try
        {
            var started = Stopwatch.GetTimestamp();
            var source = _sourceChannels;
            var frames = data.Length / channels;
            var start = Interlocked.Read(ref _frame);
            var peak = _peak;
            for (var f = 0; f < frames; f++)
            {
                var offset = ((start + f) % _frames) * source;
                for (var c = 0; c < channels; c++)
                {
                    var sample = c < source ? pcm[offset + c] : 0f;
                    data[(f * channels) + c] = sample;
                    var magnitude = sample < 0f ? -sample : sample;
                    if (magnitude > peak)
                    {
                        peak = magnitude;
                    }
                }
            }

            _peak = peak;
            Interlocked.Add(ref _frame, frames);
            Interlocked.Add(ref _fillTicks, Stopwatch.GetTimestamp() - started);
        }
        catch (Exception ex)
        {
            _playing = false;
            _error = $"fill failed: {ex.GetType().Name}: {ex.Message}";
        }
    }

    private static string Resolve(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        if (File.Exists(path))
        {
            return path;
        }

        foreach (var candidate in new[]
                 {
                     Path.Combine(MelonEnvironment.GameRootDirectory, path),
                     Path.Combine(MelonEnvironment.GameRootDirectory, "UserData", "CustomMusic", path),
                 })
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        return null;
    }

    private static JsonObject Fail(string message) => new() { { "error", message } };

    // The audio-thread shim Unity dispatches OnAudioFilterRead to; it holds no state of its own.
    public class MusicFilter : MonoBehaviour
    {
        public MusicFilter(IntPtr ptr) : base(ptr)
        {
        }

        // Proves Il2CppInterop dispatches Unity messages to this injected type at all; the filter runs on the audio thread.
        public void Start() => MelonLogger.Msg($"MusicProbe: MusicFilter.Start on {name} ({GetInstanceID()}).");

        public void OnAudioFilterRead(float[] data, int channels) => MusicProbe.Fill(data, channels);
    }

    // Unity only dispatches the message if Il2CppInterop generated a bridge, and it skips float[] parameters; the Il2Cpp array type bridges.
    public class MusicFilterStruct : MonoBehaviour
    {
        public MusicFilterStruct(IntPtr ptr) : base(ptr)
        {
        }

        public void Start() => MelonLogger.Msg($"MusicProbe: MusicFilterStruct.Start on {name} ({GetInstanceID()}).");

        public void OnAudioFilterRead(Il2CppStructArray<float> data, int channels) => MusicProbe.Fill(data, channels);
    }
}
