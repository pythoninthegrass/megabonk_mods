using System;
using System.Collections.Generic;
using System.Linq;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Chests;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

public static class InteractableRandomizationPatch
{
    public static void Apply(LevelFile settings, IReadOnlyDictionary<string, GameObject> index, IReadOnlyList<EditOp> edits,
        LevelState state, ProceduralTileGeneration tiles, MeshCollider ground, IReadOnlyList<float> playerStart, MelonLogger.Instance logger)
    {
        if (!InteractableRandomization.Enabled(settings)) return;
        if (tiles == null || ground == null || state.Tiles.Count == 0)
        {
            logger.Warning("InteractableRandomization: no tile ground available; keeping original placements");
            return;
        }

        Physics.SyncTransforms();
        var start = playerStart is { Count: 3 }
            ? new Vector3(playerStart[0], playerStart[1], playerStart[2])
            : MapGenerationController.tileSpawnPosition;
        var points = PlacementProbe.ReachablePoints(state, tiles, ground, start, logger);
        var random = new System.Random(Guid.NewGuid().GetHashCode());
        var moved = 0;
        var targets = index.Where(pair => ObjectTools.IsPickableGenId(pair.Key) && pair.Value != null && pair.Value.activeInHierarchy)
            .Select(pair => (GenId: pair.Key, Object: pair.Value, Kind: Kind(pair.Value)))
            .Where(target => target.Kind != null && InteractableRandomization.ShouldMove(settings, target.Kind.Value, target.GenId, edits))
            .OrderBy(target => target.Kind == RandomizedInteractableKind.Chest ? 1 : 0);
        foreach (var (genId, go, selectedKind) in targets)
        {
            var kind = selectedKind.Value;
            if (!PlacementProbe.GroundHit(ground, go.transform.position, out var originalHit, false))
            {
                logger.Warning($"InteractableRandomization: {genId} has no usable ground; keeping original placement");
                continue;
            }

            var original = go.transform.position;
            var originalSurface = originalHit.point;
            var originalRotation = go.transform.rotation;
            var axis = InteractableRandomization.LocalUp(kind);
            var modelUp = originalRotation * new Vector3(axis.X, axis.Y, axis.Z);
            var upright = Quaternion.FromToRotation(modelUp, Vector3.up) * originalRotation;
            go.transform.rotation = upright;
            Physics.SyncTransforms();
            if (!PlacementProbe.TryBounds(go, out var bounds))
            {
                go.transform.rotation = originalRotation;
                Physics.SyncTransforms();
                logger.Warning($"InteractableRandomization: {genId} has no usable bounds; keeping original placement");
                continue;
            }
            var offset = original.y - originalSurface.y;
            var candidates = points.Values.ToList();
            var position = original;
            bool Valid(Vector3 center)
            {
                var width = tiles.currentMapParameters.scaledTileWidth / PlacementProbe.SamplesPerTile;
                var sample = center + new Vector3((float)(random.NextDouble() - 0.5) * width * 0.5f, 0,
                    (float)(random.NextDouble() - 0.5) * width * 0.5f);
                if (!PlacementProbe.Surface(ground, sample, out var floor) || Vector3.Distance(floor, originalSurface) < 8
                    || !PlacementProbe.ClearPath(ground, center, floor, go.transform)) return false;
                var next = floor + Vector3.up * offset;
                var displaced = new Bounds(bounds.center + next - original, bounds.size);
                if (!PlacementProbe.Supported(ground, displaced, floor.y) || !PlacementProbe.Unoccupied(displaced, floor.y, go.transform)
                    || PlacementProbe.OverlapsObjects(displaced, go, index)) return false;
                position = next;
                return true;
            }

            if (!InteractableRandomization.TryChoose(candidates, random.Next, Valid, 256, out _))
            {
                go.transform.rotation = originalRotation;
                Physics.SyncTransforms();
                logger.Warning($"InteractableRandomization: {genId} has no safe reachable candidate; keeping original placement");
                continue;
            }
            go.transform.SetPositionAndRotation(position, upright);
            Physics.SyncTransforms();
            logger.Msg($"InteractableRandomization: {genId} {kind} {original.ToString("F3")} -> {position.ToString("F3")} groundOffset={offset:F3}");
            moved++;
        }
        logger.Msg($"InteractableRandomization: moved={moved} reachableFlatSamples={points.Count}");
    }

    private static RandomizedInteractableKind? Kind(GameObject go)
    {
        if (go.GetComponentInChildren<InteractableShadyGuy>() != null) return RandomizedInteractableKind.ShadyGuy;
        if (go.GetComponentInChildren<InteractableChest>() != null) return RandomizedInteractableKind.Chest;
        if (go.GetComponentInChildren<InteractableShrineMoai>() != null) return RandomizedInteractableKind.Moai;
        return null;
    }
}
