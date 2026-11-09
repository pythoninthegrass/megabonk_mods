namespace MegabonkLevels.Tests;

public class PcmAudioTests
{
    [Fact]
    public void Decode_PacksShortReadsIntoBoundedBlocks()
    {
        var remaining = PcmAudio.BlockSamples + 4;
        var audio = PcmAudio.Read(2, 44100, (_, _) =>
        {
            if (remaining == 0) return 0;
            remaining -= 2;
            return 2;
        });
        Assert.Equal(2, audio.Blocks.Count);
        Assert.Equal(PcmAudio.BlockSamples, audio.Blocks[0].Length);
        Assert.Equal(4, audio.Blocks[1].Length);
    }

    [Fact]
    public void Decode_KeepsChannelAlignedBlocksAndActualFrameCount()
    {
        var calls = 0;
        var audio = PcmAudio.Read(2, 48000, (buffer, count) =>
        {
            calls++;
            var read = calls == 1 ? count : calls == 2 ? 4 : 0;
            Array.Fill(buffer, 0.25f, 0, read);
            return read;
        });

        Assert.Equal(48000, audio.SampleRate);
        Assert.Equal(2, audio.Channels);
        Assert.Equal((PcmAudio.BlockSamples + 4) / 2, audio.Frames);
        Assert.Equal(2, audio.Blocks.Count);
        Assert.Equal(4, audio.Blocks[1].Length);
        Assert.All(audio.Blocks.SelectMany(x => x), x => Assert.Equal(0.25f, x));
    }

    [Theory]
    [InlineData(0, 44100)]
    [InlineData(3, 44100)]
    [InlineData(2, 0)]
    [InlineData(1, 192000)]
    public void Decode_RejectsInvalidFormatBeforeReading(int channels, int rate)
    {
        Assert.Throws<InvalidDataException>(() => PcmAudio.Read(channels, rate, (_, _) => throw new Exception("must not read")));
    }

    [Fact]
    public void Decode_RejectsEmptyMisalignedAndNonFiniteSamples()
    {
        Assert.Throws<InvalidDataException>(() => PcmAudio.Read(2, 44100, (_, _) => 0));
        Assert.Throws<InvalidDataException>(() => PcmAudio.Read(2, 44100, (_, _) => 1));
        Assert.Throws<InvalidDataException>(() => PcmAudio.Read(1, 44100, (buffer, _) => { buffer[0] = float.NaN; return 1; }));
        Assert.Throws<InvalidDataException>(() => PcmAudio.Read(1, 44100, (buffer, _) => { buffer[0] = float.PositiveInfinity; return 1; }));
    }

    [Fact]
    public void Decode_AllowsDecoderPeaksAboveOne()
    {
        var first = true;
        var audio = PcmAudio.Read(1, 44100, (buffer, _) =>
        {
            if (!first) return 0;
            first = false;
            buffer[0] = 1.0414f;
            return 1;
        });
        Assert.Equal(1.0414f, audio.Blocks[0][0]);
    }

    [Fact]
    public void Decode_EnforcesLimitWhileReadingAndAcceptsExactlyTheLimit()
    {
        Assert.Throws<InvalidDataException>(() => PcmAudio.Read(2, 44100, (_, _) => 4, maxSamples: 4));
        var calls = 0;
        Assert.Equal(2, PcmAudio.Read(2, 44100, (_, _) => ++calls == 1 ? 4 : 0, maxSamples: 4).Frames);
    }

    [Fact]
    public void Decode_ObservesCancellationBeforeAndBetweenReads()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        Assert.Throws<OperationCanceledException>(() => PcmAudio.Read(2, 44100, (_, _) => throw new Exception("must not read"), cancellation.Token));

        using var duringRead = new CancellationTokenSource();
        Assert.Throws<OperationCanceledException>(() => PcmAudio.Read(2, 44100, (_, count) => { duringRead.Cancel(); return count; }, duringRead.Token));
    }
}
