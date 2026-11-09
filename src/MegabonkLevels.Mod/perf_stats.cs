using System;

namespace MegabonkLevels;

// Frame-time percentiles over one measurement window, in milliseconds.
public readonly record struct FrameTimeSummary(int Frames, double MeanMs, double MedianMs, double P90Ms, double P99Ms, double MaxMs, double MinMs)
{
    public static readonly FrameTimeSummary Empty = new(0, 0, 0, 0, 0, 0, 0);
}

public static class FrameTimeStats
{
    // Nearest-rank percentiles over the first `count` entries of `samples`; the caller's buffer is not reordered.
    public static FrameTimeSummary Summarize(float[] samples, int count)
    {
        if (samples == null || count <= 0)
        {
            return FrameTimeSummary.Empty;
        }

        var filled = Math.Min(count, samples.Length);
        var sorted = new float[filled];
        Array.Copy(samples, sorted, filled);
        Array.Sort(sorted);

        double sum = 0f;
        for (var i = 0; i < filled; i++)
        {
            sum += sorted[i];
        }

        return new FrameTimeSummary(
            filled,
            sum / filled,
            At(sorted, 0.5),
            At(sorted, 0.9),
            At(sorted, 0.99),
            sorted[filled - 1],
            sorted[0]);
    }

    private static double At(float[] sorted, double rank) =>
        sorted[Math.Min(sorted.Length - 1, (int)Math.Ceiling(rank * sorted.Length) - 1)];
}

// Frame times for one measurement window. A paused frame carries no gameplay cost, so it is counted, never sampled.
public sealed class FrameBuffer
{
    private readonly float[] _frames;
    private int _write;

    public FrameBuffer(int capacity)
    {
        if (capacity < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(capacity));
        }

        _frames = new float[capacity];
    }

    public int Capacity => _frames.Length;

    public int Count { get; private set; }

    public int PausedFrames { get; private set; }

    public void Record(float ms)
    {
        _frames[_write] = ms;
        _write = (_write + 1) % _frames.Length;
        if (Count < _frames.Length)
        {
            Count++;
        }
    }

    public void Pause() => PausedFrames++;

    public FrameTimeSummary Summarize() => FrameTimeStats.Summarize(_frames, Count);

    public void Clear()
    {
        _write = 0;
        Count = 0;
        PausedFrames = 0;
    }
}

public static class PerfSpawnPlan
{
    public const int MaxEnemies = 300;

    // One point per entry, ordered outward from the centre: `perRing` evenly spaced angles per ring, each ring further out.
    public readonly record struct SpawnPoint(float X, float Z);

    public static SpawnPoint[] Ring(float centerX, float centerZ, int count, int perRing, float firstRadius, float ringSpacing)
    {
        if (count < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(count));
        }

        if (perRing < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(perRing));
        }

        var points = new SpawnPoint[count];
        for (var i = 0; i < count; i++)
        {
            var radius = firstRadius + (i / perRing) * ringSpacing;
            var angle = (Math.PI * 2 * i) / Math.Max(count, 1);
            points[i] = new SpawnPoint(
                (float)(centerX + (radius * Math.Cos(angle))),
                (float)(centerZ + (radius * Math.Sin(angle))));
        }

        return points;
    }
}

public static class PerfLimits
{
    public const float MinTimeScale = 0.05f;

    public const float MaxTimeScale = 20f;

    // The hp a measurement window parks the player at: enough that a 240-enemy swarm cannot end the run inside 20 s.
    public const int DefaultPlayerHp = 1_000_000;

    public const int MaxPlayerHp = 100_000_000;

    public static bool ValidSpawnCount(int count) => count >= 1 && count <= PerfSpawnPlan.MaxEnemies;

    public static bool ValidPlayerHp(int value) => value >= 1 && value <= MaxPlayerHp;

    public static bool ValidTimeScale(float value) =>
        !float.IsNaN(value) && !float.IsInfinity(value) && value >= MinTimeScale && value <= MaxTimeScale;
}
