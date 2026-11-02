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
    private const float Clearance = 0.6f;
    private const int SamplesPerTile = 4;

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
        var points = ReachablePoints(state, tiles, ground, start, logger);
        var random = new System.Random(Guid.NewGuid().GetHashCode());
        var moved = 0;
        var targets = index.Where(pair => ObjectTools.IsPickableGenId(pair.Key) && pair.Value != null && pair.Value.activeInHierarchy)
            .Select(pair => (GenId: pair.Key, Object: pair.Value, Kind: Kind(pair.Value)))
            .Where(target => target.Kind != null && InteractableRandomization.ShouldMove(settings, target.Kind.Value, target.GenId, edits))
            .OrderBy(target => target.Kind == RandomizedInteractableKind.Chest ? 1 : 0);
        foreach (var (genId, go, selectedKind) in targets)
        {
            var kind = selectedKind.Value;
            if (!GroundHit(ground, go.transform.position, out var originalHit, false))
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
            if (!TryBounds(go, out var bounds))
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
                var width = tiles.currentMapParameters.scaledTileWidth / SamplesPerTile;
                var sample = center + new Vector3((float)(random.NextDouble() - 0.5) * width * 0.5f, 0,
                    (float)(random.NextDouble() - 0.5) * width * 0.5f);
                if (!Surface(ground, sample, out var floor) || Vector3.Distance(floor, originalSurface) < 8
                    || !ClearPath(ground, center, floor, go.transform)) return false;
                var next = floor + Vector3.up * offset;
                var displaced = new Bounds(bounds.center + next - original, bounds.size);
                if (!Supported(ground, displaced, floor.y) || !Unoccupied(displaced, floor.y, go.transform)
                    || OverlapsObjects(displaced, go, index)) return false;
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

    private static Dictionary<(int X, int Z), Vector3> ReachablePoints(LevelState state, ProceduralTileGeneration tiles, MeshCollider ground, Vector3 start, MelonLogger.Instance logger)
    {
        var centers = state.Tiles.Keys.ToDictionary(cell => cell,
            cell => tiles.TilePositionToWorldPosition(new Vector2Int(cell.X, cell.Z)));
        var startTile = centers.MinBy(pair => (pair.Value - start).sqrMagnitude).Key;
        var topology = ReachabilityValidator.Validate(state, startTile).Reachable;
        var spacing = tiles.currentMapParameters.scaledTileWidth;
        var positions = new Dictionary<(int X, int Z), Vector3>();
        foreach (var cell in topology)
        for (var x = 0; x < SamplesPerTile; x++)
        for (var z = 0; z < SamplesPerTile; z++)
        {
            var p = centers[cell] + new Vector3(((x + 0.5f) / SamplesPerTile - 0.5f) * spacing, 0,
                ((z + 0.5f) / SamplesPerTile - 0.5f) * spacing);
            if (Surface(ground, p, out var floor, false) && ClearPoint(floor))
                positions[(cell.X * SamplesPerTile + x, cell.Z * SamplesPerTile + z)] = floor;
        }
        if (positions.Count == 0) return positions;
        if (!Surface(ground, start, out var startFloor, false))
            return new Dictionary<(int X, int Z), Vector3>();
        var starts = positions.Where(pair => pair.Key.X / SamplesPerTile == startTile.X && pair.Key.Z / SamplesPerTile == startTile.Z)
            .OrderBy(pair => (pair.Value - startFloor).sqrMagnitude).ToList();
        var first = starts.FindIndex(pair => ClearPath(ground, startFloor, pair.Value, null));
        if (first < 0) return new Dictionary<(int X, int Z), Vector3>();
        var visited = InteractableRandomization.ReachableSamples(positions, starts[first].Key, (from, to) => ClearPath(ground, from, to, null));
        logger.Msg($"InteractableRandomization: walkableSamples={positions.Count} reachableSamples={visited.Count}");
        return positions.Where(pair => visited.Contains(pair.Key)
                && state.Tiles[(pair.Key.X / SamplesPerTile, pair.Key.Z / SamplesPerTile)].Slope == SlopeDirection.None)
            .ToDictionary(pair => pair.Key, pair => pair.Value);
    }

    private static bool ClearPoint(Vector3 point)
    {
        foreach (var collider in Physics.OverlapSphere(point + Vector3.up * 1.2f, Clearance, ~0, QueryTriggerInteraction.Ignore))
        {
            if (collider != null && !IsTraversalExempt(collider.transform)) return false;
        }
        return true;
    }

    private static bool Surface(MeshCollider ground, Vector3 point, out Vector3 floor, bool flat = true)
    {
        if (GroundHit(ground, point, out var hit, flat))
        {
            floor = hit.point;
            return true;
        }
        floor = default;
        return false;
    }

    private static bool GroundHit(MeshCollider ground, Vector3 point, out RaycastHit hit, bool flat)
    {
        var top = ground.bounds.max.y + 5;
        var ray = new Ray(new Vector3(point.x, top, point.z), Vector3.down);
        return ground.Raycast(ray, out hit, top - ground.bounds.min.y + 10) && hit.normal.y > (flat ? 0.98f : 0.6f);
    }

    private static bool ClearPath(MeshCollider ground, Vector3 from, Vector3 to, Transform self)
    {
        var steps = Mathf.CeilToInt(Vector3.Distance(from, to));
        var previous = from;
        for (var i = 1; i <= steps; i++)
        {
            if (!Surface(ground, Vector3.Lerp(from, to, (float)i / steps), out var point, false)
                || Mathf.Abs(point.y - previous.y) > 1.5f) return false;
            var delta = point - previous;
            if (delta.sqrMagnitude > 0.001f)
            {
                foreach (var hit in Physics.SphereCastAll(previous + Vector3.up * 1.2f, Clearance, delta.normalized,
                             delta.magnitude, ~0, QueryTriggerInteraction.Ignore))
                {
                    if (hit.collider != null && !IsTraversalExempt(hit.collider.transform)
                        && (self == null || !hit.collider.transform.IsChildOf(self))) return false;
                }
            }
            previous = point;
        }
        return true;
    }

    private static bool IsTraversalExempt(Transform hit)
    {
        if (MyPlayer.Instance != null && hit.IsChildOf(MyPlayer.Instance.transform)) return true;
        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        return controller != null && (controller.spawnPortal != null && hit.IsChildOf(controller.spawnPortal.transform)
            || controller.spawnPlatform != null && hit.IsChildOf(controller.spawnPlatform.transform));
    }

    private static bool Supported(MeshCollider ground, Bounds bounds, float height)
    {
        foreach (var x in new[] { bounds.min.x - Clearance, bounds.max.x + Clearance })
        foreach (var z in new[] { bounds.min.z - Clearance, bounds.max.z + Clearance })
        {
            if (!Surface(ground, new Vector3(x, height, z), out var floor) || Mathf.Abs(floor.y - height) > 0.1f) return false;
        }
        return true;
    }

    private static bool Unoccupied(Bounds bounds, float floorY, Transform self)
    {
        var bottom = Mathf.Max(bounds.min.y, floorY) + 0.15f;
        var top = Mathf.Max(bounds.max.y, bottom + 2);
        var center = new Vector3(bounds.center.x, (bottom + top) * 0.5f, bounds.center.z);
        var half = new Vector3(bounds.extents.x + Clearance, (top - bottom) * 0.5f, bounds.extents.z + Clearance);
        foreach (var collider in Physics.OverlapBox(center, half, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore))
        {
            if (collider != null && !collider.transform.IsChildOf(self)) return false;
        }
        return true;
    }

    private static bool TryBounds(GameObject go, out Bounds bounds)
    {
        bounds = default;
        var found = false;
        foreach (var renderer in LiveEditPatch.ModelRenderers(go))
        {
            if (!renderer.enabled || !renderer.gameObject.activeInHierarchy) continue;
            if (!found) bounds = renderer.bounds;
            else bounds.Encapsulate(renderer.bounds);
            found = true;
        }
        foreach (var collider in go.GetComponentsInChildren<Collider>())
        {
            if (!collider.enabled || collider.isTrigger || !collider.gameObject.activeInHierarchy) continue;
            if (!found) bounds = collider.bounds;
            else bounds.Encapsulate(collider.bounds);
            found = true;
        }
        return found;
    }

    private static bool OverlapsObjects(Bounds bounds, GameObject self, IReadOnlyDictionary<string, GameObject> index)
    {
        bounds.Expand(Clearance * 2);
        foreach (var (id, other) in index)
        {
            if (!ObjectTools.IsPickableGenId(id) || other == null || other == self || !other.activeInHierarchy) continue;
            if (TryBounds(other, out var occupied) && bounds.Intersects(occupied)) return true;
        }
        foreach (var (target, other) in LiveEditPatch.PickableObjects())
        {
            if (target.Kind != ObjectTargetKind.PlacementId || other == null || other == self) continue;
            if (TryBounds(other, out var occupied) && bounds.Intersects(occupied)) return true;
        }
        return false;
    }
}
