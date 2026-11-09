using System;
using System.Runtime.InteropServices;
using Il2CppInterop.Runtime;
using UnityEngine;

namespace MegabonkLevels;

// Decodes png/jpg bytes through Unity's native icall, because the generated ImageConversion.LoadImage wrapper throws in Il2CppSystem.Span.
public static class NativeImageLoader
{
    private const int SpanWrapperSize = 16;
    private const int CachedPtrOffset = 0x10;

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate byte LoadImageInjected(IntPtr texture, IntPtr spanWrapper, byte markNonReadable);

    private static LoadImageInjected _loadImage;

    public static bool LoadImage(Texture2D texture, byte[] data)
    {
        _loadImage ??= IL2CPP.ResolveICall<LoadImageInjected>("UnityEngine.ImageConversion::LoadImage_Injected");
        var handle = GCHandle.Alloc(data, GCHandleType.Pinned);
        var span = Marshal.AllocHGlobal(SpanWrapperSize);
        try
        {
            Marshal.WriteIntPtr(span, 0, handle.AddrOfPinnedObject());
            Marshal.WriteInt32(span, 8, data.Length);
            var nativeTexture = Marshal.ReadIntPtr(texture.Pointer, CachedPtrOffset);
            return nativeTexture != IntPtr.Zero && _loadImage(nativeTexture, span, 0) != 0;
        }
        finally
        {
            Marshal.FreeHGlobal(span);
            handle.Free();
        }
    }
}
