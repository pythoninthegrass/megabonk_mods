using System.Collections.Generic;

namespace MegabonkLevels;

public readonly record struct TileState(int Height, SlopeDirection Slope);

// Removed is distinct from the record being absent from LevelState.Objects: absent means "no edit has
// ever touched this target, defer entirely to the generator"; Removed=true is an explicit override that
// must survive undo/redo and serialization as its own state, not just a missing entry.
public readonly record struct ObjectState(bool Removed, string CatalogId, TransformData? Transform,
    ObjectTarget? Owner = null, TransformData? LocalTransform = null, bool Hidden = false);

// Pure tile and object state built by replaying EditOps, independent of Unity and the loader.
public sealed class LevelState
{
    private readonly Dictionary<(int X, int Z), TileState> _tiles = new();
    private readonly Dictionary<ObjectTarget, ObjectState> _objects = new();
    private int _nextPlacementId;

    public IReadOnlyDictionary<(int X, int Z), TileState> Tiles => _tiles;
    public IReadOnlyDictionary<ObjectTarget, ObjectState> Objects => _objects;

    public static LevelState FromTiles(IEnumerable<KeyValuePair<(int X, int Z), TileState>> tiles)
    {
        var state = new LevelState();
        foreach (var (cell, tile) in tiles)
        {
            state._tiles[cell] = tile;
        }

        return state;
    }

    public TileState? GetTile(int x, int z) => _tiles.TryGetValue((x, z), out var tile) ? tile : null;

    public ObjectState? GetObject(ObjectTarget target) => _objects.TryGetValue(target, out var obj) ? obj : null;

    public bool IsObjectActive(ObjectTarget target) => _objects.TryGetValue(target, out var obj)
        && !obj.Removed && (obj.Owner is not { } owner || IsObjectActive(owner));

    public ObjectTarget SelectionTarget(ObjectTarget target, bool selectHidden) =>
        !selectHidden && GetObject(target) is { Hidden: true, Owner: { } owner } ? owner : target;

    internal void RefreshAttachments(ObjectTarget owner)
    {
        if (GetObject(owner)?.Transform is not { } transform)
        {
            return;
        }
        foreach (var target in new List<ObjectTarget>(_objects.Keys))
        {
            var child = _objects[target];
            if (child.Owner == owner && child.LocalTransform is { } local)
            {
                _objects[target] = child with { Transform = AttachmentTransform.ToWorld(transform, local) };
            }
        }
    }

    internal void SetTile(int x, int z, TileState state) => _tiles[(x, z)] = state;

    internal void RemoveTile(int x, int z) => _tiles.Remove((x, z));

    internal void SetObject(ObjectTarget target, ObjectState state) => _objects[target] = state;

    internal void RemoveObject(ObjectTarget target) => _objects.Remove(target);

    // Monotonic: once allocated, a placement id is never reused, even if the PlaceObject that
    // allocated it is later undone — this avoids a later edit resolving to a stale, unrelated object.
    internal ObjectTarget AllocatePlacementId(int? requested = null, int count = 1)
    {
        var id = requested ?? _nextPlacementId;
        if (id < _nextPlacementId || count < 1 || (long)id + count >= int.MaxValue)
        {
            throw new System.ArgumentException("Placement IDs must be unused and monotonic.", nameof(requested));
        }
        _nextPlacementId = id + count;
        return ObjectTarget.FromPlacementId(id);
    }
}
