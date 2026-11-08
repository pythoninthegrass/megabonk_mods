using System;

namespace MegabonkLevels;

public readonly record struct ScrollbarThumb(float Top, float Height);

// When the console scrollbar shows and where its thumb sits. It shows only after a mouse wheel event and hides
// HideAfterSeconds after the last one.
public sealed class ConsoleScrollbar
{
    public const double HideAfterSeconds = 2.0;

    private double? _lastWheel;

    public void OnWheel(double now) => _lastWheel = now;

    public void Hide() => _lastWheel = null;

    public bool Visible(double now, int count, int viewport) =>
        count > viewport && _lastWheel is { } last && now - last < HideAfterSeconds;

    // Top and height in track units. offset counts lines above the bottom, so offset 0 puts the thumb at the track's end.
    public static ScrollbarThumb Thumb(int offset, int count, int viewport, float track, float minHeight)
    {
        if (count <= viewport)
        {
            return new ScrollbarThumb(0f, track);
        }

        var height = Math.Clamp(track * viewport / count, Math.Min(minHeight, track), track);
        var maxOffset = count - viewport;
        var fromTop = 1f - Math.Clamp(offset, 0, maxOffset) / (float)maxOffset;
        return new ScrollbarThumb(fromTop * (track - height), height);
    }
}
