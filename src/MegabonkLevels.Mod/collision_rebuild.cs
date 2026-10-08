using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.MapGeneration.ProceduralTiles;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// The game bakes all ground collision into one CombinedCollisionMesh at generation time and then strips the per-piece
// MeshColliders, so tiles edited afterwards keep the old collision. Rebuild re-attaches each live piece's prefab collider
// mesh, runs the game's own MeshColliderCombiner, and strips the temporary colliders again.
public static class CollisionRebuild
{
    // Replaces tileGen.collider with a collision mesh built from the live pieces.
    public static void Replace(ProceduralTileGeneration tileGen, MelonLogger.Instance logger)
    {
        var previous = tileGen.collider;
        var combined = Build(tileGen, logger);
        if (combined == null)
        {
            logger.Warning("CollisionRebuild: combiner returned nothing; keeping the original collision");
            return;
        }

        tileGen.collider = combined;
        if (previous != null)
        {
            UnityEngine.Object.Destroy(previous);
        }
    }

    private static GameObject Build(ProceduralTileGeneration tileGen, MelonLogger.Instance logger)
    {
        var meshes = PrefabColliderMeshes(tileGen);
        var pieces = new Il2CppSystem.Collections.Generic.List<GameObject>();
        var temporary = new List<MeshCollider>();

        foreach (var list in new[] { tileGen.tiles, tileGen.flatTiles, tileGen.fillTiles })
        {
            for (var i = 0; i < list.Count; i++)
            {
                var piece = list[i];
                if (piece == null || !piece.activeInHierarchy || !meshes.TryGetValue(StripClone(piece.name), out var mesh))
                {
                    continue;
                }

                var existing = piece.GetComponent<MeshCollider>();
                if (existing == null)
                {
                    existing = piece.AddComponent<MeshCollider>();
                    existing.sharedMesh = mesh;
                    temporary.Add(existing);
                }

                pieces.Add(piece);
            }
        }

        var combined = MeshColliderCombiner.CombineMeshes(pieces);
        foreach (var collider in temporary)
        {
            UnityEngine.Object.Destroy(collider);
        }

        logger.Msg($"CollisionRebuild: combined {pieces.Count} pieces ({temporary.Count} temporary colliders)");
        return combined;
    }

    private static Dictionary<string, Mesh> PrefabColliderMeshes(ProceduralTileGeneration tileGen)
    {
        var result = new Dictionary<string, Mesh>();
        foreach (var prefab in new[] { tileGen.flatTile, tileGen.slopeTile, tileGen.wallFlat, tileGen.wallLeftUp, tileGen.wallLeftDown, tileGen.wallLeftCross })
        {
            var collider = prefab == null ? null : prefab.GetComponent<MeshCollider>();
            if (collider != null && collider.sharedMesh != null)
            {
                result[prefab.name] = collider.sharedMesh;
            }
        }

        return result;
    }

    private static string StripClone(string name) =>
        name.EndsWith("(Clone)", System.StringComparison.Ordinal) ? name.Substring(0, name.Length - "(Clone)".Length) : name;
}
