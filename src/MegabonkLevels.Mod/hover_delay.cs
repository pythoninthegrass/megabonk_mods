namespace MegabonkLevels;

// When any tooltip was last visible, shared so that moving between tooltips keeps them active.
public sealed class HoverActivity
{
    public float LastReadyAt { get; set; } = float.NegativeInfinity;
}

// Unity-free dwell timer: ready once a target has been hovered for the delay, or at once when a tooltip was visible within the grace period.
public sealed class HoverDelay
{
    private readonly float _delaySeconds;
    private readonly float _graceSeconds;
    private readonly HoverActivity _activity;
    private int? _target;
    private float _since;

    public HoverDelay(float delaySeconds, float graceSeconds, HoverActivity activity)
    {
        _delaySeconds = delaySeconds;
        _graceSeconds = graceSeconds;
        _activity = activity;
    }

    public bool Update(int? target, float now)
    {
        if (target != _target)
        {
            _target = target;
            _since = now;
        }

        if (!_target.HasValue)
        {
            return false;
        }

        var ready = now - _since >= _delaySeconds || now - _activity.LastReadyAt <= _graceSeconds;
        if (ready)
        {
            _activity.LastReadyAt = now;
        }

        return ready;
    }
}
