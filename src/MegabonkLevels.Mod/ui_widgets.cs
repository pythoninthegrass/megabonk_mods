using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// An editor widget's rect in screenshot pixels (origin top left), the space the mouse command and the screenshot tool use; a disabled widget ignores clicks.
public readonly record struct UiWidget(string Name, float X, float Y, float Width, float Height, bool Enabled = true)
{
    public (float X, float Y) Centre => (X + Width / 2f, Y + Height / 2f);

    public bool Contains(float x, float y) => x >= X && x < X + Width && y >= Y && y < Y + Height;
}

public static class UiWidgets
{
    // Unity screen rects have a bottom-left origin, so the top edge is the larger y.
    public static UiWidget FromScreenRect(string name, float xMin, float yMin, float xMax, float yMax, int screenHeight, bool enabled = true) =>
        new(name, xMin, screenHeight - yMax, xMax - xMin, yMax - yMin, enabled);

    // The first match wins, so list specific widgets before the panels that contain them.
    public static UiWidget? At(IEnumerable<UiWidget> widgets, float x, float y) =>
        widgets.Cast<UiWidget?>().FirstOrDefault(widget => widget.Value.Contains(x, y));

    public static bool TryFind(IReadOnlyList<UiWidget> widgets, string name, out UiWidget widget, out string error)
    {
        foreach (var candidate in widgets)
        {
            if (string.Equals(candidate.Name, name, StringComparison.OrdinalIgnoreCase))
            {
                widget = candidate;
                error = null;
                return true;
            }
        }

        widget = default;
        error = $"no widget named '{name}'; known: {string.Join(", ", widgets.Select(w => w.Name))}";
        return false;
    }
}
