using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppActors.Enemies;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;

namespace MegabonkLevels;

// Swaps the enemy a stage-boss or miniboss spawn would summon for one drawn from the level's bossPool or minibossPool, so a level can mix bosses from every map.
public static class BossPoolPatch
{
    private static MelonLogger.Instance _logger;
    private static readonly Random s_random = new();
    private static readonly HashSet<string> s_unknown = new();
    // Names already summoned in this run, shared by both pools; cleared when a new run starts.
    private static readonly HashSet<string> s_used = new(StringComparer.OrdinalIgnoreCase);
    private static int _usedRun = -1;

    public static void Install(MelonLogger.Instance logger) => _logger = logger;

    [HarmonyPatch(typeof(EnemyManager), "SpawnBoss")]
    private static class SpawnBossDrawsFromThePool
    {
        private static void Prefix(ref EEnemy eEnemy, EEnemyFlag enemyFlag)
        {
            if (!CustomLevelState.IsActive) return;
            var settings = LiveEditPatch.CurrentSettings;
            var kind = BossPools.Classify((int)enemyFlag);
            var pool = kind switch { BossPoolKind.Boss => settings.BossPool, BossPoolKind.Miniboss => settings.MinibossPool, _ => null };
            if (_usedRun != LiveEditPatch.RunGeneration)
            {
                _usedRun = LiveEditPatch.RunGeneration;
                s_used.Clear();
            }

            var name = BossPools.Pick(pool, s_random, s_used);
            if (name == null) return;
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
