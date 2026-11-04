using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using Il2Cpp;
using Il2CppActors.Enemies;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Harness control that stops the live enemies' animation updates: Behaviour.enabled=false on their AnimatedMesh and
// Animator components while renderers, colliders and the Rigidbody keep running. Only components this class stopped are
// restored, to the enabled value they had. Decisions live in EnemyAnimationCullPlan.
public static class EnemyAnimationCull
{
    private static readonly Dictionary<int, (Behaviour Body, bool WasEnabled, string TypeName)> Tracked = new();
    private static MelonLogger.Instance _logger;
    private static bool _armed;
    private static int _lastSeenEnemies = -1;
    private static int _componentsFound;
    private static float _lastScanAt = float.NegativeInfinity;

    public static bool Armed => _armed;

    public static int StoppedCount => Tracked.Count;

    // Distinct animation components seen under the live enemies at the last sweep: the denominator that says whether a
    // cull that stopped nothing found nothing, or found components the game had already disabled.
    public static int ComponentsFound => _componentsFound;

    // What the cull is holding off, by component type, so a reader can see whether an enemy carries an Animator at all.
    public static Dictionary<string, int> StoppedByType()
    {
        var census = new List<(string, bool)>();
        foreach (var entry in Tracked.Values)
        {
            census.Add((entry.TypeName, true));
        }

        return EnemyAnimationCullPlan.CountsByType(census);
    }

    public static JsonObject StoppedByTypeNode()
    {
        var node = new JsonObject();
        foreach (var (type, count) in StoppedByType())
        {
            node[type] = count;
        }

        return node;
    }

    // The perf `animation` verb: enabled=false stops the enemies' animation updates, enabled=true restores them.
    public static JsonObject Set(bool animationEnabled, MelonLogger.Instance logger)
    {
        _logger = logger;
        var enemies = LiveEnemies();
        _armed = EnemyAnimationCullPlan.ArmsCull(animationEnabled);
        if (_armed)
        {
            Sweep(enemies, log: true);
        }
        else
        {
            Restore();
        }

        _lastSeenEnemies = -1;
        _logger?.Msg($"Perf: animation: {(_armed ? "off, cull armed" : "on, cull disarmed")} enemies={enemies.Count} stopped={Tracked.Count} found={_componentsFound}");
        return new JsonObject
        {
            ["enabled"] = animationEnabled,
            ["armed"] = _armed,
            ["enemies"] = enemies.Count,
            ["behavioursOff"] = Tracked.Count,
            ["componentsFound"] = _componentsFound,
            ["byType"] = StoppedByTypeNode(),
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
        if (!EnemyAnimationCullPlan.ShouldRescan(liveCount, _lastSeenEnemies, now, _lastScanAt, EnemyControlPlan.RescanIntervalSeconds))
        {
            return;
        }

        Sweep(LiveEnemies(), log: false);
    }

    private static void Sweep(List<Enemy> enemies, bool log)
    {
        var byId = new Dictionary<int, Behaviour>();
        var types = new Dictionary<int, string>();
        var census = new List<(int, bool)>();
        foreach (var enemy in enemies)
        {
            foreach (var (body, typeName) in ComponentsOf(enemy))
            {
                try
                {
                    var id = body.GetInstanceID();
                    byId[id] = body;
                    types[id] = typeName;
                    census.Add((id, body.enabled));
                }
                catch (Exception)
                {
                    // Destroyed between the census and the read; nothing to stop.
                }
            }
        }

        var stoppedNow = 0;
        foreach (var id in EnemyAnimationCullPlan.ToDisable(census))
        {
            try
            {
                var body = byId[id];
                Tracked[id] = (body, body.enabled, types.TryGetValue(id, out var typeName) ? typeName : "Behaviour");
                body.enabled = false;
                stoppedNow++;
            }
            catch (Exception)
            {
                // Destroyed between the census and the write; nothing to stop.
            }
        }

        PruneDestroyed();
        _componentsFound = byId.Count;
        var manager = EnemyManager.Instance;
        _lastSeenEnemies = manager == null ? 0 : manager.numEnemies;
        _lastScanAt = Time.unscaledTime;
        if (log && stoppedNow > 0)
        {
            _logger?.Msg($"Perf: animation: stopped {stoppedNow} animation components, tracked={Tracked.Count}");
        }
    }

    private static void Restore()
    {
        var restored = 0;
        foreach (var (body, wasEnabled, _) in Tracked.Values)
        {
            try
            {
                body.enabled = wasEnabled;
                restored++;
            }
            catch (Exception)
            {
                // Destroyed while stopped; the pool resets it on reuse.
            }
        }

        _logger?.Msg($"Perf: animation: restored {restored} animation components");
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

    // AnimatedMesh is the game's mesh-swap ticker; Animator is there only if an enemy prefab carries one, which the census in the
    // status report settles rather than assumes. Both are Behaviours, so the cull is their enabled flag.
    private static List<(Behaviour Body, string TypeName)> ComponentsOf(Enemy enemy)
    {
        var found = new List<(Behaviour, string)>();
        try
        {
            foreach (var mesh in enemy.GetComponentsInChildren<AnimatedMesh>(true) ?? Array.Empty<AnimatedMesh>())
            {
                found.Add((mesh, nameof(AnimatedMesh)));
            }
        }
        catch (Exception)
        {
            return found;
        }

        try
        {
            foreach (var animator in enemy.GetComponentsInChildren<Animator>(true) ?? Array.Empty<Animator>())
            {
                found.Add((animator, nameof(Animator)));
            }
        }
        catch (Exception)
        {
            // No Animator on this enemy, or the type is not in this build; the mesh ticker alone is the animation.
        }

        return found;
    }
}
