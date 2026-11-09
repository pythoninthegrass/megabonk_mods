namespace MegabonkLevels;

public readonly record struct ActorPosition(uint Id, float X, float Y, float Z);

// Picks which enemies the dev readout lists: those below the kill floor first, then the rest, each group ordered by
// horizontal distance to the player (ties by lower id), capped at the capacity. The buffers are allocated once and
// reused, so offering hundreds of enemies a tick allocates nothing.
public sealed class NearbyEnemySelector
{
    private readonly ActorPosition[] _actors;
    private readonly float[] _distanceSquared;
    private readonly bool[] _belowFloor;
    private float _playerX;
    private float _playerZ;
    private float _floorY;

    public NearbyEnemySelector(int capacity)
    {
        _actors = new ActorPosition[capacity];
        _distanceSquared = new float[capacity];
        _belowFloor = new bool[capacity];
    }

    public int Count { get; private set; }

    public ActorPosition this[int index] => _actors[index];

    public void Begin(float playerX, float playerZ, float floorY)
    {
        _playerX = playerX;
        _playerZ = playerZ;
        _floorY = floorY;
        Count = 0;
    }

    public void Offer(in ActorPosition actor)
    {
        var dx = actor.X - _playerX;
        var dz = actor.Z - _playerZ;
        var distance = dx * dx + dz * dz;
        var below = KillFloor.ShouldKill(actor.Y, _floorY);

        var slot = Count;
        while (slot > 0 && Ranks(actor.Id, below, distance, slot - 1))
        {
            slot--;
        }

        if (slot >= _actors.Length)
        {
            return;
        }

        var last = Count < _actors.Length ? Count : _actors.Length - 1;
        for (var i = last; i > slot; i--)
        {
            _actors[i] = _actors[i - 1];
            _distanceSquared[i] = _distanceSquared[i - 1];
            _belowFloor[i] = _belowFloor[i - 1];
        }

        _actors[slot] = actor;
        _distanceSquared[slot] = distance;
        _belowFloor[slot] = below;
        if (Count < _actors.Length)
        {
            Count++;
        }
    }

    // True when the offered actor ranks ahead of the one already held at `index`.
    private bool Ranks(uint id, bool below, float distance, int index)
    {
        if (below != _belowFloor[index])
        {
            return below;
        }

        if (distance != _distanceSquared[index])
        {
            return distance < _distanceSquared[index];
        }

        return id < _actors[index].Id;
    }
}
