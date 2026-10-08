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
    private const string DamageSource = "KillFloor";

    private static MelonLogger.Instance _logger;
    private static bool _armed;
    private static float _floorY;
    private static float _nextCheck;
    private static bool _playerKilled;

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

        var fallen = new List<Enemy>();
        foreach (var enemy in manager.enemies.Values)
        {
            if (enemy != null && KillFloor.ShouldKill(enemy.transform.position.y, _floorY))
            {
                fallen.Add(enemy);
            }
        }

        foreach (var enemy in fallen)
        {
            _logger.Msg($"KillFloor: enemy '{enemy.name}' fell to y={enemy.transform.position.y}, killing");
            enemy.Kill(DamageSource);
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
