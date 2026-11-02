using System.Collections.Generic;

namespace MegabonkLevels;

// Decides which fallen actors the kill floor should kill on each check. A killed actor can stay in the game's
// lists for a while, so it is skipped until `retryAfterSeconds` pass, then retried with a higher attempt number so
// an actor that ignores the kill stays visible in the log.
public sealed class KillTracker
{
    private readonly float _retryAfterSeconds;
    private readonly Dictionary<uint, (float LastAttemptAt, int Attempts)> _attempts = new();
    private readonly HashSet<uint> _seen = new();
    private readonly List<uint> _stale = new();

    public KillTracker(float retryAfterSeconds)
    {
        _retryAfterSeconds = retryAfterSeconds;
    }

    // `lowestById` maps each actor the watcher can see to its lowest point, so a duplicate id cannot arrive here twice.
    public IReadOnlyList<(uint Id, int Attempt)> Select(IReadOnlyDictionary<uint, float> lowestById, float floorY, float now)
    {
        _seen.Clear();
        var picks = new List<(uint, int)>();
        foreach (var (id, y) in lowestById)
        {
            if (!KillFloor.ShouldKill(y, floorY))
            {
                continue;
            }

            _seen.Add(id);
            if (!_attempts.TryGetValue(id, out var previous))
            {
                _attempts[id] = (now, 1);
                picks.Add((id, 1));
                continue;
            }

            if (now - previous.LastAttemptAt >= _retryAfterSeconds)
            {
                var attempt = previous.Attempts + 1;
                _attempts[id] = (now, attempt);
                picks.Add((id, attempt));
            }
        }

        _stale.Clear();
        foreach (var id in _attempts.Keys)
        {
            if (!_seen.Contains(id))
            {
                _stale.Add(id);
            }
        }

        foreach (var id in _stale)
        {
            _attempts.Remove(id);
        }

        return picks;
    }
}
