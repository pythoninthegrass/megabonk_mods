using System;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using MelonLoader;

namespace MegabonkLevels;

// Writes a blank from-scratch level into the levels folder and starts it through the normal level load; the live map is not touched.
public static class NewLevel
{
    public static JsonObject Create(string requestedName, NewLevelArgs args, MelonLogger.Instance logger)
    {
        var map = (EMap)args.Map;
        var mapData = LevelLoaderPatch.FindMapData(map) ?? throw new InvalidOperationException($"no MapData for map {map}");
        if (args.StageIndex >= mapData.stages.Length)
        {
            throw new ArgumentException($"stageIndex {args.StageIndex} is out of range for {map} ({mapData.stages.Length} stages)");
        }

        var parameters = mapData.stages[args.StageIndex].mapParameters;
        var level = BlankLevel.Create(map, args.StageIndex, args.Tier, args.Size, parameters.scaledTileWidth, GameBuildIdPatch.CurrentBuildId() ?? "");
        if (FromScratchLayout.SizeRefusal(level.Grid!.Value, parameters.size) is { } refusal)
        {
            throw new ArgumentException(refusal);
        }

        var name = EditorFileNaming.NewLevelFileName(requestedName, LiveEditPatch.ListLevelFiles());
        var path = Path.Combine(LiveEditPatch.LevelsDirectoryPath(), name);
        File.WriteAllText(path, LevelFileSerializer.Serialize(level));
        if (!LevelLoaderPatch.LoadAndStart(path, logger))
        {
            throw new InvalidOperationException($"could not start {name}");
        }

        EditorMode.RequestReenter(logger);
        logger.Msg($"NewLevel: wrote {name} ({args.Size}x{args.Size} {map} stage {args.StageIndex} tier {args.Tier}) and started it");
        return new JsonObject { ["name"] = name, ["path"] = path };
    }
}
