namespace MegabonkLevels;

// The kill-enemies target names, kept free of game types so the command parser and its tests can use them.
public static class EnemyKillTargets
{
    public const string Nearest = "nearest";
    public const string All = "all";
    public const string Bosses = "bosses";

    public static readonly string[] Names = { Nearest, All, Bosses };
}
