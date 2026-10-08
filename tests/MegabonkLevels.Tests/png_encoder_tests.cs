using System.Buffers.Binary;
using System.IO.Compression;

namespace MegabonkLevels.Tests;

public class PngEncoderTests
{
    private static readonly byte[] Signature = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A };

    // 2 wide x 2 tall; rows listed bottom row first, as Unity returns them.
    private static readonly byte[] BottomUpRgb =
    {
        10, 11, 12, 20, 21, 22, // bottom row
        30, 31, 32, 40, 41, 42, // top row
    };

    private static List<(string Type, byte[] Data)> ReadChunks(byte[] png)
    {
        var chunks = new List<(string, byte[])>();
        var offset = Signature.Length;
        while (offset < png.Length)
        {
            var length = BinaryPrimitives.ReadInt32BigEndian(png.AsSpan(offset, 4));
            var type = System.Text.Encoding.ASCII.GetString(png, offset + 4, 4);
            chunks.Add((type, png.AsSpan(offset + 8, length).ToArray()));
            offset += 12 + length;
        }
        return chunks;
    }

    private static byte[] Inflate(byte[] zlib)
    {
        using var input = new MemoryStream(zlib);
        using var inflater = new ZLibStream(input, CompressionMode.Decompress);
        using var output = new MemoryStream();
        inflater.CopyTo(output);
        return output.ToArray();
    }

    [Fact]
    public void EncodeRgb_StartsWithPngSignature()
    {
        var png = PngEncoder.EncodeRgb(2, 2, BottomUpRgb);

        Assert.Equal(Signature, png.Take(Signature.Length).ToArray());
    }

    [Fact]
    public void EncodeRgb_WritesHeaderForEightBitRgb()
    {
        var chunks = ReadChunks(PngEncoder.EncodeRgb(2, 2, BottomUpRgb));

        var (type, ihdr) = chunks[0];
        Assert.Equal("IHDR", type);
        Assert.Equal(2, BinaryPrimitives.ReadInt32BigEndian(ihdr.AsSpan(0, 4)));
        Assert.Equal(2, BinaryPrimitives.ReadInt32BigEndian(ihdr.AsSpan(4, 4)));
        Assert.Equal(8, ihdr[8]);
        Assert.Equal(2, ihdr[9]);
    }

    [Fact]
    public void EncodeRgb_FlipsRowsSoTopRowComesFirst()
    {
        var chunks = ReadChunks(PngEncoder.EncodeRgb(2, 2, BottomUpRgb));

        var raw = Inflate(chunks.Where(c => c.Type == "IDAT").SelectMany(c => c.Data).ToArray());

        var expected = new byte[]
        {
            0, 30, 31, 32, 40, 41, 42, // filter byte + top row
            0, 10, 11, 12, 20, 21, 22, // filter byte + bottom row
        };
        Assert.Equal(expected, raw);
    }

    [Fact]
    public void EncodeRgb_EndsWithIendChunk()
    {
        var png = PngEncoder.EncodeRgb(2, 2, BottomUpRgb);

        var iend = new byte[] { 0, 0, 0, 0, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82 };
        Assert.Equal(iend, png.TakeLast(iend.Length).ToArray());
    }

    [Fact]
    public void EncodeRgb_WritesCorrectCrcOnHeaderChunk()
    {
        var png = PngEncoder.EncodeRgb(1, 1, new byte[] { 0, 0, 0 });

        // IHDR for a 1x1 8-bit RGB image has a well-known CRC.
        var crc = BinaryPrimitives.ReadUInt32BigEndian(png.AsSpan(Signature.Length + 8 + 13, 4));
        Assert.Equal(0x907753DEu, crc);
    }

    [Theory]
    [InlineData(0, 1, 0)]
    [InlineData(1, 0, 0)]
    [InlineData(2, 2, 11)]
    public void EncodeRgb_RejectsBadDimensionsOrBufferSize(int width, int height, int length)
    {
        Assert.Throws<ArgumentException>(() => PngEncoder.EncodeRgb(width, height, new byte[length]));
    }
}
