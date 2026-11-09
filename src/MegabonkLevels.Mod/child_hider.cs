using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace MegabonkLevels;

// Switches off the renderers and colliders of every child whose name is listed, so the object keeps its other parts.
public static class ChildHider
{
    public static void Hide(GameObject go, IReadOnlyList<string> names, ModLogger logger)
    {
        if (names == null || names.Count == 0)
        {
            return;
        }

        foreach (var child in go.GetComponentsInChildren<Transform>(true))
        {
            if (!names.Contains(child.name))
            {
                continue;
            }

            foreach (var renderer in child.GetComponents<Renderer>())
            {
                renderer.enabled = false;
            }

            foreach (var collider in child.GetComponents<Collider>())
            {
                collider.enabled = false;
            }

            logger?.Msg($"LiveEdit: hid child '{child.name}' of '{go.name}'");
        }
    }
}
