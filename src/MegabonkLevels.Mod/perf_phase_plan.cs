using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// One timed PlayerLoop subsystem with the totals accumulated for it inside a window. The dotted path follows the loop
// tree from its root phase, e.g. FixedUpdate.PhysicsSimulation.
public sealed class PhaseSlot
{
    public string Path = "";

    public long Calls;

    public double TotalMs;

    public double MaxMs;
}

// Pure logic for the PlayerLoop phase timers: which nodes a wrap pass covers, and the window's report math. The
// Il2Cpp install that walks the live loop lives in perf_phases.cs.
public static class PerfPhasePlan
{
    public sealed class Node
    {
        public string Name = "";

        public List<Node> SubSystems = new();
    }

    // Depth-first dotted path for every node, roots first: this is the wrap list and the report order.
    public static List<string> Paths(IReadOnlyList<Node> roots)
    {
        var paths = new List<string>();
        Walk(roots, "", paths);
        return paths;
    }

    private static void Walk(IReadOnlyList<Node> systems, string prefix, List<string> paths)
    {
        foreach (var system in systems)
        {
            var path = prefix.Length == 0 ? system.Name : $"{prefix}.{system.Name}";
            paths.Add(path);
            Walk(system.SubSystems, path, paths);
        }
    }

    public static void Accumulate(PhaseSlot slot, double elapsedMs)
    {
        slot.Calls++;
        slot.TotalMs += elapsedMs;
        if (elapsedMs > slot.MaxMs)
        {
            slot.MaxMs = elapsedMs;
        }
    }

    // A parent's wrap covers its children, so self time is what the parent adds beyond them.
    public static double SelfMs(double totalMs, double childTotalMs) => Math.Max(0d, totalMs - childTotalMs);

    // GC pause per frame over a window; zero when no frame was sampled.
    public static double GcPauseMsPerFrame(double pauseDeltaMs, int frames) => frames <= 0 ? 0d : pauseDeltaMs / frames;
}
