using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Unity-free scripted keyboard and mouse state; keys are UnityEngine.KeyCode member names.
public sealed class InjectedInputQueue
{
    private const float MouseIdleSeconds = 10f;
    private const float RealMouseTolerance = 2f;

    private readonly List<(int Offset, Action Apply)> _pending = new();
    private readonly HashSet<string> _heldKeys = new();
    private readonly HashSet<string> _pressedKeys = new();
    private readonly HashSet<string> _releasedKeys = new();
    private readonly HashSet<int> _heldButtons = new();
    private readonly HashSet<int> _pressedButtons = new();
    private readonly HashSet<int> _releasedButtons = new();
    private int _cursor;
    private int? _lastFrame;
    private float _now;
    private float _mouseTouchedAt;
    private (float X, float Y) _realMouse;
    private (float X, float Y) _realMouseBaseline;

    public (float, float)? MousePosition { get; private set; }

    public string InputStringThisFrame { get; private set; } = "";

    public float ScrollDeltaThisFrame { get; private set; }

    public void EnqueueTap(string key, IReadOnlyList<string> modifiers)
    {
        var offset = _cursor;
        if (modifiers.Count > 0)
        {
            foreach (var modifier in modifiers)
            {
                Schedule(offset, () => PressKey(modifier));
            }

            offset++;
        }

        Schedule(offset, () => PressKey(key));
        Schedule(offset + 1, () => ReleaseKey(key));
        offset += 2;

        if (modifiers.Count > 0)
        {
            foreach (var modifier in modifiers)
            {
                Schedule(offset, () => ReleaseKey(modifier));
            }

            offset++;
        }

        _cursor = offset;
    }

    public void EnqueueKeyDown(string key) => ScheduleNext(() => PressKey(key));

    public void EnqueueKeyUp(string key) => ScheduleNext(() => ReleaseKey(key));

    // Applies on the same frame as the next step, so a click queued after a move lands on the moved position.
    public void EnqueueMouseMove(float x, float y) => Schedule(_cursor, () =>
    {
        MousePosition = (x, y);
        _mouseTouchedAt = _now;
        _realMouseBaseline = _realMouse;
    });

    public void EnqueueClick(int button)
    {
        Schedule(_cursor, () => PressButton(button));
        Schedule(_cursor + 1, () => ReleaseButton(button));
        _cursor += 2;
    }

    public void EnqueueMouseDown(int button) => ScheduleNext(() => PressButton(button));

    public void EnqueueMouseUp(int button) => ScheduleNext(() => ReleaseButton(button));

    public void EnqueueText(string text)
    {
        foreach (var c in text)
        {
            var typed = c.ToString();
            ScheduleNext(() => InputStringThisFrame = typed);
        }
    }

    // Positive notches scroll up, matching UnityEngine.Input.mouseScrollDelta.y.
    public void EnqueueScroll(float notches) => ScheduleNext(() =>
    {
        ScrollDeltaThisFrame = notches;
        _mouseTouchedAt = _now;
    });

    public void ClearMouse() => MousePosition = null;

    // The injected pointer yields to the real mouse once it moves, and lapses after MouseIdleSeconds without a move or button event unless an injected button is held.
    public void BeginFrame(int frame, float now = 0f, (float X, float Y) realMouse = default)
    {
        if (_lastFrame == frame)
        {
            return;
        }

        _lastFrame = frame;
        _now = now;
        _realMouse = realMouse;
        _pressedKeys.Clear();
        _releasedKeys.Clear();
        _pressedButtons.Clear();
        _releasedButtons.Clear();
        InputStringThisFrame = "";
        ScrollDeltaThisFrame = 0f;

        var due = _pending.FindAll(step => step.Offset == 0);
        _pending.RemoveAll(step => step.Offset == 0);
        for (var i = 0; i < _pending.Count; i++)
        {
            _pending[i] = (_pending[i].Offset - 1, _pending[i].Apply);
        }

        _cursor = Math.Max(_cursor - 1, 0);

        foreach (var step in due)
        {
            step.Apply();
        }

        if (MousePosition != null && (RealMouseMoved() || (_heldButtons.Count == 0 && now - _mouseTouchedAt >= MouseIdleSeconds)))
        {
            MousePosition = null;
        }
    }

    public bool IsKeyHeld(string key) => _heldKeys.Contains(key);

    public bool WasKeyPressedThisFrame(string key) => _pressedKeys.Contains(key);

    public bool WasKeyReleasedThisFrame(string key) => _releasedKeys.Contains(key);

    public bool IsMouseHeld(int button) => _heldButtons.Contains(button);

    public bool WasMousePressedThisFrame(int button) => _pressedButtons.Contains(button);

    public bool WasMouseReleasedThisFrame(int button) => _releasedButtons.Contains(button);

    private bool RealMouseMoved() =>
        Math.Abs(_realMouse.X - _realMouseBaseline.X) > RealMouseTolerance || Math.Abs(_realMouse.Y - _realMouseBaseline.Y) > RealMouseTolerance;

    private void Schedule(int offset, Action apply) => _pending.Add((offset, apply));

    private void ScheduleNext(Action apply)
    {
        Schedule(_cursor, apply);
        _cursor++;
    }

    private void PressKey(string key)
    {
        if (_heldKeys.Add(key))
        {
            _pressedKeys.Add(key);
        }
    }

    private void ReleaseKey(string key)
    {
        if (_heldKeys.Remove(key))
        {
            _releasedKeys.Add(key);
        }
    }

    private void PressButton(int button)
    {
        _mouseTouchedAt = _now;
        if (_heldButtons.Add(button))
        {
            _pressedButtons.Add(button);
        }
    }

    private void ReleaseButton(int button)
    {
        _mouseTouchedAt = _now;
        if (_heldButtons.Remove(button))
        {
            _releasedButtons.Add(button);
        }
    }
}
