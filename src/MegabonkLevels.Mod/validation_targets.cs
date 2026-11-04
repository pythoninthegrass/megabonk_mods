using System.Linq;

namespace MegabonkLevels;

public enum ValidationTargetSource
{
    AuthoredLevel,
    NameSearch,
}

public readonly record struct ValidationTargets(ValidationTargetSource Source, (int X, int Z)? Start, (int X, int Z)? Boss, string Warning);

// Picks Validate's start and boss cells: a from-scratch level authors them, a generated-baseline level leaves them to a name search of the generated objects.
public static class ValidationTargetSelector
{
    public static ValidationTargets Select(LevelFile level, LevelState state, int width, int depth, float spacing)
    {
        if (!level.IsFromScratch)
        {
            return new ValidationTargets(ValidationTargetSource.NameSearch, null, null, null);
        }

        var start = CellOf(level.Spawn, width, depth, spacing);
        var boss = CellOf(level.BossSpawner, width, depth, spacing);
        var warning = boss is { } cell && !HasGround(state, cell, width, depth, spacing)
            ? $"boss spawner over empty cell ({cell.X}, {cell.Z}) with no placed object there"
            : null;
        return new ValidationTargets(ValidationTargetSource.AuthoredLevel, start, boss, warning);
    }

    private static (int X, int Z)? CellOf(SpawnPoint? point, int width, int depth, float spacing)
    {
        if (point?.Position is not { Count: 3 } position)
        {
            return null;
        }

        var cell = PositionReadout.CellOf(position[0], position[2], width, depth, spacing);
        return cell.InGrid ? (cell.X, cell.Z) : null;
    }

    // A placed object counts as ground whatever it is, since a catalog id does not say whether its mesh can be stood on.
    private static bool HasGround(LevelState state, (int X, int Z) cell, int width, int depth, float spacing) =>
        state.GetTile(cell.X, cell.Z) != null
        || state.Objects.Values.Any(obj =>
            !obj.Removed
            && obj.Transform is { } transform
            && PositionReadout.CellOf(transform.Position.X, transform.Position.Z, width, depth, spacing) is { InGrid: true } at
            && (at.X, at.Z) == cell);
}
