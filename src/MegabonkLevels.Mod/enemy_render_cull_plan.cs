using System.Collections.Generic;

namespace MegabonkLevels;

// Pure decisions for the enemy render cull; the Unity-side enumeration and Renderer writes live in enemy_render_cull.cs.
public static class EnemyRenderCullPlan
{
    // The verb's bool says whether enemy rendering is wanted; the cull arms on the opposite sense. One place, so the
    // harness arms and the arms a sweep labels cannot drift apart.
    public static bool ArmsCull(bool renderEnabled) => !renderEnabled;

    // Rescan only when the population moved or the interval elapsed, so an armed cull costs near nothing per frame.
    public static bool ShouldRescan(int liveEnemies, int lastSeenEnemies, double nowSeconds, double lastScanSeconds, double intervalSeconds)
        => liveEnemies != lastSeenEnemies || nowSeconds - lastScanSeconds >= intervalSeconds;

    // Renderers the game has enabled right now, including ones we disabled that it turned back on.
    public static List<int> ToDisable(IEnumerable<(int InstanceId, bool Enabled)> renderers)
    {
        var ids = new List<int>();
        foreach (var (instanceId, enabled) in renderers)
        {
            if (enabled)
            {
                ids.Add(instanceId);
            }
        }

        return ids;
    }

    // Checksum of live enemy positions; two samples a moment apart show whether the swarm still moves while culled.
    public static double PositionSum(IEnumerable<(float X, float Y, float Z)> positions)
    {
        var sum = 0d;
        foreach (var (x, y, z) in positions)
        {
            sum += x + y + z;
        }

        return sum;
    }
}
