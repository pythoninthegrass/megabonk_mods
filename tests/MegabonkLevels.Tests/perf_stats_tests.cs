namespace MegabonkLevels.Tests;

public class FrameTimeStatsTests
{
    [Fact]
    public void Summarize_NoSamples_ReturnsEmpty()
    {
        Assert.Equal(FrameTimeSummary.Empty, FrameTimeStats.Summarize(Array.Empty<float>(), 0));
    }

    [Fact]
    public void Summarize_CountBeyondFilledRange_ReadsOnlyTheFilledPrefix()
    {
        var samples = new float[] { 20f, 30f, 99f, 99f };

        var summary = FrameTimeStats.Summarize(samples, 2);

        Assert.Equal(2, summary.Frames);
        Assert.Equal(25d, summary.MeanMs, 6);
        Assert.Equal(20d, summary.MinMs, 6);
        Assert.Equal(30d, summary.MaxMs, 6);
    }

    [Fact]
    public void Summarize_SingleSample_EveryPercentileIsThatSample()
    {
        var summary = FrameTimeStats.Summarize(new[] { 16.7f }, 1);

        Assert.Equal(1, summary.Frames);
        Assert.Equal(16.7d, summary.MeanMs, 5);
        Assert.Equal(16.7d, summary.MedianMs, 5);
        Assert.Equal(16.7d, summary.P90Ms, 5);
        Assert.Equal(16.7d, summary.P99Ms, 5);
        Assert.Equal(16.7d, summary.MaxMs, 5);
        Assert.Equal(16.7d, summary.MinMs, 5);
    }

    [Fact]
    public void Summarize_HundredFrames_NearestRankPercentiles()
    {
        var samples = new float[100];
        for (var i = 0; i < 100; i++)
        {
            samples[i] = i + 1f;
        }

        var summary = FrameTimeStats.Summarize(samples, 100);

        Assert.Equal(50d, summary.MedianMs, 6);
        Assert.Equal(90d, summary.P90Ms, 6);
        Assert.Equal(99d, summary.P99Ms, 6);
        Assert.Equal(1d, summary.MinMs, 6);
        Assert.Equal(100d, summary.MaxMs, 6);
        Assert.Equal(50.5d, summary.MeanMs, 6);
    }

    [Fact]
    public void Summarize_UnorderedInput_DoesNotReorderTheCallerArray()
    {
        var samples = new float[] { 30f, 10f, 20f };

        FrameTimeStats.Summarize(samples, 3);

        Assert.Equal(new[] { 30f, 10f, 20f }, samples);
    }

    [Fact]
    public void Summarize_CountAboveBufferLength_IsClampedToTheBuffer()
    {
        var samples = new float[] { 5f, 5f };

        var summary = FrameTimeStats.Summarize(samples, 99);

        Assert.Equal(2, summary.Frames);
    }
}

public class PerfSpawnPlanTests
{
    [Fact]
    public void Ring_ZeroCount_ReturnsNoPoints()
    {
        Assert.Empty(PerfSpawnPlan.Ring(0f, 0f, 0, 6, 8f, 4f));
    }

    [Fact]
    public void Ring_CountBelowPerRing_SitsOnTheFirstRadius()
    {
        var points = PerfSpawnPlan.Ring(10f, -4f, 3, 6, 8f, 4f);

        Assert.Equal(3, points.Length);
        foreach (var point in points)
        {
            Assert.Equal(8f, PerfTestMath.Distance(point, 10f, -4f), 3);
        }
    }

    [Fact]
    public void Ring_PassesThePerRingBoundary_StepsOutByTheRingSpacing()
    {
        var points = PerfSpawnPlan.Ring(0f, 0f, 5, 4, 8f, 4f);

        Assert.Equal(8f, PerfTestMath.Distance(points[3], 0f, 0f), 3);
        Assert.Equal(12f, PerfTestMath.Distance(points[4], 0f, 0f), 3);
    }

    [Fact]
    public void Ring_PointsSpreadAroundTheCentre_NoTwoShareAnAngle()
    {
        var points = PerfSpawnPlan.Ring(0f, 0f, 8, 8, 8f, 4f);
        var angles = points.Select(PerfTestMath.BearingDegrees).ToArray();

        for (var i = 0; i < angles.Length; i++)
        {
            for (var j = i + 1; j < angles.Length; j++)
            {
                Assert.NotEqual(angles[i], angles[j], 3);
            }
        }
    }

    [Fact]
    public void Ring_NegativeCount_Throws()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => PerfSpawnPlan.Ring(0f, 0f, -1, 6, 8f, 4f));
    }

    [Fact]
    public void Ring_PerRingBelowOne_Throws()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => PerfSpawnPlan.Ring(0f, 0f, 4, 0, 8f, 4f));
    }

    [Fact]
    public void CountAboveTheMaximum_IsRejected()
    {
        Assert.False(PerfLimits.ValidSpawnCount(PerfSpawnPlan.MaxEnemies + 1));
        Assert.True(PerfLimits.ValidSpawnCount(PerfSpawnPlan.MaxEnemies));
        Assert.False(PerfLimits.ValidSpawnCount(0));
    }

    [Fact]
    public void PlayerHp_OutsideTheRange_IsRejected()
    {
        Assert.True(PerfLimits.ValidPlayerHp(1));
        Assert.True(PerfLimits.ValidPlayerHp(PerfLimits.MaxPlayerHp));
        Assert.False(PerfLimits.ValidPlayerHp(0));
        Assert.False(PerfLimits.ValidPlayerHp(-1));
        Assert.False(PerfLimits.ValidPlayerHp(PerfLimits.MaxPlayerHp + 1));
    }

    [Fact]
    public void Timescale_OutsideTheBoundsOrNaN_IsRejected()
    {
        Assert.True(PerfLimits.ValidTimeScale(1f));
        Assert.True(PerfLimits.ValidTimeScale(PerfLimits.MinTimeScale));
        Assert.True(PerfLimits.ValidTimeScale(PerfLimits.MaxTimeScale));
        Assert.False(PerfLimits.ValidTimeScale(0f));
        Assert.False(PerfLimits.ValidTimeScale(PerfLimits.MaxTimeScale + 1f));
        Assert.False(PerfLimits.ValidTimeScale(float.NaN));
    }
}

internal static class PerfTestMath
{
    public static double Distance(PerfSpawnPlan.SpawnPoint point, float centerX, float centerZ) =>
        Math.Sqrt((point.X - centerX) * (point.X - centerX) + (point.Z - centerZ) * (point.Z - centerZ));

    public static double BearingDegrees(PerfSpawnPlan.SpawnPoint point) =>
        (Math.Atan2(point.Z, point.X) * 180d / Math.PI + 360d) % 360d;
}
