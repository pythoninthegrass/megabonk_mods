namespace MegabonkLevels;

public readonly record struct GenerationSnapshot(
    int MapSeed,
    int DebugSeed,
    string MapName,
    int MapType,
    int TileCount,
    int FlatTileCount,
    int FillTileCount,
    int NodeCount,
    string Hash,
    int ObjectCount,
    string ObjectsHash);

public static class GenerationReport
{
    public static string Format(GenerationSnapshot snapshot) =>
        $"A_GenerationComplete: map={snapshot.MapName} mapType={snapshot.MapType} mapSeed={snapshot.MapSeed} debugSeed={snapshot.DebugSeed} tiles={snapshot.TileCount} flatTiles={snapshot.FlatTileCount} fillTiles={snapshot.FillTileCount} nodes={snapshot.NodeCount} hash={snapshot.Hash} objects={snapshot.ObjectCount} objectsHash={snapshot.ObjectsHash}";
}
