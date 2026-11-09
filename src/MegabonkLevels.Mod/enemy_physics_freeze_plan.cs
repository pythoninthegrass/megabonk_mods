using System.Collections.Generic;

namespace MegabonkLevels;

// Pure decisions for the physics freeze; the Unity-side enumeration and Rigidbody writes live in enemy_physics_freeze.cs.
public static class EnemyPhysicsFreezePlan
{
    // enabled=false means the enemy's physics is not wanted, which is what arms the freeze.
    public static bool ArmsFreeze(bool physicsEnabled) => EnemyControlPlan.ArmsControl(physicsEnabled);

    public static bool ShouldRescan(int liveEnemies, int lastSeenEnemies, double nowSeconds, double lastScanSeconds, double intervalSeconds)
        => EnemyControlPlan.ShouldRescan(liveEnemies, lastSeenEnemies, nowSeconds, lastScanSeconds, intervalSeconds);

    // Bodies the solver is integrating right now, including ones we froze that the game made dynamic again.
    public static List<int> ToSetKinematic(IEnumerable<(int InstanceId, bool IsKinematic)> bodies)
    {
        var ids = new List<int>();
        foreach (var (instanceId, isKinematic) in bodies)
        {
            if (!isKinematic)
            {
                ids.Add(instanceId);
            }
        }

        return ids;
    }

    // What each body we freeze was before, so restore puts back the value it found rather than assuming dynamic.
    public static Dictionary<int, bool> PriorValues(IEnumerable<(int InstanceId, bool IsKinematic)> bodies)
    {
        var prior = new Dictionary<int, bool>();
        foreach (var (instanceId, isKinematic) in bodies)
        {
            if (!isKinematic && !prior.ContainsKey(instanceId))
            {
                prior[instanceId] = isKinematic;
            }
        }

        return prior;
    }

    // What the arm takes out besides the solver, so a reader cannot mistake the figure for a pure solver measurement.
    public static IReadOnlyList<string> Suppresses => new[]
    {
        "Unity's physics solver: a kinematic body is not integrated by it",
        "the body's contacts, and the broadphase work those contacts generate",
        "movement the game drives through Rigidbody.velocity, which a kinematic body ignores",
    };

    public static string FidelityNote()
        => "a kinematic swarm leaves the solver, the broadphase and its contacts, and stops translating if the game moves it through "
            + "Rigidbody.velocity: the figure is solver plus contacts plus movement, not the solver alone. Read it against the window's "
            + "enemy count and position sum to see how far the swarm still moved.";
}
