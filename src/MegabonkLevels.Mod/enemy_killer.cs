using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using Il2CppAssets.Scripts.Actors;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Managers;
using UnityEngine;

namespace MegabonkLevels;

// See "Killing enemies" in docs/development.md.
public static class EnemyKiller
{
    private const string Source = "HarnessKill";
    private const float LethalDamage = 1_000_000f;

    public static JsonObject Kill(string target)
    {
        var manager = EnemyManager.Instance;
        if (manager?.enemies == null)
        {
            throw new InvalidOperationException("kill-enemies: no enemy manager in the scene");
        }

        var victims = Select(manager, target);
        var results = new JsonArray();
        var bosses = 0;
        var dead = 0;
        foreach (var enemy in victims)
        {
            var isBoss = enemy.IsBoss();
            var hpBefore = enemy.hp;
            var id = enemy.id;
            Submit(enemy);
            var hpAfter = enemy.hp;
            bosses += isBoss ? 1 : 0;
            dead += hpAfter <= 0f ? 1 : 0;
            results.Add(new JsonObject
            {
                ["id"] = id,
                ["name"] = enemy.gameObject != null ? enemy.gameObject.name : null,
                ["boss"] = isBoss,
                ["stageBoss"] = enemy.IsStageBoss(),
                ["hpBefore"] = hpBefore,
                ["hpAfter"] = hpAfter,
            });
        }

        return new JsonObject
        {
            ["target"] = target,
            ["found"] = victims.Count,
            ["killed"] = dead,
            ["bossesFound"] = bosses,
            ["stageBossDied"] = manager.stageBossIsDead,
            ["enemies"] = results,
        };
    }

    // Lethal damage through Enemy.DamageExternal runs the game's own Damage and death handlers, so the death events fire.
    private static void Submit(Enemy enemy)
    {
        var dc = new DamageContainer(1f, Source)
        {
            damage = LethalDamage,
            enemy = enemy,
            flags = DcFlags.BypassAll | DcFlags.IgnoreArmor | DcFlags.BossDamage,
        };
        enemy.DamageExternal(dc);
    }

    private static List<Enemy> Select(EnemyManager manager, string target)
    {
        var live = new List<Enemy>();
        foreach (var enemy in manager.enemies.Values)
        {
            if (enemy != null && enemy.hp > 0f)
            {
                live.Add(enemy);
            }
        }

        switch (target)
        {
            case EnemyKillTargets.All:
                return live;
            case EnemyKillTargets.Bosses:
                return live.FindAll(enemy => enemy.IsBoss());
            case EnemyKillTargets.Nearest:
                var player = MyPlayer.Instance
                    ?? throw new InvalidOperationException("kill-enemies: no player: start a run first");
                var origin = player.transform.position;
                Enemy nearest = null;
                var best = float.MaxValue;
                foreach (var enemy in live)
                {
                    var distance = Vector3.SqrMagnitude(enemy.transform.position - origin);
                    if (distance < best)
                    {
                        best = distance;
                        nearest = enemy;
                    }
                }

                return nearest == null ? new List<Enemy>() : new List<Enemy> { nearest };
            default:
                throw new ArgumentException($"kill-enemies: unknown target '{target}'");
        }
    }
}
