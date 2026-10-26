namespace MegabonkLevels;

// Turns a held key into repeated presses: one at once, then a delay, then one per interval.
public sealed class KeyRepeater
{
    private readonly float _delay;
    private readonly float _interval;
    private float _timer;

    public KeyRepeater(float delay = 0.4f, float interval = 0.04f)
    {
        _delay = delay;
        _interval = interval;
    }

    public int Step(bool pressed, bool held, float deltaTime)
    {
        if (!held)
        {
            _timer = 0f;
            return pressed ? 1 : 0;
        }

        if (pressed)
        {
            _timer = _delay;
            return 1;
        }

        _timer -= deltaTime;
        var fired = 0;
        while (_timer <= 0f)
        {
            fired++;
            _timer += _interval;
        }

        return fired;
    }
}
