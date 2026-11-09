namespace MegabonkLevels;

// Shared decisions for the live-enemy harness controls (render cull, physics freeze, animation cull): the arm sense and
// the rescan policy, so the three cannot drift apart the way the render verb's two arm conversions once did.
public static class EnemyControlPlan
{
    public const double RescanIntervalSeconds = 0.5;

    // Every control's wire bool says whether the thing is wanted; the control arms on the opposite sense.
    public static bool ArmsControl(bool enabledWanted) => !enabledWanted;

    // Rescan only when the population moved or the interval elapsed, so an armed control costs near nothing per frame.
    public static bool ShouldRescan(int liveEnemies, int lastSeenEnemies, double nowSeconds, double lastScanSeconds, double intervalSeconds)
        => liveEnemies != lastSeenEnemies || nowSeconds - lastScanSeconds >= intervalSeconds;
}
