using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;
using UnityEngine;

namespace MegabonkLevels;

// Diagnostic for flat or white surfaces: the shader, keywords and textures of every material under the matching objects.
public static class MaterialDump
{
    public const string DefaultObject = "Warehouse";

    private static readonly string[] TextureProperties = { "_MainTex", "_AlbedoMap", "_BaseMap" };
    private static readonly string[] ColorProperties = { "_Color", "_AlbedoColor" };

    public static JsonObject Build(string objectName)
    {
        var filter = objectName ?? DefaultObject;
        var seen = new HashSet<int>();
        var materials = new JsonArray();
        var shaders = new Dictionary<string, int>();
        var keywordSets = new Dictionary<string, int>();
        var withoutTexture = 0;
        var renderers = 0;

        foreach (var renderer in UnityEngine.Object.FindObjectsOfType<Renderer>())
        {
            if (!HasAncestorNamed(renderer.transform, filter))
            {
                continue;
            }

            renderers++;
            foreach (var material in renderer.sharedMaterials)
            {
                if (material == null || !seen.Add(material.GetInstanceID()))
                {
                    continue;
                }

                var entry = Describe(material);
                materials.Add(entry);
                Count(shaders, entry["shader"]!.GetValue<string>());
                Count(keywordSets, string.Join(" ", entry["keywords"]!.AsArray().Select(k => k!.GetValue<string>())));
                if (!entry["textures"]!.AsObject().Any(t => t.Value != null))
                {
                    withoutTexture++;
                }
            }
        }

        return new JsonObject
        {
            ["object"] = filter,
            ["renderers"] = renderers,
            ["materialCount"] = materials.Count,
            ["withoutTexture"] = withoutTexture,
            ["shaders"] = ToObject(shaders),
            ["keywordSets"] = ToObject(keywordSets),
            ["materials"] = materials,
        };
    }

    private static bool HasAncestorNamed(Transform transform, string filter)
    {
        for (var current = transform; current != null; current = current.parent)
        {
            if (current.name.Contains(filter, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

    private static JsonObject Describe(Material material)
    {
        var textures = new JsonObject();
        foreach (var property in TextureProperties.Where(material.HasProperty))
        {
            textures[property] = material.GetTexture(property)?.name;
        }

        var colors = new JsonObject();
        foreach (var property in ColorProperties.Where(material.HasProperty))
        {
            var color = material.GetColor(property);
            colors[property] = $"{color.r:0.##},{color.g:0.##},{color.b:0.##},{color.a:0.##}";
        }

        return new JsonObject
        {
            ["name"] = material.name,
            ["shader"] = material.shader != null ? material.shader.name : "(none)",
            ["keywords"] = new JsonArray(material.shaderKeywords.OrderBy(k => k, StringComparer.Ordinal).Select(k => (JsonNode)k).ToArray()),
            ["textures"] = textures,
            ["colors"] = colors,
            ["renderQueue"] = material.renderQueue,
        };
    }

    private static void Count(Dictionary<string, int> counts, string key) =>
        counts[key] = counts.TryGetValue(key, out var count) ? count + 1 : 1;

    private static JsonObject ToObject(Dictionary<string, int> counts)
    {
        var result = new JsonObject();
        foreach (var (key, count) in counts.OrderByDescending(c => c.Value))
        {
            result[key] = count;
        }

        return result;
    }
}
