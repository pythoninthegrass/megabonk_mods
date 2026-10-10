using System.Linq;

namespace MegabonkLevels;

public enum EditorTool
{
    Raise,
    Lower,
    Slope,
    Remove,
    Place,
    Select,
}

// Unity-free toolbar text and hotkeys shared by the tile tools and the object tools.
public static class EditorTools
{
    private const string CurrentToolColor = "#ffd84d";
    private static readonly EditorTool[] Tools = { EditorTool.Raise, EditorTool.Lower, EditorTool.Slope, EditorTool.Remove, EditorTool.Place, EditorTool.Select };

    public static EditorTool? FromHotkey(int digit) => digit >= 1 && digit <= Tools.Length ? Tools[digit - 1] : null;

    public static bool IsObjectTool(EditorTool tool) => tool is EditorTool.Place or EditorTool.Select;

    public static string ToolbarText(EditorTool current, string detail)
    {
        var tools = string.Join("   ", Tools.Select((tool, i) =>
            tool == current ? $"<color={CurrentToolColor}>[{i + 1} {tool}]</color>" : $"{i + 1} {tool}"));
        return $"{tools}\n{detail}";
    }

    public static string TileDetail((int X, int Z, TileState State)? target) =>
        target is { } t ? $"target ({t.X},{t.Z}) level {t.State.Height} slope {t.State.Slope}" : "target none";

    public static string PlaceDetail((int X, int Z)? cell, string selectedItem)
    {
        var where = cell is { } c ? $"({c.X},{c.Z})" : null;
        if (selectedItem == null)
        {
            return where == null ? "place - pick an item in the palette" : $"place {where} - pick an item in the palette";
        }

        return where == null ? $"place {selectedItem} - target none" : $"place {selectedItem} at {where}";
    }

    public static string SelectDetail(string selectedObject, string hoveredObject, (int X, int Z)? cell)
    {
        if (selectedObject != null)
        {
            var target = cell is { } c ? $"target ({c.X},{c.Z})" : "target none";
            return $"selected {selectedObject} - drag to move, R rotate, Del remove\n{target}";
        }

        return hoveredObject != null ? $"click to select {hoveredObject}" : "click an object to select it";
    }
}
