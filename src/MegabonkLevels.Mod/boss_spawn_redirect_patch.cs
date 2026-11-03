using System;
using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Managers;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// The Warehouse's boss portal hangs inside the glass box above the main half pipe, hidden in plain sight. A spawner
// summons its boss at its own position, so the boss appears in a box it can climb but never leave, and "Defeat the
// Boss" cannot complete. This intercepts the spawns the portal triggers and teleports each one to a random walkable
// spot in the level's interior away from the box, keeping the portal, its VFX and the Defeat the Boss wiring where the
// game put them.
//
// The Boss Curse shrine (InteractableShrineCursed) increments GameManager.bossCurses, making the same Interact() call
// summon 1 + bossCurses bosses through the same path, so the redirect arms for all of them and spaces the copies.
public static class BossSpawnRedirectPatch
{
    private const int CandidatesPerBoss = 48;
    // Large prime multiplier so each copy of a curse summon samples its own ring instead of the shared candidate order.
    private const int SeedPerCopy = 7919;
    // A surface counts as floor only when its normal is close enough to up; bosses must not land on a wall face.
    private const float WalkableNormalY = 0.8f;

    private static MelonLogger.Instance _logger;
    private static int? _armedFrame;
    private static int _expectedMoves;
    private static int _moveCount;
    private static Vec3 _spawner;
    private static int _seed;
    private static readonly List<Vec3> _taken = new();
    // SpawnBoss summons through the positional SpawnEnemy, so both postfixes see one spawn; the pointer set stops the
    // outer call from moving an enemy the inner call already placed.
    private static readonly HashSet<IntPtr> _movedBosses = new();

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // Called when a level's edits are applied, so an arming left over from a previous run can never move a later boss.
    public static void Disarm()
    {
        _armedFrame = null;
        _expectedMoves = 0;
        _moveCount = 0;
        _taken.Clear();
        _movedBosses.Clear();
    }

    [HarmonyPatch(typeof(InteractableBossSpawner), "Interact")]
    private static class InteractArmsTheRedirect
    {
        private static void Prefix(InteractableBossSpawner __instance)
        {
            if (!BossSpawnRedirect.ShouldArm(CustomLevelState.IsActive) || __instance == null)
            {
                return;
            }

            var curses = GameManager.Instance != null ? GameManager.Instance.bossCurses : 0;
            _expectedMoves = BossSpawnRedirect.ExpectedMoves(curses);
            _moveCount = 0;
            _taken.Clear();
            _movedBosses.Clear();
            var at = __instance.transform.position;
            _spawner = new Vec3(at.x, at.y, at.z);
            _seed = Environment.TickCount;
            _armedFrame = Time.frameCount;
            _logger?.Msg($"BossSpawnRedirect: armed at spawner ({at.x:0.###}, {at.y:0.###}, {at.z:0.###}), " +
                         $"expecting {_expectedMoves} boss(es) at frame {Time.frameCount}.");
        }
    }

    [HarmonyPatch(typeof(EnemyManager), "SpawnBoss")]
    private static class SpawnBossMovesTheBoss
    {
        private static void Postfix(Enemy __result, Vector3 pos) => MoveIfArmed(__result, pos, "SpawnBoss");
    }

    // SpawnBoss summons through this overload, so a spawner that goes straight to it is caught too.
    [HarmonyPatch(typeof(EnemyManager), "SpawnEnemy", new[]
    {
        typeof(EnemyData), typeof(Vector3), typeof(int), typeof(bool), typeof(EEnemyFlag), typeof(bool), typeof(float),
    })]
    private static class SpawnEnemyMovesTheBoss
    {
        private static void Postfix(Enemy __result, Vector3 pos) => MoveIfArmed(__result, pos, "SpawnEnemy");
    }

    private static void MoveIfArmed(Enemy boss, Vector3 requested, string via)
    {
        if (!_armedFrame.HasValue)
        {
            return;
        }

        var frame = Time.frameCount;

        if (BossSpawnRedirect.ShouldExpire(_armedFrame, _expectedMoves, _moveCount, frame))
        {
            if (_moveCount < _expectedMoves)
            {
                _logger?.Msg($"BossSpawnRedirect: window expired at frame {frame} after {_moveCount}/{_expectedMoves} moves.");
            }
            _armedFrame = null;
            return;
        }

        if (!BossSpawnRedirect.ShouldConsume(_armedFrame, frame))
        {
            return;
        }

        if (boss == null || !boss.IsBoss())
        {
            return;
        }

        if (!_movedBosses.Add(boss.Pointer))
        {
            return;
        }

        if (!TryFindSpot(boss, out var floor))
        {
            _logger?.Msg($"BossSpawnRedirect: no usable interior spot for the boss spawned via {via}, left alone.");
            return;
        }

        var from = boss.transform.position;
        var placed = BossSpawnRedirect.FloorPlacement(floor,
            new Vec3(requested.x, requested.y, requested.z),
            new Vec3(from.x, from.y, from.z));

        boss.transform.position = new Vector3(placed.X, placed.Y, placed.Z);
        if (boss.rb != null)
        {
            boss.rb.velocity = Vector3.zero;
        }

        _taken.Add(floor);
        _moveCount++;
        _logger?.Msg($"BossSpawnRedirect: boss {_moveCount}/{_expectedMoves} moved from ({from.x:0.###}, {from.y:0.###}, {from.z:0.###}) to " +
                     $"({placed.X:0.###}, {placed.Y:0.###}, {placed.Z:0.###}) via {via}.");

        if (BossSpawnRedirect.ShouldExpire(_armedFrame, _expectedMoves, _moveCount, frame))
        {
            _armedFrame = null;
        }
    }

    // Collects every usable ring spot (each copy draws its own ring, seeded by move count) and keeps the one
    // farthest from the copies already placed. See BossSpawnRedirect.PickSpot.
    private static bool TryFindSpot(Enemy boss, out Vec3 floorPoint)
    {
        floorPoint = default;
        var killFloorY = LiveEditPatch.KillFloorY ?? float.MinValue;
        var top = _spawner.Y + 20f;
        var usable = new List<Vec3>();

        foreach (var candidate in BossSpawnRedirect.CandidateRing(_spawner, _seed + _moveCount * SeedPerCopy, CandidatesPerBoss))
        {
            if (!BossSpawnRedirect.SpotUsable(candidate, _spawner, killFloorY, _taken))
            {
                continue;
            }

            var hits = Physics.RaycastAll(new Ray(new Vector3(candidate.X, top, candidate.Z), Vector3.down),
                top - (killFloorY == float.MinValue ? -100f : killFloorY - 5f), ~0, QueryTriggerInteraction.Ignore);
            var best = float.MinValue;
            foreach (var hit in hits)
            {
                if (hit.normal.y < WalkableNormalY || hit.collider.transform.IsChildOf(boss.transform))
                {
                    continue;
                }

                if (hit.point.y > best) best = hit.point.y;
            }

            if (best == float.MinValue)
            {
                continue;
            }

            var spot = new Vec3(candidate.X, best, candidate.Z);
            if (!BossSpawnRedirect.SpotUsable(spot, _spawner, killFloorY, _taken) || !PlacementProbe.ClearPoint(new Vector3(spot.X, spot.Y, spot.Z)))
            {
                continue;
            }

            usable.Add(spot);
        }

        return BossSpawnRedirect.PickSpot(usable, _taken, out floorPoint);
    }
}
