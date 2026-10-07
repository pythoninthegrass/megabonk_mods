namespace MegabonkLevels;

public readonly record struct GenerationSnapshot(int MapSeed, int TileCount, int FlatTileCount, int FillTileCount);

public static class GenerationReport
{
    public static string Format(GenerationSnapshot snapshot) =>
        $"A_GenerationComplete: mapSeed={snapshot.MapSeed} tiles={snapshot.TileCount} flatTiles={snapshot.FlatTileCount} fillTiles={snapshot.FillTileCount}";
}
