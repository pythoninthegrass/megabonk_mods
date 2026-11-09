using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// A minimal from-scratch level to start editing: a flat square grid with the spawn at its centre and the boss spawner two cells east.
public static class BlankLevel
{
    public const int DefaultSize = 7;
    public const int MinimumSize = 3;
    private const float SpawnBodyY = 2f;
    private const float BossSpawnerRotationY = 270f;

    public static LevelFile Create(EMap map, int stageIndex, int tier, int size, float spacing, string gameBuildId)
    {
        if (size < MinimumSize)
        {
            throw new ArgumentException($"A from-scratch grid must be at least {MinimumSize} by {MinimumSize}, got {size}.", nameof(size));
        }

        var cells = new List<AuthoredCell>(size * size);
        for (var x = 0; x < size; x++)
        {
            for (var z = 0; z < size; z++)
            {
                cells.Add(new AuthoredCell(x, z, 0));
            }
        }

        var centre = size / 2;
        var bossCell = Math.Min(centre + 2, size - 1);
        var (spawnX, spawnZ) = PositionReadout.CellCentre(centre, centre, size, size, spacing);
        var (bossX, bossZ) = PositionReadout.CellCentre(bossCell, centre, size, size, spacing);

        return new LevelFile(
            SchemaVersion: LevelFile.CurrentSchemaVersion,
            GameBuildId: gameBuildId,
            Map: map,
            StageIndex: stageIndex,
            Tier: tier,
            Seed: 0,
            Packs: new Dictionary<string, string>(),
            Edits: Array.Empty<EditOp>(),
            Baseline: LevelFile.NoBaseline,
            Grid: new LevelGrid(size, size, cells),
            Spawn: new SpawnPoint(new[] { spawnX, SpawnBodyY, spawnZ }, new[] { 0f, 0f, 0f }),
            BossSpawner: new SpawnPoint(new[] { bossX, 0f, bossZ }, new[] { 0f, BossSpawnerRotationY, 0f }));
    }
}
