namespace MegabonkLevels;

// Supported means the editor can enter; TileTools is false on terrain maps, where only object editing works.
public readonly record struct EditorMapSupportResult(bool Supported, bool TileTools, string Reason);

// Tiles maps (EMapType.Tiles) expose the ProceduralTileGeneration grid; ProceduralMesh maps are one heightmap mesh and get object editing only.
public static class EditorMapSupport
{
    public const int TilesMapType = 0;
    public const int ProceduralMeshMapType = 1;

    public static EditorMapSupportResult Check(string mapName, int mapType) => mapType switch
    {
        TilesMapType => new EditorMapSupportResult(true, true, ""),
        ProceduralMeshMapType => new EditorMapSupportResult(true, false, $"{mapName} is a terrain map (mapType={mapType}); the tile tools are disabled, objects can still be edited."),
        _ => new EditorMapSupportResult(false, false, $"{mapName} has an unknown map type (mapType={mapType}); the editor cannot edit it."),
    };
}
