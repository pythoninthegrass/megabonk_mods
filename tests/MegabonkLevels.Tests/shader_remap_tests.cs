namespace MegabonkLevels.Tests;

public class ShaderRemapTests
{
    private const string Target = "MK/Toon/Built-in/Standard/Simple + Outline";

    private static PropertyCopy Copy(ShaderRemapPlan plan, string from) => plan.Copies.Single(c => c.From == from);

    [Theory]
    [InlineData("Standard")]
    [InlineData("Standard (Specular setup)")]
    [InlineData("Legacy Shaders/Diffuse")]
    [InlineData("Legacy Shaders/Bumped Diffuse")]
    [InlineData("Legacy Shaders/Transparent/Cutout/Diffuse")]
    [InlineData("Unlit/Texture")]
    [InlineData("Universal Render Pipeline/Lit")]
    [InlineData("Universal Render Pipeline/Simple Lit")]
    [InlineData("HDRP/Lit")]
    public void PlanFor_AuthoringShader_TargetsTheGameToonShader(string shader)
    {
        var plan = ShaderRemap.PlanFor(shader);

        Assert.NotNull(plan);
        Assert.Equal(Target, plan.TargetShader);
        Assert.True(plan.Recognized);
    }

    [Theory]
    [InlineData("MK/Toon/Built-in/Standard/Simple")]
    [InlineData("MK/Toon/Built-in/Standard/Simple + Outline")]
    [InlineData("MK/Toon/Built-in/Particles/Simple")]
    [InlineData("Toon/Lit Tri Planar Normal")]
    [InlineData("Sprites/Default")]
    [InlineData("UI/Default")]
    public void PlanFor_ShaderTheGameShips_KeepsIt(string shader)
    {
        Assert.Null(ShaderRemap.PlanFor(shader));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("Hidden/InternalErrorShader")]
    [InlineData("Custom/Whatever")]
    public void PlanFor_MissingOrUnknownShader_FallsBackToTheDefaultAndIsNotRecognized(string shader)
    {
        var plan = ShaderRemap.PlanFor(shader);

        Assert.NotNull(plan);
        Assert.Equal(Target, plan.TargetShader);
        Assert.False(plan.Recognized);
    }

    [Fact]
    public void PlanFor_Standard_MapsAlbedoNormalAndEmission()
    {
        var plan = ShaderRemap.PlanFor("Standard");

        Assert.Equal(("_AlbedoMap", PropertyKind.Texture), (Copy(plan, "_MainTex").To, Copy(plan, "_MainTex").Kind));
        Assert.Equal(("_AlbedoColor", PropertyKind.Color), (Copy(plan, "_Color").To, Copy(plan, "_Color").Kind));
        Assert.Equal("_NormalMap", Copy(plan, "_BumpMap").To);
        Assert.Equal("_EmissionMap", Copy(plan, "_EmissionMap").To);
        Assert.Equal(("_EmissionColor", PropertyKind.Color), (Copy(plan, "_EmissionColor").To, Copy(plan, "_EmissionColor").Kind));
    }

    [Fact]
    public void PlanFor_UrpLit_MapsBaseMapAndBaseColor()
    {
        var plan = ShaderRemap.PlanFor("Universal Render Pipeline/Lit");

        Assert.Equal("_AlbedoMap", Copy(plan, "_BaseMap").To);
        Assert.Equal("_AlbedoColor", Copy(plan, "_BaseColor").To);
        Assert.Equal("_NormalMap", Copy(plan, "_BumpMap").To);
    }

    [Fact]
    public void PlanFor_UnknownShader_StillCopiesTheCommonProperties()
    {
        var plan = ShaderRemap.PlanFor("Custom/Whatever");

        Assert.Equal("_AlbedoMap", Copy(plan, "_MainTex").To);
        Assert.Equal("_AlbedoColor", Copy(plan, "_Color").To);
    }

    [Theory]
    [InlineData("Standard")]
    [InlineData("Universal Render Pipeline/Lit")]
    [InlineData("Custom/Whatever")]
    public void PlanFor_AnyRemap_EnablesTheKeywordsTheGamesOwnMaterialsUse(string shader)
    {
        var plan = ShaderRemap.PlanFor(shader);

        Assert.Equal(
            new[] { "_MK_LIGHT_CEL", "_MK_WRAPPED_DIFFUSE", "_WRAPPEDLIGHTING_ON", "_MK_RECEIVE_SHADOWS", "_RECEIVESHADOWS_ON", "_MK_ENVIRONMENT_REFLECTIONS_AMBIENT", "_MK_ARTISTIC_ANIMATION_STUTTER" },
            plan.BaseKeywords);
    }

    [Fact]
    public void PlanFor_AlbedoAndEmissionCopies_NameTheKeywordTheyEnable()
    {
        var plan = ShaderRemap.PlanFor("Standard");

        Assert.Equal("_MK_ALBEDO_MAP", Copy(plan, "_MainTex").Keyword);
        Assert.Equal("_MK_EMISSION", Copy(plan, "_EmissionMap").Keyword);
        Assert.Equal("_MK_EMISSION", Copy(plan, "_EmissionColor").Keyword);
        Assert.Null(Copy(plan, "_Color").Keyword);
        Assert.Null(Copy(plan, "_BumpMap").Keyword);
    }

    [Fact]
    public void PlanFor_EveryCopy_HasADistinctSourceProperty()
    {
        foreach (var shader in new[] { "Standard", "Universal Render Pipeline/Lit", "Custom/Whatever" })
        {
            var sources = ShaderRemap.PlanFor(shader).Copies.Select(c => c.From).ToList();

            Assert.Equal(sources.Count, sources.Distinct().Count());
        }
    }
}
