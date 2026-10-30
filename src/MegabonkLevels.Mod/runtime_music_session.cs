using System;
using System.IO;
using System.Linq;

namespace MegabonkLevels;

// Shares ordered selection and prefetch policy between stage startup and radio progression.
public sealed class RuntimeMusicSession<T> : IDisposable where T : class
{
    private readonly CustomMusicLibrary _library;
    private readonly RuntimeMusicOwner<T> _owner;
    private readonly RadioPlaylist _playlist;

    public T Current => _owner.Current;

    public RuntimeMusicSession(CustomMusicLibrary library, RuntimeMusicOwner<T> owner)
    {
        _library = library;
        _owner = owner;
        _playlist = RadioPlaylist.PreserveOrder(library.Names);
    }

    public void Select(string name, Action<T> play)
    {
        var path = _library.Resolve(name);
        if (path == null)
        {
            throw new FileNotFoundException($"No discovered custom track '{name}'.");
        }

        _owner.Switch(path, play);
        var canonical = _library.Names.First(entry => string.Equals(entry, name, StringComparison.OrdinalIgnoreCase));
        _playlist.StartAfter(canonical);
        _owner.Prefetch(_library.Resolve(_playlist.Peek()));
    }

    public void PlayNext(Action<T> play) => Select(_playlist.Next(), play);

    public void Dispose() => _owner.Dispose();
}
