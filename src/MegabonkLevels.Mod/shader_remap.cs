using System;
using System.Collections.Generic;

namespace MegabonkLevels;

public enum PropertyKind
{
    Texture,
    Color,
}

// Keyword, when set, is enabled on the target material only if the copied value is non-empty (a texture, or a non-black color).
public readonly record struct PropertyCopy(string From, string To, PropertyKind Kind, string Keyword = null);

// Recognized is false when the authoring shader was missing or unknown, so the caller can warn once.
public sealed class ShaderRemapPlan
{
    public ShaderRemapPlan(string targetShader, IReadOnlyList<PropertyCopy> copies, IReadOnlyList<string> baseKeywords, bool recognized)
    {
        TargetShader = targetShader;
        Copies = copies;
        BaseKeywords = baseKeywords;
        Recognized = recognized;
    }

    public string TargetShader { get; }

    public IReadOnlyList<PropertyCopy> Copies { get; }

    public IReadOnlyList<string> BaseKeywords { get; }

    public bool Recognized { get; }
}

// Chooses the game shader and property copies for a pack material; see docs/asset-bundles.md.
public static class ShaderRemap
{
    public const string TargetShader = "MK/Toon/Built-in/Standard/Simple + Outline";

    private const string AlbedoKeyword = "_MK_ALBEDO_MAP";
    private const string EmissionKeyword = "_MK_EMISSION";

    // Keywords every textured in-game MK.Toon Simple + Outline material carries; the build only keeps shader variants for keyword sets the game itself uses.
    private static readonly string[] BaseKeywords =
    {
        "_MK_LIGHT_CEL", "_MK_WRAPPED_DIFFUSE", "_WRAPPEDLIGHTING_ON", "_MK_RECEIVE_SHADOWS", "_RECEIVESHADOWS_ON", "_MK_ENVIRONMENT_REFLECTIONS_AMBIENT", "_MK_ARTISTIC_ANIMATION_STUTTER",
    };

    private static readonly string[] GameShaderPrefixes = { "MK/Toon/", "Toon/", "Sprites/", "UI/" };

    private static readonly string[] AuthoringShaderPrefixes = { "Standard", "Legacy Shaders/", "Unlit/", "Universal Render Pipeline/", "HDRP/" };

    private static readonly PropertyCopy[] BuiltInCopies =
    {
        new("_MainTex", "_AlbedoMap", PropertyKind.Texture, AlbedoKeyword),
        new("_Color", "_AlbedoColor", PropertyKind.Color),
        new("_BumpMap", "_NormalMap", PropertyKind.Texture),
        new("_EmissionMap", "_EmissionMap", PropertyKind.Texture, EmissionKeyword),
        new("_EmissionColor", "_EmissionColor", PropertyKind.Color, EmissionKeyword),
    };

    private static readonly PropertyCopy[] UrpCopies =
    {
        new("_BaseMap", "_AlbedoMap", PropertyKind.Texture, AlbedoKeyword),
        new("_BaseColor", "_AlbedoColor", PropertyKind.Color),
        new("_BumpMap", "_NormalMap", PropertyKind.Texture),
        new("_EmissionMap", "_EmissionMap", PropertyKind.Texture, EmissionKeyword),
        new("_EmissionColor", "_EmissionColor", PropertyKind.Color, EmissionKeyword),
    };

    // Returns null when the game already ships the shader and the material is left alone.
    public static ShaderRemapPlan PlanFor(string authoringShader)
    {
        if (string.IsNullOrEmpty(authoringShader) || authoringShader.StartsWith("Hidden/", StringComparison.Ordinal))
        {
            return new ShaderRemapPlan(TargetShader, BuiltInCopies, BaseKeywords, false);
        }

        if (StartsWithAny(authoringShader, GameShaderPrefixes))
        {
            return null;
        }

        var recognized = StartsWithAny(authoringShader, AuthoringShaderPrefixes);
        var copies = authoringShader.StartsWith("Universal Render Pipeline/", StringComparison.Ordinal) ? UrpCopies : BuiltInCopies;
        return new ShaderRemapPlan(TargetShader, copies, BaseKeywords, recognized);
    }

    private static bool StartsWithAny(string value, string[] prefixes)
    {
        foreach (var prefix in prefixes)
        {
            if (value.StartsWith(prefix, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }
}
