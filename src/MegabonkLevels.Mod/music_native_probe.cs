using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json.Nodes;
using Il2CppInterop.Runtime;
using Il2Cpp;
using Il2CppAssets.Scripts.Audio.Music;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

internal static class MusicNativeProbe
{
    private static AudioClip _clip;
    private static MusicTrack _track;

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeSpan
    {
        public IntPtr Begin;
        public int Length;
    }

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void CreateSound(IntPtr clip, ref NativeSpan name, int frames, int channels, int rate, byte stream);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate byte TransferData(IntPtr clip, ref NativeSpan data, int offset);

    internal static JsonObject PlayTone(MelonLogger.Instance logger)
    {
        const int rate = 44100;
        var pcm = new float[rate * 2];
        for (var i = 0; i < pcm.Length; i++)
        {
            var envelope = Math.Min(1d, Math.Min(i, pcm.Length - 1 - i) / 441d);
            pcm[i] = (float)(0.12d * envelope * Math.Sin(2d * Math.PI * 440d * i / rate));
        }

        return Play(pcm, 1, rate, logger);
    }

    internal static JsonObject Play(float[] pcm, int channels, int rate, MelonLogger.Instance logger)
    {
        AudioClip clip = null;
        try
        {
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows) || IntPtr.Size != 8)
            {
                throw new PlatformNotSupportedException("native clip probe ABI is verified only on the Win64 player; inspect the native platform first");
            }

            if (pcm.Length == 0 || channels <= 0 || pcm.Length % channels != 0 || rate <= 0)
            {
                throw new ArgumentException("invalid PCM dimensions");
            }

            var controller = MusicController.Instance;
            if (controller?.musicSource == null)
            {
                throw new InvalidOperationException("start a run before the native clip probe");
            }

            var create = Resolve<CreateSound>("CreateUserSound_Injected");
            var write = Resolve<TransferData>("SetData_Injected");
            var read = Resolve<TransferData>("GetData_Injected");
            logger.Msg("MusicNativeProbe: constructing clip through Unity's GC-handle unmarshaller.");
            clip = AudioClip.Construct_Internal();
            var native = clip?.m_CachedPtr ?? IntPtr.Zero;
            if (native == IntPtr.Zero)
            {
                throw new InvalidOperationException("clip construction returned no native object");
            }

            logger.Msg($"MusicNativeProbe: native clip 0x{native.ToInt64():X}; creating {pcm.Length / channels} frames.");
            var name = "runtime-mp3-native-probe".ToCharArray();
            WithPinned(name, name.Length, (ref NativeSpan span) => create(native, ref span, pcm.Length / channels, channels, rate, 0));
            logger.Msg("MusicNativeProbe: writing PCM.");
            WithPinned(pcm, pcm.Length, (ref NativeSpan span) =>
            {
                if (write(native, ref span, 0) == 0)
                {
                    throw new InvalidOperationException("native SetData returned false");
                }
            });

            var check = new float[Math.Min(pcm.Length, 4096 * channels)];
            WithPinned(check, check.Length, (ref NativeSpan span) =>
            {
                if (read(native, ref span, 0) == 0)
                {
                    throw new InvalidOperationException("native GetData returned false");
                }
            });
            var maxError = 0f;
            for (var i = 0; i < check.Length; i++)
            {
                maxError = Math.Max(maxError, Math.Abs(check[i] - pcm[i]));
            }

            if (maxError > 0.0001f)
            {
                throw new InvalidOperationException($"PCM roundtrip mismatch: {maxError}");
            }

            var track = ScriptableObject.CreateInstance(Il2CppType.Of<MusicTrack>()).Cast<MusicTrack>();
            track.hideFlags = HideFlags.HideAndDontSave;
            track.trackName = "Runtime native clip probe";
            track.loop = clip;
            var oldClip = _clip;
            var oldTrack = _track;
            controller.PlayMusicTrack(track);
            _clip = clip;
            _track = track;
            if (oldTrack != null)
            {
                UnityEngine.Object.Destroy(oldTrack);
            }

            if (oldClip != null)
            {
                UnityEngine.Object.Destroy(oldClip);
            }

            logger.Msg($"MusicNativeProbe: playing normal MusicTrack, {clip.length:F3}s; PCM roundtrip error {maxError}.");
            return new JsonObject
            {
                ["action"] = "native-play",
                ["length"] = clip.length,
                ["sampleRate"] = rate,
                ["channels"] = channels,
                ["frames"] = pcm.Length / channels,
                ["roundtripMaxError"] = maxError,
                ["sourceIsPlaying"] = controller.musicSource.isPlaying,
                ["sourceClip"] = controller.musicSource.clip?.name,
            };
        }
        catch (Exception ex)
        {
            logger.Warning($"MusicNativeProbe: {ex.GetType().Name}: {ex.Message}");
            if (clip != null && clip != _clip)
            {
                UnityEngine.Object.Destroy(clip);
            }

            return new JsonObject { ["action"] = "native-play", ["error"] = ex.Message };
        }
    }

    private delegate void PinnedAction(ref NativeSpan span);

    private static void WithPinned(Array data, int length, PinnedAction action)
    {
        var handle = GCHandle.Alloc(data, GCHandleType.Pinned);
        try
        {
            var span = new NativeSpan { Begin = handle.AddrOfPinnedObject(), Length = length };
            action(ref span);
        }
        finally
        {
            handle.Free();
        }
    }

    private static T Resolve<T>(string name) where T : Delegate
    {
        var address = IL2CPP.il2cpp_resolve_icall($"UnityEngine.AudioClip::{name}");
        return address == IntPtr.Zero
            ? throw new MissingMethodException(name)
            : Marshal.GetDelegateForFunctionPointer<T>(address);
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
