using System.Collections.Generic;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Pure report shapes for the probe attach status and the component census; the Unity-side counting lives in perf_probes.cs and perf_monitor.cs.
public static class PerfProbePlan
{
    // One census row per component type: scene counts components on active game objects, live those enabled and active in hierarchy, any all loaded instances including prefabs and inactive ones.
    public static JsonArray CensusNode(IEnumerable<(string Name, int Scene, int Live, int Any)> rows)
    {
        var array = new JsonArray();
        foreach (var (name, scene, live, any) in rows)
        {
            array.Add(new JsonObject { ["name"] = name, ["scene"] = scene, ["live"] = live, ["any"] = any });
        }

        return array;
    }

    // One row per probe target: whether Harmony reports the method as patched.
    public static JsonArray AttachNode(IEnumerable<(string Name, bool Patched)> rows)
    {
        var array = new JsonArray();
        foreach (var (name, patched) in rows)
        {
            array.Add(new JsonObject { ["name"] = name, ["patched"] = patched });
        }

        return array;
    }
}
