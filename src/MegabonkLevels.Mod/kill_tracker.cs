using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Decides which fallen actors the kill floor should kill on each check. A killed actor can stay in the game's
// lists for a while, so it is skipped until `retryAfterSeconds` pass, then retried with a higher attempt number so
// an actor that ignores the kill stays visible in the log.
public sealed class KillTracker
{
    private readonly float _retryAfterSeconds;
    private readonly Dictionary<uint, (float LastAttemptAt, int Attempts)> _attempts = new();

    public KillTracker(float retryAfterSeconds)
    {
        _retryAfterSeconds = retryAfterSeconds;
    }

    public IReadOnlyList<(uint Id, int Attempt)> Select(IEnumerable<(uint Id, float Y)> candidates, float floorY, float now)
    {
        var present = candidates.GroupBy(c => c.Id).ToDictionary(g => g.Key, g => g.First().Y);
        foreach (var id in _attempts.Keys.Where(id => !present.ContainsKey(id) || !KillFloor.ShouldKill(present[id], floorY)).ToList())
        {
            _attempts.Remove(id);
        }

        var picks = new List<(uint, int)>();
        foreach (var (id, y) in present)
        {
            if (!KillFloor.ShouldKill(y, floorY))
            {
                continue;
            }

            var attempts = 0;
            if (_attempts.TryGetValue(id, out var previous))
            {
                if (now - previous.LastAttemptAt < _retryAfterSeconds)
                {
                    continue;
                }

                attempts = previous.Attempts;
            }

            _attempts[id] = (now, attempts + 1);
            picks.Add((id, attempts + 1));
        }

        return picks;
    }
}
