using System.Collections.Generic;
using System.Linq;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Kills the player and enemies that fall below KillFloor.FloorY in a mod-loaded level, so a removed tile or an
// uncovered void ends the fall instead of leaving bodies resting on the game's own catch floor.
public static class KillFloorWatcher
{
    private const float MarginBelowLowestTile = 40f;
    private const float CheckIntervalSeconds = 0.25f;
    private const float RetryKillAfterSeconds = 2f;
    private const float HeartbeatSeconds = 5f;
    private const string DamageSource = "KillFloor";

    private static MelonLogger.Instance _logger;
    private static bool _armed;
    private static float _floorY;
    private static float _nextCheck;
    private static bool _playerKilled;
    private static float _nextHeartbeat;
    private static float _lowestEnemyY = float.PositiveInfinity;
    private static float _lowestBossY = float.PositiveInfinity;
    private static readonly KillTracker _enemyKills = new(RetryKillAfterSeconds);

    public static void Arm(ProceduralTileGeneration tileGen, MelonLogger.Instance logger)
    {
        var mapParameters = tileGen.currentMapParameters ?? tileGen.currentStage?.mapParameters;
        var levels = LiveLevels(tileGen);
        var catchFloorY = CatchFloorY();
        _floorY = KillFloor.FloorY(levels, mapParameters.scaledTileHeight, MarginBelowLowestTile, catchFloorY);
        _logger = logger;
        _playerKilled = false;
        _armed = !float.IsNegativeInfinity(_floorY);
        logger.Msg(_armed ? $"KillFloor: armed at y={_floorY} (catch floor y={catchFloorY})" : "KillFloor: no tiles, not armed");
    }

    public static void Disarm()
    {
        _armed = false;
    }

    public static void Tick()
    {
        if (!_armed || Time.unscaledTime < _nextCheck)
        {
            return;
        }

        _nextCheck = Time.unscaledTime + CheckIntervalSeconds;
        KillFallenPlayer();
        KillFallenEnemies();
    }

    private static void KillFallenPlayer()
    {
        var player = MyPlayer.Instance;
        if (_playerKilled || player == null || !KillFloor.ShouldKill(player.transform.position.y, _floorY))
        {
            return;
        }

        _playerKilled = true;
        _logger.Msg($"KillFloor: player fell to y={player.transform.position.y}, killing");
        player.inventory.playerHealth.KillPlayer();
    }

    private static void KillFallenEnemies()
    {
        var manager = EnemyManager.Instance;
        if (manager?.enemies == null)
        {
            return;
        }

        var actors = new Dictionary<uint, Enemy>();
        foreach (var enemy in manager.enemies.Values)
        {
            AddActor(actors, enemy);
        }

        // Stage bosses are kept in their own list and were not found in `enemies` in testing.
        if (manager.stageBosses != null)
        {
            foreach (var boss in manager.stageBosses)
            {
                AddActor(actors, boss);
            }
        }

        LogHeartbeat(manager, actors);

        var candidates = actors.Select(a => (a.Key, LowestPoint(a.Value)));
        foreach (var (id, attempt) in _enemyKills.Select(candidates, _floorY, Time.unscaledTime))
        {
            var enemy = actors[id];
            var position = enemy.transform.position;
            var lowest = LowestPoint(enemy);
            var stillPresent = attempt > 1 ? $" (still present, attempt {attempt})" : string.Empty;
            _logger.Msg($"KillFloor: enemy '{enemy.name}' id={id} fell to ({position.x}, {position.y}, {position.z}) lowest={lowest}, killing{stillPresent}");
            enemy.Kill(DamageSource);
        }
    }

    // Once every few seconds, reports how many actors the watcher sees and the lowest height each group reached since
    // the last report, so a boss that never shows up in a kill line can be told apart from one that never fell.
    private static void LogHeartbeat(EnemyManager manager, Dictionary<uint, Enemy> actors)
    {
        foreach (var enemy in manager.enemies.Values)
        {
            if (enemy != null)
            {
                _lowestEnemyY = Mathf.Min(_lowestEnemyY, LowestPoint(enemy));
            }
        }

        var bosses = manager.stageBosses;
        var bossReport = new List<string>();
        if (bosses != null)
        {
            foreach (var boss in bosses.ToArray().Where(b => b != null))
            {
                _lowestBossY = Mathf.Min(_lowestBossY, LowestPoint(boss));
                bossReport.Add($"'{boss.name}' id={boss.id} y={boss.transform.position.y} lowest={LowestPoint(boss)} inEnemies={manager.enemies.ContainsKey(boss.id)}");
            }
        }

        if (Time.unscaledTime < _nextHeartbeat)
        {
            return;
        }

        _nextHeartbeat = Time.unscaledTime + HeartbeatSeconds;
        _logger.Msg($"KillFloor: watch enemies={manager.enemies.Count} stageBosses={bosses?.Count ?? -1} lowestEnemyY={_lowestEnemyY} lowestBossY={_lowestBossY} bosses=[{string.Join("; ", bossReport)}]");
        _lowestEnemyY = float.PositiveInfinity;
        _lowestBossY = float.PositiveInfinity;
    }

    private static float LowestPoint(Enemy enemy)
    {
        var collider = enemy.collider;
        float? colliderMinY = collider != null && collider.enabled ? collider.bounds.min.y : null;
        return KillFloor.LowestPoint(enemy.transform.position.y, colliderMinY);
    }

    private static void AddActor(Dictionary<uint, Enemy> actors, Enemy enemy)
    {
        if (enemy != null)
        {
            actors[enemy.id] = enemy;
        }
    }

    private static IEnumerable<int> LiveLevels(ProceduralTileGeneration tileGen)
    {
        var levels = new List<int>();
        foreach (var column in tileGen.proceduralTiles)
        {
            levels.AddRange(column?.Where(t => t != null).Select(t => t.posY) ?? Enumerable.Empty<int>());
        }

        return levels;
    }

    // The game's own floor far below the map: the lowest world collider (the rest are boundary walls) sits at its
    // transform's y, since its mesh bounds read as a 1x1x1 box. The kill floor must stay above it.
    private static float CatchFloorY()
    {
        var floorY = float.PositiveInfinity;
        foreach (var trigger in Object.FindObjectsOfType<WorldColliderTrigger>())
        {
            floorY = Mathf.Min(floorY, trigger.transform.position.y);
        }

        return float.IsPositiveInfinity(floorY) ? float.NegativeInfinity : floorY;
    }
}
