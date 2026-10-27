namespace MegabonkLevels;

public readonly record struct EditorMapSupportResult(bool Supported, string Reason);

// The editor edits the ProceduralTileGeneration grid, so only maps generated as tiles (EMapType.Tiles) are supported.
public static class EditorMapSupport
{
    public const int TilesMapType = 0;
    public const int ProceduralMeshMapType = 1;

    public static EditorMapSupportResult Check(string mapName, int mapType) =>
        mapType == TilesMapType
            ? new EditorMapSupportResult(true, "")
            : new EditorMapSupportResult(false, $"{mapName} is not a tile map (mapType={mapType}); the editor needs a tile grid.");
}
