using System;
using System.Runtime.InteropServices;
using Il2CppInterop.Runtime;
using UnityEngine;

namespace MegabonkLevels;

internal static class RuntimeAudioClip
{
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

    internal static AudioClip Create(string name, PcmAudio audio, out float roundtripMaxError)
    {
        EnsureSupported();

        AudioClip clip = null;
        try
        {
            var create = Resolve<CreateSound>("CreateUserSound_Injected");
            var write = Resolve<TransferData>("SetData_Injected");
            var read = Resolve<TransferData>("GetData_Injected");
            clip = AudioClip.Construct_Internal();
            var native = clip?.m_CachedPtr ?? IntPtr.Zero;
            if (native == IntPtr.Zero)
            {
                throw new InvalidOperationException("Clip construction returned no native object.");
            }

            var chars = name.ToCharArray();
            WithPinned(chars, chars.Length, (ref NativeSpan span) => create(native, ref span, audio.Frames, audio.Channels, audio.SampleRate, 0));
            roundtripMaxError = 0f;
            var offset = 0;
            var check = new float[PcmAudio.BlockSamples];
            foreach (var block in audio.Blocks)
            {
                WithPinned(block, block.Length, (ref NativeSpan span) =>
                {
                    if (write(native, ref span, offset) == 0)
                    {
                        throw new InvalidOperationException("Native SetData returned false.");
                    }
                });

                WithPinned(check, block.Length, (ref NativeSpan span) =>
                {
                    if (read(native, ref span, offset) == 0)
                    {
                        throw new InvalidOperationException("Native GetData returned false.");
                    }
                });
                for (var i = 0; i < block.Length; i++)
                {
                    var error = Math.Abs(check[i] - block[i]);
                    if (!float.IsFinite(check[i]) || error > 0.0001f)
                    {
                        throw new InvalidOperationException($"PCM roundtrip mismatch at frame {offset}: {error}.");
                    }

                    roundtripMaxError = Math.Max(roundtripMaxError, error);
                }

                offset += block.Length / audio.Channels;
            }

            clip.hideFlags = HideFlags.HideAndDontSave;
            return clip;
        }
        catch
        {
            if (clip != null)
            {
                UnityEngine.Object.Destroy(clip);
            }

            throw;
        }
    }

    internal static void EnsureSupported()
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows) || IntPtr.Size != 8)
        {
            throw new PlatformNotSupportedException("Native clip ABI is verified only on the Win64 player; inspect the native platform first.");
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
}
