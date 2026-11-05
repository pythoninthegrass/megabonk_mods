using Il2Cpp;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;

namespace MegabonkLevels;

// Logs the game's static boss events so a harness can match a boss spawn, death or defeat. Subscribed once at startup,
// so a level reload or a vanilla run never adds a second handler.
public static class BossEventPatch
{
    public static void Install(MelonLogger.Instance logger)
    {
        InteractableBossSpawner.A_BossSpawned += (Il2CppSystem.Action)(() => logger.Msg(BossEventLog.Format("A_BossSpawned")));
        InteractableBossSpawner.A_BossDefeated += (Il2CppSystem.Action<bool>)(flag => logger.Msg(BossEventLog.Format("A_BossDefeated", flag)));
        InteractableBossSpawner.A_NumBossesDefeated += (Il2CppSystem.Action<int>)(count => logger.Msg(BossEventLog.Format("A_NumBossesDefeated", count)));
        GraveyardBossRoom.A_BossDied += (Il2CppSystem.Action)(() => logger.Msg(BossEventLog.Format("A_BossDied")));
        EnemyManager.A_StageBossDied += (Il2CppSystem.Action)(() => logger.Msg(BossEventLog.Format("A_StageBossDied")));
    }
}
