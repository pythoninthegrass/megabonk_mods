using System.Collections.Generic;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Draws a ground tile with a biome's terrain material where the level's ground zones say so; cliff and fill pieces keep their own look.
public static class GroundSkin
{
    private const string GroundMaterialPrefix = "m_topGrass";
    private static readonly HashSet<string> s_missing = new();
    private static Dictionary<string, Material> s_materials;

    public static void Apply(GameObject tile, int x, int z, IReadOnlyList<GroundZone> zones, MelonLogger.Instance logger)
    {
        var name = GroundZones.MaterialAt(zones, x, z);
        if (name == null) return;
        var material = Find(name);
        if (material == null)
        {
            if (s_missing.Add(name)) logger.Warning($"GroundSkin: no material named '{name}'; ground zone left as it was");
            return;
        }

        foreach (var renderer in tile.GetComponentsInChildren<MeshRenderer>(true))
        {
            var current = renderer.sharedMaterial;
            if (current != null && current.name.StartsWith(GroundMaterialPrefix)) renderer.sharedMaterial = material;
        }
    }

    private static Material Find(string name)
    {
        if (s_materials == null || !s_materials.TryGetValue(name, out var cached) || cached == null)
        {
            s_materials = new Dictionary<string, Material>();
            foreach (var material in Resources.FindObjectsOfTypeAll<Material>())
            {
                if (material != null && !s_materials.ContainsKey(material.name)) s_materials[material.name] = material;
            }
        }

        return s_materials.TryGetValue(name, out var found) ? found : null;
    }
}
