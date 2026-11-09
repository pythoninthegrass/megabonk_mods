namespace MegabonkLevels.Tests;

public class LevelThumbnailSidecarTests : IDisposable
{
    private readonly string _folder = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());

    public LevelThumbnailSidecarTests() => Directory.CreateDirectory(_folder);

    public void Dispose() => Directory.Delete(_folder, true);

    private string Write(string name, byte[]? content = null)
    {
        var path = Path.Combine(_folder, name);
        File.WriteAllBytes(path, content ?? [1]);
        return path;
    }

    private static byte[] PngHeader(int width, int height)
    {
        var bytes = new byte[33];
        new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52 }.CopyTo(bytes, 0);
        System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(bytes.AsSpan(16), width);
        System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(bytes.AsSpan(20), height);
        return bytes;
    }

    private static byte[] JpegHeader(int width, int height)
    {
        var bytes = new List<byte> { 0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x04, 0x4A, 0x46, 0xFF, 0xC0, 0x00, 0x11, 0x08 };
        bytes.AddRange([(byte)(height >> 8), (byte)height, (byte)(width >> 8), (byte)width]);
        bytes.AddRange(new byte[10]);
        return bytes.ToArray();
    }

    [Fact]
    public void Find_MissingSidecarReturnsNothingWithoutWarning()
    {
        var level = Write("thps.mblevel.json");

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.Null(result.Warning);
    }

    [Fact]
    public void Find_BiomeIconIsSeparateFromTheThumbnail()
    {
        var level = Write("thps.mblevel.json");
        var thumbnail = Write("thps.png");
        var biome = Write("thps.biome.png");

        Assert.Equal(thumbnail, LevelThumbnailSidecar.Find(level).Path);
        Assert.Equal(biome, LevelThumbnailSidecar.Find(level, LevelThumbnailSidecar.BiomeSuffix).Path);
    }

    [Fact]
    public void Find_BiomeIconAloneLeavesTheThumbnailEmpty()
    {
        var level = Write("thps.mblevel.json");
        Write("thps.biome.jpg");

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.Null(result.Warning);
    }

    [Fact]
    public void Find_MissingBiomeIconReturnsNothingWithoutWarning()
    {
        var level = Write("thps.mblevel.json");
        Write("thps.png");

        var result = LevelThumbnailSidecar.Find(level, LevelThumbnailSidecar.BiomeSuffix);

        Assert.Null(result.Path);
        Assert.Null(result.Warning);
    }

    [Fact]
    public void Find_AmbiguousBiomeIconWarnsByName()
    {
        var level = Write("thps.mblevel.json");
        Write("thps.biome.png");
        Write("thps.biome.jpg");

        var result = LevelThumbnailSidecar.Find(level, LevelThumbnailSidecar.BiomeSuffix);

        Assert.Null(result.Path);
        Assert.Contains("biome icon", result.Warning);
    }

    [Theory]
    [InlineData(".png")]
    [InlineData(".PNG")]
    [InlineData(".jpg")]
    [InlineData(".Jpg")]
    [InlineData(".jpeg")]
    [InlineData(".JPEG")]
    public void Find_MatchesSupportedExtensionsCaseInsensitively(string extension)
    {
        var level = Write("thps.mblevel.json");
        var image = Write("thps" + extension);

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Equal(image, result.Path);
        Assert.Null(result.Warning);
    }

    [Fact]
    public void Find_MatchesBaseNameCaseInsensitively()
    {
        var level = Write("thps.mblevel.json");
        var image = Write("THPS.png");

        Assert.Equal(image, LevelThumbnailSidecar.Find(level).Path);
    }

    [Fact]
    public void Find_IgnoresOtherExtensionsAndOtherLevels()
    {
        var level = Write("thps.mblevel.json");
        Write("thps.gif");
        Write("thps.png.txt");
        Write("other.png");
        Directory.CreateDirectory(Path.Combine(_folder, "nested"));
        File.WriteAllBytes(Path.Combine(_folder, "nested", "thps.png"), [1]);

        Assert.Null(LevelThumbnailSidecar.Find(level).Path);
    }

    [Fact]
    public void Find_MultipleCandidatesWarnAndFallBack()
    {
        var level = Write("thps.mblevel.json");
        Write("thps.png");
        Write("thps.jpg");

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.NotNull(result.Warning);
    }

    [Fact]
    public void Find_EmptyFileWarnsAndFallsBack()
    {
        var level = Write("thps.mblevel.json");
        Write("thps.png", []);

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.NotNull(result.Warning);
    }

    [Fact]
    public void Find_OversizedFileWarnsAndFallsBack()
    {
        var level = Write("thps.mblevel.json");
        using (var stream = File.Create(Path.Combine(_folder, "thps.png")))
        {
            stream.SetLength(LevelThumbnailSidecar.MaxBytes + 1);
        }

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.NotNull(result.Warning);
    }

    [Fact]
    public void Find_FileAtSizeLimitIsAccepted()
    {
        var level = Write("thps.mblevel.json");
        using (var stream = File.Create(Path.Combine(_folder, "thps.png")))
        {
            stream.SetLength(LevelThumbnailSidecar.MaxBytes);
        }

        Assert.NotNull(LevelThumbnailSidecar.Find(level).Path);
    }

    [Fact]
    public void Find_DoesNotFollowSymlinks()
    {
        var level = Write("thps.mblevel.json");
        var target = Write("source.txt");
        File.CreateSymbolicLink(Path.Combine(_folder, "thps.png"), target);

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.NotNull(result.Warning);
    }

    [Theory]
    [InlineData("bad:name.mblevel.json")]
    [InlineData("bad\u0001name.mblevel.json")]
    public void Find_InvalidBaseNameIsSkippedWithWarning(string levelName)
    {
        var level = Path.Combine(_folder, levelName);
        File.WriteAllBytes(Path.Combine(_folder, levelName.Replace(".mblevel.json", ".png")), [1]);

        var result = LevelThumbnailSidecar.Find(level);

        Assert.Null(result.Path);
        Assert.NotNull(result.Warning);
    }

    [Fact]
    public void Find_MissingDirectoryReturnsNothing()
    {
        var result = LevelThumbnailSidecar.Find(Path.Combine(_folder, "missing", "thps.mblevel.json"));

        Assert.Null(result.Path);
        Assert.Null(result.Warning);
    }

    [Fact]
    public void TryReadDimensions_ReadsPngHeader()
    {
        Assert.True(LevelThumbnailSidecar.TryReadDimensions(PngHeader(1280, 720), out var width, out var height));
        Assert.Equal((1280, 720), (width, height));
    }

    [Fact]
    public void TryReadDimensions_ReadsJpegStartOfFrame()
    {
        Assert.True(LevelThumbnailSidecar.TryReadDimensions(JpegHeader(1920, 1080), out var width, out var height));
        Assert.Equal((1920, 1080), (width, height));
    }

    [Theory]
    [InlineData(new byte[0])]
    [InlineData(new byte[] { 1, 2, 3, 4 })]
    [InlineData(new byte[] { 0x89, 0x50, 0x4E, 0x47 })]
    [InlineData(new byte[] { 0xFF, 0xD8, 0xFF })]
    public void TryReadDimensions_RejectsUnrecognizedOrTruncatedData(byte[] data)
    {
        Assert.False(LevelThumbnailSidecar.TryReadDimensions(data, out _, out _));
    }

    [Theory]
    [InlineData(4096, 4096, true)]
    [InlineData(4097, 100, false)]
    [InlineData(100, 4097, false)]
    [InlineData(0, 100, false)]
    [InlineData(100, 0, false)]
    public void DimensionsWithinLimit_EnforcesPerSideCap(int width, int height, bool expected)
    {
        Assert.Equal(expected, LevelThumbnailSidecar.DimensionsWithinLimit(width, height));
    }
}
