using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Harness control that takes the live enemies out of Unity's physics solver: Rigidbody.isKinematic=true on every Rigidbody
// under them while AI, renderers and animation keep running. Only bodies this class froze are restored, to the value found.
public static class EnemyPhysicsFreeze
{
    private static readonly Dictionary<int, (Rigidbody Body, bool WasKinematic)> Tracked = new();
    private static MelonLogger.Instance _logger;
    private static bool _armed;
    private static int _lastSeenEnemies = -1;
    private static float _lastScanAt = float.NegativeInfinity;

    public static bool Armed => _armed;

    public static int FrozenCount => Tracked.Count;

    // The perf `physics` verb: enabled=false means the enemy's physics is not wanted, so the freeze arms and sweeps now;
    // enabled=true restores every body it froze and disarms.
    public static JsonObject Set(bool physicsEnabled, MelonLogger.Instance logger)
    {
        _logger = logger;
        var enemies = LiveEnemies();
        _armed = EnemyPhysicsFreezePlan.ArmsFreeze(physicsEnabled);
        if (_armed)
        {
            Sweep(enemies, log: true);
        }
        else
        {
            Restore();
        }

        _lastSeenEnemies = -1;
        _logger?.Msg($"Perf: physics: {(_armed ? "off, freeze armed" : "on, freeze disarmed")} enemies={enemies.Count} kinematic={Tracked.Count}");
        return new JsonObject
        {
            ["enabled"] = physicsEnabled,
            ["armed"] = _armed,
            ["enemies"] = enemies.Count,
            ["rigidbodiesKinematic"] = Tracked.Count,
        };
    }

    // Called from PerfMonitor.Tick every harness frame; while disarmed the whole path is one bool test.
    public static void Apply()
    {
        if (!_armed)
        {
            return;
        }

        var manager = EnemyManager.Instance;
        var liveCount = manager == null ? 0 : manager.numEnemies;
        var now = Time.unscaledTime;
        if (!EnemyPhysicsFreezePlan.ShouldRescan(liveCount, _lastSeenEnemies, now, _lastScanAt, EnemyControlPlan.RescanIntervalSeconds))
        {
            return;
        }

        Sweep(LiveEnemies(), log: false);
    }

    private static void Sweep(List<Enemy> enemies, bool log)
    {
        var byId = new Dictionary<int, Rigidbody>();
        var census = new List<(int, bool)>();
        foreach (var enemy in enemies)
        {
            foreach (var body in BodiesOf(enemy))
            {
                try
                {
                    var id = body.GetInstanceID();
                    byId[id] = body;
                    census.Add((id, body.isKinematic));
                }
                catch (Exception)
                {
                    // Destroyed between the census and the read; nothing to freeze.
                }
            }
        }

        var frozenNow = 0;
        var prior = EnemyPhysicsFreezePlan.PriorValues(census);
        foreach (var id in EnemyPhysicsFreezePlan.ToSetKinematic(census))
        {
            try
            {
                var body = byId[id];
                Tracked[id] = (body, prior[id]);
                body.isKinematic = true;
                frozenNow++;
            }
            catch (Exception)
            {
                // Destroyed between the census and the write; nothing to freeze.
            }
        }

        PruneDestroyed();
        var manager = EnemyManager.Instance;
        _lastSeenEnemies = manager == null ? 0 : manager.numEnemies;
        _lastScanAt = Time.unscaledTime;
        if (log && frozenNow > 0)
        {
            _logger?.Msg($"Perf: physics: froze {frozenNow} rigidbodies, tracked={Tracked.Count}");
        }
    }

    private static void Restore()
    {
        var restored = 0;
        foreach (var (body, wasKinematic) in Tracked.Values)
        {
            try
            {
                body.isKinematic = wasKinematic;
                restored++;
            }
            catch (Exception)
            {
                // Destroyed while frozen; the pool resets it on reuse.
            }
        }

        _logger?.Msg($"Perf: physics: restored {restored} rigidbodies");
        Tracked.Clear();
    }

    private static void PruneDestroyed()
    {
        List<int> dead = null;
        foreach (var pair in Tracked)
        {
            try
            {
                if (pair.Value.Body == null)
                {
                    (dead ??= new List<int>()).Add(pair.Key);
                }
            }
            catch (Exception)
            {
                (dead ??= new List<int>()).Add(pair.Key);
            }
        }

        if (dead == null)
        {
            return;
        }

        foreach (var id in dead)
        {
            Tracked.Remove(id);
        }
    }

    private static List<Enemy> LiveEnemies()
    {
        var enemies = new List<Enemy>();
        var manager = EnemyManager.Instance;
        var byId = manager?.enemies;
        if (byId == null)
        {
            return enemies;
        }

        foreach (var enemy in byId.Values)
        {
            if (enemy != null)
            {
                enemies.Add(enemy);
            }
        }

        return enemies;
    }

    private static Rigidbody[] BodiesOf(Enemy enemy)
    {
        try
        {
            return enemy.GetComponentsInChildren<Rigidbody>(true) ?? Array.Empty<Rigidbody>();
        }
        catch (Exception)
        {
            return Array.Empty<Rigidbody>();
        }
    }
}
