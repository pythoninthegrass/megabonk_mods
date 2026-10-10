using System;

namespace MegabonkLevels;

// Unity-free scroll maths for the palette list.
public static class PaletteScroll
{
    // Keeps the offset when the row is fully visible, otherwise centres the row, clamped to the content.
    public static float OffsetToReveal(float rowTop, float rowHeight, float viewHeight, float currentOffset, float contentHeight)
    {
        var visible = rowTop >= currentOffset && rowTop + rowHeight <= currentOffset + viewHeight;
        if (visible)
        {
            return currentOffset;
        }

        var maxOffset = MathF.Max(0f, contentHeight - viewHeight);
        return Math.Clamp(rowTop + rowHeight / 2f - viewHeight / 2f, 0f, maxOffset);
    }
}
