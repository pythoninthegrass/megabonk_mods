using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;
using UnityEngine;

namespace MegabonkLevels;

// Diagnostic for choosing pack remap targets: which candidate shaders resolve, and what shaders and properties the scene's materials use.
public static class ShaderReport
{
    private static readonly string[] Candidates =
    {
        "MK/Toon/Built-in/Standard/Simple",
        "MK/Toon/Built-in/Standard/Simple + Outline",
        "MK/Toon/Built-in/Standard/Physically Based + Outline",
        "MK/Toon/Built-in/Particles/Simple",
        "Toon/Lit Tri Planar Normal",
        "Toon/Lit Tri Planar Noise Blend",
        "Unlit/Texture",
        "Unlit/Color",
        "UnlitVertexColor",
        "Standard",
        "Standard (Specular setup)",
        "Legacy Shaders/Diffuse",
        "Legacy Shaders/VertexLit",
    };

    public static JsonObject Build()
    {
        var found = new JsonObject();
        foreach (var name in Candidates)
        {
            found[name] = Shader.Find(name) != null;
        }

        var materials = new Dictionary<string, (int Count, List<string> Properties)>();
        foreach (var renderer in Object.FindObjectsOfType<Renderer>())
        {
            foreach (var material in renderer.sharedMaterials)
            {
                if (material == null || material.shader == null)
                {
                    continue;
                }

                var shader = material.shader;
                var seen = materials.TryGetValue(shader.name, out var entry) ? entry : (0, PropertyNames(shader));
                materials[shader.name] = (seen.Item1 + 1, seen.Item2);
            }
        }

        var used = new JsonObject();
        foreach (var (name, entry) in materials.OrderByDescending(m => m.Value.Count))
        {
            used[name] = new JsonObject { ["materials"] = entry.Count, ["properties"] = new JsonArray(entry.Properties.Select(p => (JsonNode)p).ToArray()) };
        }

        return new JsonObject { ["found"] = found, ["inScene"] = used, ["mkKeywordSets"] = MkKeywordSets() };
    }

    // Keyword sets of loaded MK.Toon Standard materials, by shader and whether an albedo map is set, to see which shader variants the build kept.
    private static JsonObject MkKeywordSets()
    {
        var counts = new Dictionary<string, int>();
        foreach (var material in Resources.FindObjectsOfTypeAll<Material>())
        {
            if (material.shader == null || !material.shader.name.StartsWith("MK/Toon/Built-in/Standard/"))
            {
                continue;
            }

            var textured = material.HasProperty("_AlbedoMap") && material.GetTexture("_AlbedoMap") != null;
            var key = $"{material.shader.name} | albedo={textured} | {string.Join(",", material.shaderKeywords.OrderBy(k => k))}";
            counts[key] = counts.TryGetValue(key, out var n) ? n + 1 : 1;
        }

        var result = new JsonObject();
        foreach (var (key, count) in counts.OrderByDescending(c => c.Value).Take(12))
        {
            result[key] = count;
        }

        return result;
    }

    private static List<string> PropertyNames(Shader shader)
    {
        var names = new List<string>();
        for (var i = 0; i < shader.GetPropertyCount(); i++)
        {
            names.Add($"{shader.GetPropertyName(i)}:{shader.GetPropertyType(i)}");
        }

        return names;
    }
}
