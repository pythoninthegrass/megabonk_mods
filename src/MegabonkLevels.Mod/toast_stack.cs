using System;
using System.Collections.Generic;

namespace MegabonkLevels;

public readonly record struct Toast(string Text, bool IsError, float Expiry);

// Unity-free toast list, newest first, so index 0 is the toast nearest the toolbar.
public sealed class ToastStack
{
    private readonly List<Toast> _items = new();
    private readonly float _lifetime;
    private readonly int _maxToasts;

    public ToastStack(float lifetime, int maxToasts)
    {
        _lifetime = lifetime;
        _maxToasts = maxToasts;
    }

    public IReadOnlyList<Toast> Items => _items;

    public void Push(string text, bool isError, float now)
    {
        _items.Insert(0, new Toast(text, isError, now + _lifetime));
        if (_items.Count > _maxToasts)
        {
            _items.RemoveAt(_items.Count - 1);
        }
    }

    public bool Expire(float now) => _items.RemoveAll(t => now >= t.Expiry) > 0;

    public void Dismiss(int index)
    {
        if (index >= 0 && index < _items.Count)
        {
            _items.RemoveAt(index);
        }
    }

    public void Clear() => _items.Clear();
}
