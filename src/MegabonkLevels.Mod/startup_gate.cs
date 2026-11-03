using System.Collections.Generic;
using System.Globalization;

namespace MegabonkLevels;

public enum StartupGatePhase
{
    Idle,
    Covering,
    Placing,
    Open,
}

public enum StartupGateCommandKind
{
    ShowCover,
    HideCover,
    HoldPlayer,
    ReleaseHold,
    PlacePlayer,
    Log,
}

public readonly record struct StartupGateCommand(StartupGateCommandKind Kind, string Detail);

// Coordinates startup cover, hold and placement from content/portal readiness and spawn events, never player position.
public sealed class StartupGate
{
    public const float DefaultTimeoutSeconds = 8f;

    public static float ParseTimeoutSeconds(string value) =>
        float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var seconds) && float.IsFinite(seconds) && seconds > 0f
            ? seconds : DefaultTimeoutSeconds;

    private readonly float _timeoutSeconds;
    private readonly float _spawnBurstSeconds;
    private readonly float _placeRetrySeconds;
    private readonly int _maxPlaceAttempts;

    private readonly List<StartupGateCommand> _commands = new List<StartupGateCommand>();

    private bool _custom;
    private bool _coverVisible;
    private bool _holding;
    private bool _holdIssued;
    private bool _pendingPlacement;
    private bool _waitingForPortal;
    private bool _ignoringPortal;
    private bool _placed;
    private float _deadline;
    private float? _portalDeadline;
    private float _nextAttemptAt;
    private float _now;
    private int _attempts;
    private float? _lastSpawnAt;

    public StartupGate(float timeoutSeconds = DefaultTimeoutSeconds, float spawnBurstSeconds = 0.25f, float placeRetrySeconds = 0.1f, int maxPlaceAttempts = 100)
    {
        _timeoutSeconds = timeoutSeconds;
        _spawnBurstSeconds = spawnBurstSeconds;
        _placeRetrySeconds = placeRetrySeconds;
        _maxPlaceAttempts = maxPlaceAttempts;
    }

    public StartupGatePhase Phase { get; private set; } = StartupGatePhase.Idle;

    // The body stays where the game put it until the placement lands, so it cannot fall through a map still being rebuilt.
    public bool ShouldHoldPlayer => _holding;

    // True while a placement is owed and an attempt is allowed; the adapter teleports, then reports PlacementCompleted.
    public bool ShouldAttemptPlace => Phase != StartupGatePhase.Idle && !_waitingForPortal && _pendingPlacement && _attempts < _maxPlaceAttempts && _nextAttemptAt <= _now;

    // Whether the authored start has been applied at least once during this run.
    public bool Placed => _placed;

    public IReadOnlyList<StartupGateCommand> Drain()
    {
        if (_commands.Count == 0)
        {
            return System.Array.Empty<StartupGateCommand>();
        }

        var drained = new List<StartupGateCommand>(_commands);
        _commands.Clear();
        return drained;
    }

    // Every run starts here, modded or not: only a custom run gets a cover, and a vanilla start clears any leftover state.
    public void RunStarted(bool customLevel, float now, bool waitForPortal = false)
    {
        _now = now;
        Release(null);
        Reset();
        if (!customLevel)
        {
            return;
        }

        _custom = true;
        _waitingForPortal = waitForPortal;
        Phase = StartupGatePhase.Covering;
        _coverVisible = true;
        _deadline = now + _timeoutSeconds;
        _commands.Add(new StartupGateCommand(StartupGateCommandKind.ShowCover, "custom run started"));
    }

    // The game placed the player itself: from the menu flow this lands once, inside generation, and a later one (a stage
    // teleport, a restart) is the only thing that asks for another placement after the run is already open.
    public void GameSpawnedPlayer(float now)
    {
        _now = now;
        if (Phase == StartupGatePhase.Idle)
        {
            return;
        }

        if (_lastSpawnAt is float last && now - last < _spawnBurstSeconds)
        {
            return;
        }

        _lastSpawnAt = now;
        _ignoringPortal = false;

        // Once the content is in the world the spawn is simply corrected once; before that the player is held where the
        // game put it, so it cannot fall through a map that is still being torn down and rebuilt.
        if (Phase == StartupGatePhase.Placing || Phase == StartupGatePhase.Open)
        {
            RequestPlacement("the game moved the player");
            return;
        }

        if (!_holdIssued)
        {
            _holdIssued = true;
            _holding = true;
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.HoldPlayer, "held where the game put the player"));
        }
    }

    // Generation finished and the level's edits are in the world: the one placement becomes owed.
    public void ContentReady(float now)
    {
        _now = now;
        if (!_custom || Phase == StartupGatePhase.Idle)
        {
            return;
        }

        if (Phase == StartupGatePhase.Covering)
        {
            Phase = StartupGatePhase.Placing;
        }

        Progress(now);
        if (!_ignoringPortal)
        {
            RequestPlacement("level content ready");
        }
    }

    // Only real generation/edit progress renews the deadline; ticking or retrying placement does not.
    public void Progress(float now)
    {
        if (Phase == StartupGatePhase.Covering || Phase == StartupGatePhase.Placing)
        {
            _deadline = now + _timeoutSeconds;
        }
    }

    // The portal's cached baseline-position animation must finish before the authored placement can stick. A portal that
    // runs after the start was already applied is the last writer, so it re-owes exactly one placement.
    public void PortalClosed(float now)
    {
        if (Phase == StartupGatePhase.Idle || !_waitingForPortal)
        {
            return;
        }

        _now = now;
        _waitingForPortal = false;
        _portalDeadline = null;
        Progress(now);
        if (_ignoringPortal)
        {
            Release("harness teleport kept");
            Phase = StartupGatePhase.Open;
            return;
        }

        if (_placed && !_pendingPlacement)
        {
            RequestPlacement("the spawn portal moved the player");
        }
    }

    // A spawn portal owns the player's position while it animates. Only a portal that runs after the authored start
    // landed takes it back: before that the game's own spawn still decides when the player is held.
    public void PortalOpened(float now)
    {
        _now = now;
        if (!_custom || Phase == StartupGatePhase.Idle || _ignoringPortal)
        {
            return;
        }

        _waitingForPortal = true;
        _deadline = now + _timeoutSeconds;
        _portalDeadline = now + _timeoutSeconds;
        if (Phase == StartupGatePhase.Open)
        {
            Phase = StartupGatePhase.Placing;
        }

        if (!_placed)
        {
            return;
        }

        if (!_coverVisible)
        {
            _coverVisible = true;
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.ShowCover, "a spawn portal owns the player"));
        }

        if (!_holding)
        {
            _holding = true;
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.HoldPlayer, "held while the spawn portal runs"));
        }
    }

    // A harness teleport is deliberate. Nothing the cover owes may move the player afterwards; if a portal still has an
    // animation to run, the player stays pinned on the harness point until it finishes.
    public void HarnessTeleported(float now)
    {
        _now = now;
        if (!_custom || Phase == StartupGatePhase.Idle)
        {
            return;
        }

        _pendingPlacement = false;
        _attempts = 0;
        _ignoringPortal = true;
        _portalDeadline = null;
        if (_waitingForPortal)
        {
            return;
        }

        Release("harness teleport kept");
        Phase = StartupGatePhase.Open;
    }

    // The adapter reports this only after the authored-start teleport actually landed on a live player.
    public void PlacementCompleted(float now)
    {
        _now = now;
        if (Phase == StartupGatePhase.Idle)
        {
            return;
        }

        _pendingPlacement = false;
        _placed = true;
        if (Phase == StartupGatePhase.Placing)
        {
            Phase = StartupGatePhase.Open;
        }

        Release(null);
    }

    // A start that was cancelled, or one that threw on the way in: the cover has to go and nothing later may place the player.
    public void Cancelled(string reason) => Abort(reason);

    public void Failed(string reason) => Abort(reason);

    // Advances the cover deadline and nothing else: no timing here ever moves the player.
    public void Tick(float now)
    {
        _now = now;
        if (Phase != StartupGatePhase.Covering && Phase != StartupGatePhase.Placing)
        {
            return;
        }

        if (now <= _deadline)
        {
            return;
        }

        Release("startup cover released after the timeout");
        Phase = StartupGatePhase.Open;

        // A portal that opened and never reported back must not strand the run: an unopened portal keeps the wait
        // (the load may simply be slow), an opened one does not.
        if (_portalDeadline is float portalDeadline && now > portalDeadline)
        {
            _waitingForPortal = false;
            _portalDeadline = null;
        }
    }

    // Called by the adapter when an attempt was allowed and no player existed to be placed.
    public void PlaceAttemptFailed(string reason, float now)
    {
        _now = now;
        if (!_pendingPlacement)
        {
            return;
        }

        _attempts++;
        _nextAttemptAt = now + _placeRetrySeconds;
        if (_attempts == _maxPlaceAttempts)
        {
            _pendingPlacement = false;
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.Log, $"no player to place: {reason}"));
        }
    }

    private void Abort(string reason)
    {
        if (Phase == StartupGatePhase.Idle)
        {
            return;
        }

        Release(reason);
        Phase = StartupGatePhase.Idle;
    }

    private void RequestPlacement(string reason)
    {
        if (_pendingPlacement)
        {
            return;
        }

        _pendingPlacement = true;
        _attempts = 0;
        _nextAttemptAt = 0f;
        _commands.Add(new StartupGateCommand(StartupGateCommandKind.PlacePlayer, reason));
    }

    private void Release(string reason)
    {
        if (_holding)
        {
            _holding = false;
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.ReleaseHold, reason ?? "startup finished"));
        }

        if (_coverVisible)
        {
            _coverVisible = false;
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.HideCover, reason ?? "startup finished"));
        }

        if (reason != null)
        {
            _commands.Add(new StartupGateCommand(StartupGateCommandKind.Log, reason));
        }
    }

    private void Reset()
    {
        _custom = false;
        _coverVisible = false;
        _holding = false;
        _holdIssued = false;
        _pendingPlacement = false;
        _waitingForPortal = false;
        _ignoringPortal = false;
        _portalDeadline = null;
        _placed = false;
        _attempts = 0;
        _nextAttemptAt = 0f;
        _lastSpawnAt = null;
        Phase = StartupGatePhase.Idle;
    }
}
