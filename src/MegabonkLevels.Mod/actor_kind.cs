namespace MegabonkLevels;

// See "Enemy kinds" in docs/development.md for the EEnemyFlag bits and precedence rule.
public enum ActorKind
{
    Enemy,
    Elite,
    Miniboss,
    StageBoss,
    FinalBoss,
}

public static class ActorKinds
{
    private const int Elite = 1;
    private const int Boss = 2;
    private const int StageBoss = 4;
    private const int SummonerMiniboss = 16;
    private const int FinalBoss = 32;

    public static ActorKind Of(int enemyFlags)
    {
        if ((enemyFlags & FinalBoss) != 0)
        {
            return ActorKind.FinalBoss;
        }

        if ((enemyFlags & StageBoss) != 0)
        {
            return ActorKind.StageBoss;
        }

        if ((enemyFlags & (Boss | SummonerMiniboss)) != 0)
        {
            return ActorKind.Miniboss;
        }

        if ((enemyFlags & Elite) != 0)
        {
            return ActorKind.Elite;
        }

        return ActorKind.Enemy;
    }

    // Every label ends in a colon, matching the player's "me:" line.
    public static string Label(ActorKind kind) => kind switch
    {
        ActorKind.FinalBoss => "final boss:",
        ActorKind.StageBoss => "boss:",
        ActorKind.Miniboss => "miniboss:",
        ActorKind.Elite => "elite:",
        _ => "enemy:",
    };

    // Bosses, stage bosses and minibosses are always listed in the readout; elites and plain enemies are subject to
    // the bounded nearest/below-floor selection.
    public static bool IsBossTier(ActorKind kind) =>
        kind is ActorKind.FinalBoss or ActorKind.StageBoss or ActorKind.Miniboss;
}
