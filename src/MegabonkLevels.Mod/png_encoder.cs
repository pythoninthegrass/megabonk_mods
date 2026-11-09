using System;
using System.Buffers.Binary;
using System.IO;
using System.IO.Compression;

namespace MegabonkLevels;

// Minimal 8-bit RGB PNG writer; Il2CppInterop cannot marshal ImageConversion.EncodeToPNG's byte[] result.
public static class PngEncoder
{
    private static readonly byte[] Signature = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A };
    private static readonly uint[] CrcTable = BuildCrcTable();

    // bottomUpRgb holds width*height*3 bytes with the bottom row first, matching Unity's texture layout.
    public static byte[] EncodeRgb(int width, int height, byte[] bottomUpRgb)
    {
        if (width <= 0 || height <= 0)
        {
            throw new ArgumentException($"invalid dimensions {width}x{height}");
        }

        var rowBytes = width * 3;
        if (bottomUpRgb.Length != rowBytes * height)
        {
            throw new ArgumentException($"expected {rowBytes * height} bytes for {width}x{height} RGB, got {bottomUpRgb.Length}");
        }

        var header = new byte[13];
        BinaryPrimitives.WriteInt32BigEndian(header.AsSpan(0, 4), width);
        BinaryPrimitives.WriteInt32BigEndian(header.AsSpan(4, 4), height);
        header[8] = 8; // bit depth
        header[9] = 2; // color type: RGB

        using var output = new MemoryStream();
        output.Write(Signature, 0, Signature.Length);
        WriteChunk(output, "IHDR", header);
        WriteChunk(output, "IDAT", CompressScanlines(width, height, bottomUpRgb));
        WriteChunk(output, "IEND", Array.Empty<byte>());
        return output.ToArray();
    }

    private static byte[] CompressScanlines(int width, int height, byte[] bottomUpRgb)
    {
        var rowBytes = width * 3;
        using var compressed = new MemoryStream();
        using (var zlib = new ZLibStream(compressed, CompressionLevel.Fastest, leaveOpen: true))
        {
            for (var row = height - 1; row >= 0; row--)
            {
                zlib.WriteByte(0); // filter type: none
                zlib.Write(bottomUpRgb, row * rowBytes, rowBytes);
            }
        }
        return compressed.ToArray();
    }

    private static void WriteChunk(Stream output, string type, byte[] data)
    {
        var typeBytes = System.Text.Encoding.ASCII.GetBytes(type);
        var buffer = new byte[4];

        BinaryPrimitives.WriteInt32BigEndian(buffer, data.Length);
        output.Write(buffer, 0, 4);
        output.Write(typeBytes, 0, 4);
        output.Write(data, 0, data.Length);

        var crc = 0xFFFFFFFFu;
        crc = UpdateCrc(crc, typeBytes);
        crc = UpdateCrc(crc, data);
        BinaryPrimitives.WriteUInt32BigEndian(buffer, crc ^ 0xFFFFFFFFu);
        output.Write(buffer, 0, 4);
    }

    private static uint UpdateCrc(uint crc, byte[] bytes)
    {
        foreach (var b in bytes)
        {
            crc = CrcTable[(crc ^ b) & 0xFF] ^ (crc >> 8);
        }
        return crc;
    }

    private static uint[] BuildCrcTable()
    {
        var table = new uint[256];
        for (uint n = 0; n < 256; n++)
        {
            var c = n;
            for (var k = 0; k < 8; k++)
            {
                c = (c & 1) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            }
            table[n] = c;
        }
        return table;
    }
}
