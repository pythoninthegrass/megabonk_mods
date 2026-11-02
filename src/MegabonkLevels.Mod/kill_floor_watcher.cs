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
    private const string HeartbeatVariable = "MEGABONK_KILL_FLOOR_HEARTBEAT";
    private const string DamageSource = "KillFloor";

    private static MelonLogger.Instance _logger;
    private static bool _armed;
    private static float _floorY;
    private static float _nextCheck;
    private static bool _playerKilled;
    private static bool _heartbeatEnabled = EnvFlag.IsSet(HeartbeatVariable);
    private static float _nextHeartbeat;
    private static float _lowestEnemyY = float.PositiveInfinity;
    private static float _lowestBossY = float.PositiveInfinity;
    private static readonly KillTracker _enemyKills = new(RetryKillAfterSeconds);
    private static readonly Dictionary<uint, Enemy> _actors = new();
    private static readonly Dictionary<uint, float> _lowestById = new();

    public static bool Armed => _armed;

    public static float FloorY => _armed ? _floorY : float.NegativeInfinity;

    public static void Arm(ProceduralTileGeneration tileGen, MelonLogger.Instance logger, float? killFloorY = null)
    {
        var mapParameters = tileGen.currentMapParameters ?? tileGen.currentStage?.mapParameters;
        var catchFloorY = CatchFloorY();
        var authored = killFloorY.HasValue;
        _floorY = authored
            ? KillFloor.FloorYExplicit(killFloorY, catchFloorY)
            : KillFloor.FloorY(LiveLevels(tileGen), mapParameters.scaledTileHeight, MarginBelowLowestTile, catchFloorY);
        _logger = logger;
        _playerKilled = false;
        _armed = !float.IsNegativeInfinity(_floorY);
        if (_armed)
        {
            var columns = tileGen.proceduralTiles;
            PositionLabel.Arm(columns.Length, columns[0].Length, mapParameters.scaledTileWidth, mapParameters.scaledTileHeight, _floorY, logger);
        }
        else
        {
            PositionLabel.Disarm();
        }

        logger.Msg(
            _armed
                ? $"KillFloor: armed at y={_floorY} ({(authored ? "authored" : "derived from tiles")}, catch floor y={catchFloorY})"
                : "KillFloor: no tiles, not armed");
        if (_armed && _heartbeatEnabled)
        {
            logger.Msg("KillFloor: heartbeat on");
        }
    }

    // A ProceduralMesh map has no tile grid, so the floor comes from the lowest point of the terrain collider.
    public static void ArmTerrain(float lowestTerrainY, MelonLogger.Instance logger)
    {
        var catchFloorY = CatchFloorY();
        _floorY = KillFloor.FloorYForTerrain(lowestTerrainY, MarginBelowLowestTile, catchFloorY);
        _logger = logger;
        _playerKilled = false;
        _armed = !float.IsNegativeInfinity(_floorY);
        PositionLabel.Disarm();
        logger.Msg(_armed ? $"KillFloor: armed at y={_floorY} (terrain low y={lowestTerrainY}, catch floor y={catchFloorY})" : "KillFloor: no terrain, not armed");
    }

    // The environment variable sets the starting state; the harness commands change it while the game runs.
    public static void SetHeartbeat(bool enabled, MelonLogger.Instance logger)
    {
        _heartbeatEnabled = enabled;
        _nextHeartbeat = 0f;
        logger.Msg($"KillFloor: heartbeat {(enabled ? "on" : "off")}");
    }

    public static void Disarm()
    {
        _armed = false;
        PositionLabel.Disarm();
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

        _actors.Clear();
        _lowestById.Clear();
        foreach (var enemy in manager.enemies.Values)
        {
            AddActor(enemy, isBoss: false);
        }

        // Stage bosses are kept in their own list and were not found in `enemies` in testing.
        var bosses = manager.stageBosses;
        if (bosses != null)
        {
            for (var i = 0; i < bosses.Count; i++)
            {
                AddActor(bosses[i], isBoss: true);
            }
        }

        if (_heartbeatEnabled)
        {
            LogHeartbeat(manager);
        }

        foreach (var (id, attempt) in _enemyKills.Select(_lowestById, _floorY, Time.unscaledTime))
        {
            var enemy = _actors[id];
            var position = enemy.transform.position;
            var stillPresent = attempt > 1 ? $" (still present, attempt {attempt})" : string.Empty;
            _logger.Msg($"KillFloor: enemy '{enemy.name}' id={id} fell to ({position.x}, {position.y}, {position.z}) lowest={_lowestById[id]}, killing{stillPresent}");
            enemy.Kill(DamageSource);
        }
    }

    // The pivot alone decides for everyone standing far above the floor; the collider is read only within reaching
    // distance of it, where reading bounds is what the kill decision actually needs.
    private static void AddActor(Enemy enemy, bool isBoss)
    {
        if (enemy == null)
        {
            return;
        }

        var pivotY = enemy.transform.position.y;
        var collider = KillFloor.ShouldProbeCollider(pivotY, _floorY) ? enemy.collider : null;
        var colliderMinY = collider != null && collider.enabled ? collider.bounds.min.y : (float?)null;
        var id = enemy.id;
        _actors[id] = enemy;
        _lowestById[id] = KillFloor.LowestPoint(pivotY, colliderMinY);
        if (!_heartbeatEnabled)
        {
            return;
        }

        if (isBoss)
        {
            _lowestBossY = Mathf.Min(_lowestBossY, pivotY);
        }
        else
        {
            _lowestEnemyY = Mathf.Min(_lowestEnemyY, pivotY);
        }
    }

    // Once every few seconds, reports how many actors the watcher sees and the lowest height each group reached since
    // the last report, so a boss that never shows up in a kill line can be told apart from one that never fell.
    private static void LogHeartbeat(EnemyManager manager)
    {
        if (Time.unscaledTime < _nextHeartbeat)
        {
            return;
        }

        var bosses = manager.stageBosses;
        var bossReport = new List<string>();
        if (bosses != null)
        {
            for (var i = 0; i < bosses.Count; i++)
            {
                var boss = bosses[i];
                if (boss == null)
                {
                    continue;
                }

                var lowest = _lowestById.TryGetValue(boss.id, out var recorded) ? recorded : boss.transform.position.y;
                bossReport.Add($"'{boss.name}' id={boss.id} y={boss.transform.position.y} lowest={lowest} inEnemies={manager.enemies.ContainsKey(boss.id)}");
            }
        }

        _nextHeartbeat = Time.unscaledTime + HeartbeatSeconds;
        _logger.Msg($"KillFloor: watch enemies={manager.enemies.Count} stageBosses={bosses?.Count ?? -1} lowestEnemyY={_lowestEnemyY} lowestBossY={_lowestBossY} bosses=[{string.Join("; ", bossReport)}]");
        _lowestEnemyY = float.PositiveInfinity;
        _lowestBossY = float.PositiveInfinity;
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
