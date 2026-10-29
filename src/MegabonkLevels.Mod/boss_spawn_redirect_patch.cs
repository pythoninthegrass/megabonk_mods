using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Managers;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// The Warehouse's boss portal hangs inside the glass box above the main half pipe, hidden in plain sight. A spawner
// summons its boss at its own position, so the boss would appear in a box the player launches into and could never get
// out of. This intercepts the spawn the portal triggers and puts the boss on the ground instead, keeping the portal,
// its VFX and the Defeat the Boss wiring where the game put them.
public static class BossSpawnRedirectPatch
{
    private static MelonLogger.Instance _logger;
    private static int? _armedFrame;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // Called when a level's edits are applied, so an arming left over from a previous run can never move a later boss.
    public static void Disarm()
    {
        _armedFrame = null;
    }

    [HarmonyPatch(typeof(InteractableBossSpawner), "Interact")]
    private static class InteractArmsTheRedirect
    {
        private static void Prefix()
        {
            var target = LiveEditPatch.BossSpawnPosition;
            if (!BossSpawnRedirect.ShouldArm(CustomLevelState.IsActive, target))
            {
                return;
            }

            _armedFrame = Time.frameCount;
            _logger?.Msg($"BossSpawnRedirect: armed for ({target[0]:0.###}, {target[1]:0.###}, {target[2]:0.###}) at frame {Time.frameCount}.");
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
        var armedFrame = _armedFrame.Value;
        _armedFrame = null;
        if (!BossSpawnRedirect.ShouldConsume(armedFrame, frame))
        {
            _logger?.Msg($"BossSpawnRedirect: a boss spawned via {via} at frame {frame} but the redirect armed at {armedFrame}, left alone.");
            return;
        }

        var target = LiveEditPatch.BossSpawnPosition;
        if (!BossSpawnRedirect.IsUsablePosition(target) || boss == null)
        {
            _logger?.Msg("BossSpawnRedirect: no boss to move.");
            return;
        }

        var anchor = new Vec3(target[0], target[1], target[2]);
        var from = boss.transform.position;
        var placed = BossSpawnRedirect.Placement(
            anchor,
            new Vec3(requested.x, requested.y, requested.z),
            new Vec3(from.x, from.y, from.z));

        boss.transform.position = new Vector3(placed.X, placed.Y, placed.Z);
        if (boss.rb != null)
        {
            boss.rb.velocity = Vector3.zero;
        }

        _logger?.Msg($"BossSpawnRedirect: boss moved from ({from.x:0.###}, {from.y:0.###}, {from.z:0.###}) to " +
                     $"({placed.X:0.###}, {placed.Y:0.###}, {placed.Z:0.###}) via {via}.");
    }
}
