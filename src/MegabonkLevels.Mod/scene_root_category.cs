using System;

namespace MegabonkLevels;

// Names the generator-index category of a scene root spawned after the tile objects parent.
public static class SceneRootCategory
{
    private const string CloneSuffix = "(Clone)";
    private const string ObjectPrefix = "object:";
    private const string SceneryPrefix = "scenery:";
    // The fog-of-war sphere is part of the run, not decoration, so it stays out of the index.
    private const string FogOfWarSphereName = "FogOfWarSphere";

    // "object:<prefab>" for a spawned prefab clone, "scenery:<name>" for an uncloned decoration root, null for a root the index leaves alone.
    public static string Of(string rootName)
    {
        if (rootName == FogOfWarSphereName)
        {
            return null;
        }

        return rootName.EndsWith(CloneSuffix, StringComparison.Ordinal)
            ? ObjectPrefix + rootName.Substring(0, rootName.Length - CloneSuffix.Length)
            : SceneryPrefix + rootName;
    }
}
