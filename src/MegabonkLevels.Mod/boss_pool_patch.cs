using System;
using System.Collections.Generic;
using HarmonyLib;
using Assets.Scripts.Actors.Enemies;
using Actors.Enemies;
using Assets.Scripts.Managers;

namespace MegabonkLevels;

// Swaps the enemy a stage-boss or miniboss spawn would summon for one drawn from the level's bossPool or minibossPool, so a level can mix bosses from every map.
public static class BossPoolPatch
{
    private static ModLogger _logger;
    private static readonly HashSet<string> s_unknown = new();

    public static void Install(ModLogger logger) => _logger = logger;

    [HarmonyPatch(typeof(EnemyManager), "SpawnBoss")]
    private static class SpawnBossDrawsFromThePool
    {
        private static void Prefix(ref EEnemy eEnemy, EEnemyFlag enemyFlag)
        {
            if (!CustomLevelState.IsActive) return;
            var settings = LiveEditPatch.CurrentSettings;
            var kind = BossPools.Classify((int)enemyFlag);
            var pool = kind switch { BossPoolKind.Boss => settings.BossPool, BossPoolKind.Miniboss => settings.MinibossPool, _ => null };
            var name = LiveEditPatch.RunRandom.PickBoss(pool);
            if (name == null)
            {
                if (pool is { Count: > 0 })
                    _logger?.Msg($"BossPool: {kind} pool exhausted; keeping {eEnemy} (flags {enemyFlag})");
                return;
            }
            if (!Enum.TryParse<EEnemy>(name, true, out var chosen))
            {
                if (s_unknown.Add(name)) _logger?.Warning($"BossPool: unknown enemy '{name}' ignored");
                return;
            }

            _logger?.Msg($"BossPool: {kind} spawn of {eEnemy} (flags {enemyFlag}) replaced by {chosen}");
            eEnemy = chosen;
        }
    }
}
