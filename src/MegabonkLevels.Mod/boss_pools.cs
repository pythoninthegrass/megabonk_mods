using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public enum BossPoolKind { None, Boss, Miniboss }

// Which pool of enemy names a boss spawn draws from, and the draw itself.
public static class BossPools
{
    // EEnemyFlag bits: Boss 2, StageBoss 4, SummonerMiniboss 16, FinalBoss 32.
    private const int BossBit = 2;
    private const int StageBossBit = 4;
    private const int SummonerMinibossBit = 16;
    private const int FinalBossBit = 32;
    public const int MaxEntries = 64;

    // A stage or final boss draws from the boss pool, a miniboss from the miniboss pool, and anything else (swarms, challenge enemies) is left alone.
    public static BossPoolKind Classify(int flags) =>
        (flags & (StageBossBit | FinalBossBit)) != 0 ? BossPoolKind.Boss
        : (flags & (BossBit | SummonerMinibossBit)) != 0 ? BossPoolKind.Miniboss
        : BossPoolKind.None;

    // A uniformly drawn name from those not yet in `used`, which is then added to it so the same enemy never spawns twice in a run;
    // null for an absent, empty or used-up pool so the game's own pick stands.
    public static string Pick(IReadOnlyList<string> pool, Random random, ISet<string> used = null)
    {
        var fresh = pool?.Where(name => used == null || !used.Contains(name)).ToList();
        if (fresh is not { Count: > 0 }) return null;
        var name = fresh[random.Next(fresh.Count)];
        used?.Add(name);
        return name;
    }

    public static void Validate(IReadOnlyList<string> pool, string field)
    {
        if (pool == null) return;
        if (pool.Count > MaxEntries || pool.Any(string.IsNullOrWhiteSpace))
        {
            throw new ArgumentException($"{field} lists up to {MaxEntries} enemy names, none blank.");
        }
    }
}
