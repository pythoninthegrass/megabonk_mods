using Assets.Scripts.Managers;

namespace MegabonkLevels;

// Dev-harness switch over EnemyManager.enabledWaves; enemies already alive stay, and a new scene builds a new manager with the default restored.
public static class EnemySpawns
{
    private static EnemyManager _disabledManager;

    public static bool Off => _disabledManager != null && ReferenceEquals(_disabledManager, EnemyManager.Instance) && !_disabledManager.enabledWaves;

    public static void Set(bool enabled, ModLogger logger)
    {
        var manager = EnemyManager.Instance;
        if (manager == null)
        {
            logger.Warning($"DevHarness: spawns {(enabled ? "on" : "off")} ignored, no EnemyManager in the scene.");
            return;
        }

        manager.enabledWaves = enabled;
        _disabledManager = enabled ? null : manager;
        logger.Msg($"DevHarness: enemy spawns {(enabled ? "on" : "off")}, enabledWaves={manager.enabledWaves}, numEnemies={manager.numEnemies}.");
    }
}
