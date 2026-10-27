using System;
using System.Collections.Generic;
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

    // The tool active on entering the editor; Select edits nothing until an object is pressed.
    public const EditorTool Default = EditorTool.Select;

    public static EditorTool? FromHotkey(int digit) => digit >= 1 && digit <= Tools.Length ? Tools[digit - 1] : null;

    public static bool IsObjectTool(EditorTool tool) => tool is EditorTool.Place or EditorTool.Select;

    // A terrain map has no tile grid, so the tile tools are unavailable there.
    public static bool IsAvailable(EditorTool tool, bool tileTools) => tileTools || IsObjectTool(tool);

    public static string UnavailableMessage(EditorTool tool) => $"{tool} is unavailable: this is a terrain map with no tile grid, only objects can be edited";

    public static IReadOnlyList<EditorTool> All => Tools;

    public static string ToolLabel(EditorTool tool, EditorTool current)
    {
        var label = $"{Array.IndexOf(Tools, tool) + 1} {tool}";
        return tool == current ? $"<color={CurrentToolColor}>[{label}]</color>" : label;
    }

    public static string WidgetName(EditorTool tool) => $"Tool:{tool}";

    public static string ToolbarText(EditorTool current) => string.Join("   ", Tools.Select(tool => ToolLabel(tool, current)));

    public static string Description(EditorTool tool) => tool switch
    {
        EditorTool.Raise => "Click a tile to raise it one level",
        EditorTool.Lower => "Click a tile to lower it one level",
        EditorTool.Slope => "Click a tile to cycle its slope: north, east, south, west, flat",
        EditorTool.Remove => "Click a tile to remove it",
        EditorTool.Place => "Pick an item in the palette, then click the map to place it",
        EditorTool.Select => "Click an object to select it; drag to move, R rotate, Del remove",
        _ => "",
    };

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
