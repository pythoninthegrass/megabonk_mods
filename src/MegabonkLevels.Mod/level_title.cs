using System;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace MegabonkLevels;

// Replaces the stage name and description on the run-start banner and run-config panel for custom runs; see docs/level-format.md.
public static class LevelTitle
{
    private static MelonLogger.Instance _logger;

    // The level's title and description as loaded, kept so an editor save writes them back.
    public static string Title { get; private set; }
    public static string Description { get; private set; }

    public static void Prepare(string title, string description, MelonLogger.Instance logger)
    {
        _logger = logger;
        Title = title;
        Description = description;
    }

    [HarmonyPatch(typeof(MapTitle), "GetTitle")]
    private static class GetTitlePostfix
    {
        private static void Postfix(ref string __result)
        {
            if (Title != null && CustomLevelState.IsActive)
            {
                __result = Title;
            }
        }
    }

    [HarmonyPatch(typeof(MapTitle), "GetDescription")]
    private static class GetDescriptionPostfix
    {
        private static void Postfix(ref string __result)
        {
            if (Description != null && CustomLevelState.IsActive)
            {
                __result = Description;
            }
        }
    }

    [HarmonyPatch(typeof(StageData), nameof(StageData.GetDescription))]
    private static class StageDescriptionPostfix
    {
        private static void Postfix(ref string __result)
        {
            if (Description != null && CustomLevelState.IsActive)
            {
                __result = Description;
            }
        }
    }

    [HarmonyPatch(typeof(RunConfigUi), "Start")]
    private static class RunConfigUiStartPostfix
    {
        private static void Postfix(RunConfigUi __instance)
        {
            if (Title == null || !CustomLevelState.IsActive)
            {
                return;
            }

            try
            {
                __instance.t_mapName.text = Title;
            }
            catch (Exception ex)
            {
                _logger?.Warning($"Title: could not set the run-config map name: {ex.Message}.");
            }
        }
    }
}
