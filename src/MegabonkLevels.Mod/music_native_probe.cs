using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json.Nodes;
using System.Threading;
using Il2CppInterop.Runtime;

namespace MegabonkLevels;

internal static class MusicNativeProbe
{
    private const string Tone = "<native-probe-tone>";
    private static RuntimeMusicOwner<RuntimeMusicTrack> _owner;

    private static RuntimeMusicOwner<RuntimeMusicTrack> CreateOwner() => new(
        (path, token) => path == Tone ? CreateTone(token) : Mp3Decoder.Decode(path, token),
        (path, audio) => new RuntimeMusicTrack(path == Tone ? "runtime-native-tone" : Path.GetFileNameWithoutExtension(path), audio),
        track => track.Dispose());

    internal static JsonObject PlayTone(ModLogger logger)
        => Play(Tone, logger);

    internal static JsonObject PlayFile(string path, ModLogger logger)
        => Play(path, logger);

    private static PcmAudio CreateTone(CancellationToken cancellation)
    {
        const int rate = 44100;
        var position = 0;
        return PcmAudio.Read(1, rate, (buffer, count) =>
        {
            var read = Math.Min(count, rate * 2 - position);
            for (var j = 0; j < read; j++)
            {
                var i = position + j;
                var envelope = Math.Min(1d, Math.Min(i, rate * 2 - 1 - i) / 441d);
                buffer[j] = (float)(0.12d * envelope * Math.Sin(2d * Math.PI * 440d * i / rate));
            }

            position += read;
            return read;
        }, cancellation);
    }

    private static JsonObject Play(string path, ModLogger logger)
    {
        try
        {
            RuntimeAudioClip.EnsureSupported();
            var controller = MusicController.Instance;
            if (controller?.musicSource == null)
            {
                throw new InvalidOperationException("start a run before the native clip probe");
            }

            _owner ??= CreateOwner();
            _owner.Switch(path, track => track.Play());
            var current = _owner.Current;
            logger.Msg($"MusicNativeProbe: playing normal MusicTrack, {current.Clip.length:F3}s; PCM roundtrip error {current.RoundtripMaxError}.");
            return new JsonObject
            {
                ["action"] = "native-play",
                ["length"] = current.Clip.length,
                ["sampleRate"] = current.SampleRate,
                ["channels"] = current.Channels,
                ["frames"] = current.Frames,
                ["roundtripMaxError"] = current.RoundtripMaxError,
                ["sourceIsPlaying"] = controller.musicSource.isPlaying,
                ["sourceClip"] = controller.musicSource.clip?.name,
            };
        }
        catch (Exception ex)
        {
            logger.Warning($"MusicNativeProbe: {ex.GetType().Name}: {ex.Message}");
            return new JsonObject { ["action"] = "native-play", ["error"] = ex.Message };
        }
    }

    internal static void ReleaseIfInactive()
    {
        var current = _owner?.Current;
        var controller = MusicController.Instance;
        if (current == null || (controller != null && controller.currentTrack == current.Track))
        {
            return;
        }

        _owner.Dispose();
        _owner = null;
    }

    internal static JsonObject Inspect()
    {
        var calls = new JsonArray();
        foreach (var name in new[] { "Construct_Internal_Injected", "CreateUserSound_Injected", "SetData_Injected", "GetData_Injected" })
        {
            var address = IL2CPP.il2cpp_resolve_icall($"UnityEngine.AudioClip::{name}");
            var call = new JsonObject { ["name"] = name, ["address"] = $"0x{address.ToInt64():X}" };
            if (address != IntPtr.Zero)
            {
                foreach (ProcessModule module in Process.GetCurrentProcess().Modules)
                {
                    var offset = address.ToInt64() - module.BaseAddress.ToInt64();
                    if (offset >= 0 && offset < module.ModuleMemorySize)
                    {
                        call["module"] = module.ModuleName;
                        call["rva"] = $"0x{offset:X}";
                        break;
                    }
                }

                var bytes = new byte[96];
                Marshal.Copy(address, bytes, 0, bytes.Length);
                call["code"] = Convert.ToHexString(bytes);
            }

            calls.Add(call);
        }

        return new JsonObject { ["action"] = "native-info", ["calls"] = calls };
    }
}
