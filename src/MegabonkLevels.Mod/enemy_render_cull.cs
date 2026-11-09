using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using Assets.Scripts.Actors.Enemies;
using Assets.Scripts.Managers;
using UnityEngine;

namespace MegabonkLevels;

// Harness control that hides enemies only: Renderer.enabled=false on every renderer under the live enemies while
// AI, physics and animation components keep running. Only renderers this class turned off are restored; renderers
// the game disabled itself (dissolve, effects) stay the game's. Decisions live in EnemyRenderCullPlan.
public static class EnemyRenderCull
{
    private static readonly Dictionary<int, Renderer> Tracked = new();
    private static ModLogger _logger;
    private static bool _armed;
    private static int _lastSeenEnemies = -1;
    private static float _lastScanAt = float.NegativeInfinity;

    public static bool Armed => _armed;

    public static int DisabledCount => Tracked.Count;

    // The perf `render` verb: enabled=false is "stop rendering enemies", so it arms the cull and sweeps the swarm now;
    // enabled=true restores what it hid and disarms. The response reports what the cull does, not the caller's wording.
    public static JsonObject Set(bool renderEnabled, ModLogger logger)
    {
        _logger = logger;
        var enemies = LiveEnemies();
        _armed = EnemyRenderCullPlan.ArmsCull(renderEnabled);
        if (_armed)
        {
            Sweep(enemies, log: true);
        }
        else
        {
            Restore();
        }

        _lastSeenEnemies = -1;
        _logger?.Msg($"Perf: render: {(_armed ? "off, cull armed" : "on, cull disarmed")} enemies={enemies.Count} renderersOff={Tracked.Count}");
        return new JsonObject
        {
            ["enabled"] = renderEnabled,
            ["armed"] = _armed,
            ["enemies"] = enemies.Count,
            ["renderersOff"] = Tracked.Count,
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
        if (!EnemyRenderCullPlan.ShouldRescan(liveCount, _lastSeenEnemies, now, _lastScanAt, EnemyControlPlan.RescanIntervalSeconds))
        {
            return;
        }

        Sweep(LiveEnemies(), log: false);
    }

    public static double EnemyPositionSum()
    {
        var positions = new List<(float, float, float)>();
        foreach (var enemy in LiveEnemies())
        {
            try
            {
                var position = enemy.rb != null ? enemy.rb.position : enemy.transform.position;
                positions.Add((position.x, position.y, position.z));
            }
            catch (Exception)
            {
                // A despawned mid-read enemy simply misses this sample.
            }
        }

        return EnemyRenderCullPlan.PositionSum(positions);
    }

    private static void Sweep(List<Enemy> enemies, bool log)
    {
        var byId = new Dictionary<int, Renderer>();
        var census = new List<(int, bool)>();
        foreach (var enemy in enemies)
        {
            foreach (var renderer in RenderersOf(enemy))
            {
                try
                {
                    var id = renderer.GetInstanceID();
                    byId[id] = renderer;
                    census.Add((id, renderer.enabled));
                }
                catch (Exception)
                {
                    // Destroyed between the census and the read; nothing to hide.
                }
            }
        }

        var disabledNow = 0;
        foreach (var id in EnemyRenderCullPlan.ToDisable(census))
        {
            try
            {
                byId[id].enabled = false;
                Tracked[id] = byId[id];
                disabledNow++;
            }
            catch (Exception)
            {
                // Destroyed between the census and the write; nothing to hide.
            }
        }

        PruneDestroyed();
        var manager = EnemyManager.Instance;
        _lastSeenEnemies = manager == null ? 0 : manager.numEnemies;
        _lastScanAt = Time.unscaledTime;
        if (log && disabledNow > 0)
        {
            _logger?.Msg($"Perf: render: disabled {disabledNow} renderers, tracked={Tracked.Count}");
        }
    }

    private static void Restore()
    {
        var restored = 0;
        foreach (var renderer in Tracked.Values)
        {
            try
            {
                renderer.enabled = true;
                restored++;
            }
            catch (Exception)
            {
                // Destroyed while culled; the pool resets it on reuse.
            }
        }

        _logger?.Msg($"Perf: render: restored {restored} renderers");
        Tracked.Clear();
    }

    private static void PruneDestroyed()
    {
        List<int> dead = null;
        foreach (var pair in Tracked)
        {
            try
            {
                if (pair.Value == null)
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

    private static Renderer[] RenderersOf(Enemy enemy)
    {
        try
        {
            return enemy.GetComponentsInChildren<Renderer>(true) ?? Array.Empty<Renderer>();
        }
        catch (Exception)
        {
            return Array.Empty<Renderer>();
        }
    }
}
