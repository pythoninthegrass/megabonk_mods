using System.Collections.Generic;

namespace MegabonkLevels;

// Pure decisions for the animation cull; the Unity-side enumeration and Behaviour writes live in enemy_animation_cull.cs.
public static class EnemyAnimationCullPlan
{
    // enabled=false means the enemy's animation is not wanted, which is what arms the cull.
    public static bool ArmsCull(bool animationEnabled) => EnemyControlPlan.ArmsControl(animationEnabled);

    public static bool ShouldRescan(int liveEnemies, int lastSeenEnemies, double nowSeconds, double lastScanSeconds, double intervalSeconds)
        => EnemyControlPlan.ShouldRescan(liveEnemies, lastSeenEnemies, nowSeconds, lastScanSeconds, intervalSeconds);

    // Components the game has enabled right now, including ones we stopped that it turned back on.
    public static List<int> ToDisable(IEnumerable<(int InstanceId, bool Enabled)> behaviours)
    {
        var ids = new List<int>();
        foreach (var (instanceId, enabled) in behaviours)
        {
            if (enabled)
            {
                ids.Add(instanceId);
            }
        }

        return ids;
    }

    // How many of each animation component type the cull stopped, so the doc can say what an enemy actually carries.
    public static Dictionary<string, int> CountsByType(IEnumerable<(string Type, bool Enabled)> census)
    {
        var counts = new Dictionary<string, int>();
        foreach (var (type, enabled) in census)
        {
            if (!enabled)
            {
                continue;
            }

            counts[type] = counts.TryGetValue(type, out var seen) ? seen + 1 : 1;
        }

        return counts;
    }

    // What the arm takes out, so the figure is not read as animation-only when the swarm's reach changed with it.
    public static IReadOnlyList<string> Suppresses => new[]
    {
        "AnimatedMesh.Update: the mesh-swap ticker that advances each enemy's frames",
        "Animator.Update, on any enemy that carries an Animator",
        "whatever those updates drive, including how far the swarm reaches the player and so how much AI work it does",
    };

    public static string FidelityNote()
        => "only the animation components are stopped: renderers, colliders and the Rigidbody keep running. Stopping them can change "
            + "how far the swarm reaches the player, which changes AI work, so read the arm against its enemy count and position sum.";
}
