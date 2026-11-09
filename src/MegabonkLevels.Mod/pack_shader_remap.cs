using System.Collections.Generic;
using UnityEngine;

namespace MegabonkLevels;

// Swaps pack materials onto the game's toon shader at load time, copying the properties ShaderRemap maps; see docs/asset-bundles.md.
public static class PackShaderRemap
{
    private static readonly Dictionary<int, Material> Remapped = new();
    private static readonly HashSet<string> Warned = new();

    public static void Apply(GameObject prefab, ModLogger logger)
    {
        foreach (var renderer in prefab.GetComponentsInChildren<Renderer>(true))
        {
            var materials = renderer.sharedMaterials;
            var changed = false;
            for (var i = 0; i < materials.Length; i++)
            {
                var replacement = Remap(materials[i], prefab.name, logger);
                if (replacement != null)
                {
                    materials[i] = replacement;
                    changed = true;
                }
            }

            if (changed)
            {
                renderer.sharedMaterials = materials;
            }
        }
    }

    private static Material Remap(Material source, string prefabName, ModLogger logger)
    {
        var shaderName = source != null && source.shader != null ? source.shader.name : null;
        var plan = ShaderRemap.PlanFor(shaderName);
        if (plan == null)
        {
            return null;
        }

        if (source != null && Remapped.TryGetValue(source.GetInstanceID(), out var cached) && cached != null)
        {
            return cached;
        }

        var target = Shader.Find(plan.TargetShader);
        if (target == null)
        {
            logger.Warning($"Packs: shader '{plan.TargetShader}' not found; '{prefabName}' keeps its authoring materials.");
            return null;
        }

        if (!plan.Recognized && Warned.Add($"{prefabName}:{shaderName}"))
        {
            logger.Warning($"Packs: '{prefabName}' uses unrecognized shader '{shaderName ?? "(none)"}'; remapping with the default property copies.");
        }

        var material = new Material(target) { name = source != null ? source.name : $"{prefabName}-remapped" };
        foreach (var keyword in plan.BaseKeywords)
        {
            material.EnableKeyword(keyword);
        }

        if (source != null)
        {
            CopyProperties(source, material, plan);
            Remapped[source.GetInstanceID()] = material;
        }

        return material;
    }

    private static void CopyProperties(Material source, Material destination, ShaderRemapPlan plan)
    {
        foreach (var copy in plan.Copies)
        {
            if (!source.HasProperty(copy.From) || !destination.HasProperty(copy.To))
            {
                continue;
            }

            bool hasValue;
            if (copy.Kind == PropertyKind.Texture)
            {
                var texture = source.GetTexture(copy.From);
                hasValue = texture != null;
                destination.SetTexture(copy.To, texture);
                destination.SetTextureScale(copy.To, source.GetTextureScale(copy.From));
                destination.SetTextureOffset(copy.To, source.GetTextureOffset(copy.From));
            }
            else
            {
                var color = source.GetColor(copy.From);
                hasValue = color.r > 0f || color.g > 0f || color.b > 0f;
                destination.SetColor(copy.To, color);
            }

            if (hasValue && copy.Keyword != null)
            {
                destination.EnableKeyword(copy.Keyword);
            }
        }
    }
}
