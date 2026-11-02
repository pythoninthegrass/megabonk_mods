using System;
using MegabonkLevels;
using Xunit;

public class FrameBufferTests
{
    [Fact]
    public void Record_BelowCapacity_CountsEveryFrame()
    {
        var buffer = new FrameBuffer(8);

        buffer.Record(4f);
        buffer.Record(6f);

        Assert.Equal(2, buffer.Count);
        Assert.Equal(0, buffer.PausedFrames);
        Assert.Equal(5d, buffer.Summarize().MeanMs);
    }

    [Fact]
    public void Record_PastCapacity_KeepsTheLatestFrames()
    {
        var buffer = new FrameBuffer(4);

        buffer.Record(100f);
        for (var i = 0; i < 4; i++)
        {
            buffer.Record(2f);
        }

        var summary = buffer.Summarize();
        Assert.Equal(4, buffer.Count);
        Assert.Equal(2d, summary.MeanMs);
        Assert.Equal(2d, summary.MaxMs);
    }

    [Fact]
    public void Pause_CountsTheFrameWithoutSamplingIt()
    {
        var buffer = new FrameBuffer(8);

        buffer.Record(4f);
        for (var i = 0; i < 3; i++)
        {
            buffer.Pause();
        }

        Assert.Equal(1, buffer.Count);
        Assert.Equal(3, buffer.PausedFrames);
        Assert.Equal(4f, buffer.Summarize().MaxMs);
    }

    [Fact]
    public void Summarize_NoSamples_IsEmpty()
    {
        var buffer = new FrameBuffer(8);
        buffer.Pause();

        var summary = buffer.Summarize();

        Assert.Equal(0, summary.Frames);
        Assert.Equal(1, buffer.PausedFrames);
    }

    [Fact]
    public void Clear_DropsSamplesCountsAndPausedFrames()
    {
        var buffer = new FrameBuffer(8);
        buffer.Record(4f);
        buffer.Pause();

        buffer.Clear();

        Assert.Equal(0, buffer.Count);
        Assert.Equal(0, buffer.PausedFrames);
        Assert.Equal(0, buffer.Summarize().Frames);
    }

    [Fact]
    public void Clear_AfterWrapping_RestartsFromAnEmptyBuffer()
    {
        var buffer = new FrameBuffer(2);
        buffer.Record(100f);
        buffer.Record(200f);

        buffer.Clear();
        buffer.Record(5f);

        Assert.Equal(1, buffer.Count);
        Assert.Equal(5d, buffer.Summarize().MeanMs);
    }

    [Fact]
    public void Constructor_NonPositiveCapacity_Throws()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => new FrameBuffer(0));
    }
}
