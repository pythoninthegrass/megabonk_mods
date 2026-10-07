using Il2Cpp;
using MelonLoader;

namespace MegabonkLevels;

// Subscribes to MapGenerationController.A_GenerationComplete and logs the seed and spawned-tile counts.
public static class GenerationPatch
{
    public static void Install(MelonLogger.Instance logger)
    {
        MapGenerationController.A_GenerationComplete += (Il2CppSystem.Action)(() => OnGenerationComplete(logger));
    }

    private static void OnGenerationComplete(MelonLogger.Instance logger)
    {
        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        var tiles = controller?.proceduralTileGeneration;
        var snapshot = new GenerationSnapshot(
            MapGenerationController.mapSeed,
            tiles?.tiles?.Count ?? -1,
            tiles?.flatTiles?.Count ?? -1,
            tiles?.fillTiles?.Count ?? -1);
        logger.Msg(GenerationReport.Format(snapshot));
    }
}
