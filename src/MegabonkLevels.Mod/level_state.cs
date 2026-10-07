using System.Collections.Generic;

namespace MegabonkLevels;

public readonly record struct TileState(int Height, SlopeDirection Slope);

// Removed is distinct from the record being absent from LevelState.Objects: absent means "no edit has
// ever touched this target, defer entirely to the generator"; Removed=true is an explicit override that
// must survive undo/redo and serialization as its own state, not just a missing entry.
public readonly record struct ObjectState(bool Removed, string CatalogId, TransformData? Transform);

// Pure data: a tile grid plus placed/removed/moved object overrides, built by replaying EditOps
// (TASK-003.02) through an EditStack. Has no Unity or MelonLoader dependency so it can be unit tested
// and reused outside the running game.
public sealed class LevelState
{
    private readonly Dictionary<(int X, int Z), TileState> _tiles = new();
    private readonly Dictionary<ObjectTarget, ObjectState> _objects = new();
    private int _nextPlacementId;

    public IReadOnlyDictionary<(int X, int Z), TileState> Tiles => _tiles;
    public IReadOnlyDictionary<ObjectTarget, ObjectState> Objects => _objects;

    public TileState? GetTile(int x, int z) => _tiles.TryGetValue((x, z), out var tile) ? tile : null;

    public ObjectState? GetObject(ObjectTarget target) => _objects.TryGetValue(target, out var obj) ? obj : null;

    internal void SetTile(int x, int z, TileState state) => _tiles[(x, z)] = state;

    internal void RemoveTile(int x, int z) => _tiles.Remove((x, z));

    internal void SetObject(ObjectTarget target, ObjectState state) => _objects[target] = state;

    internal void RemoveObject(ObjectTarget target) => _objects.Remove(target);

    // Monotonic: once allocated, a placement id is never reused, even if the PlaceObject that
    // allocated it is later undone — this avoids a later edit resolving to a stale, unrelated object.
    internal ObjectTarget AllocatePlacementId() => ObjectTarget.FromPlacementId(_nextPlacementId++);
}
