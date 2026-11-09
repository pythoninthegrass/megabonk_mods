using System;
using System.Threading;
using System.Threading.Tasks;

namespace MegabonkLevels;

// Call from the game thread; only the successor's managed decode runs on a worker.
public sealed class RuntimeMusicOwner<T> : IDisposable where T : class
{
    private readonly Func<string, CancellationToken, PcmAudio> _decode;
    private readonly Func<string, PcmAudio, T> _create;
    private readonly Action<T> _destroy;
    private readonly int _ownerThread = Environment.CurrentManagedThreadId;
    private CancellationTokenSource _cancellation;
    private Task<PcmAudio> _prefetch;
    private string _next;
    private string _currentName;
    private bool _disposed;

    public T Current { get; private set; }

    public RuntimeMusicOwner(Func<string, CancellationToken, PcmAudio> decode, Func<string, PcmAudio, T> create, Action<T> destroy)
    {
        _decode = decode;
        _create = create;
        _destroy = destroy;
    }

    public void Switch(string name, Action<T> play)
    {
        ThrowIfDisposed();
        PcmAudio audio;
        if (name == _next && _prefetch != null)
        {
            try
            {
                audio = _prefetch.GetAwaiter().GetResult();
            }
            finally
            {
                ClearPrefetch();
            }
        }
        else
        {
            CancelPrefetch();
            audio = _decode(name, CancellationToken.None);
        }

        var candidate = _create(name, audio);
        try
        {
            play(candidate);
        }
        catch
        {
            _destroy(candidate);
            throw;
        }

        var previous = Current;
        Current = candidate;
        _currentName = name;
        if (previous != null)
        {
            _destroy(previous);
        }
    }

    public void Prefetch(string name)
    {
        ThrowIfDisposed();
        if (name == _next && _prefetch != null)
        {
            return;
        }

        CancelPrefetch();
        if (name == null || name == _currentName)
        {
            return;
        }

        _next = name;
        _cancellation = new CancellationTokenSource();
        var token = _cancellation.Token;
        _prefetch = Task.Run(() => _decode(name, token), token);
    }

    private void CancelPrefetch()
    {
        if (_prefetch == null)
        {
            return;
        }

        _cancellation.Cancel();
        try
        {
            _prefetch.GetAwaiter().GetResult();
        }
        catch (Exception)
        {
            // A discarded prefetch's error must not prevent cleanup or another request.
        }
        finally
        {
            ClearPrefetch();
        }
    }

    private void ClearPrefetch()
    {
        _prefetch = null;
        _next = null;
        _cancellation?.Dispose();
        _cancellation = null;
    }

    private void ThrowIfDisposed()
    {
        CheckThread();
        if (_disposed)
        {
            throw new ObjectDisposedException(nameof(RuntimeMusicOwner<T>));
        }
    }

    public void Dispose()
    {
        CheckThread();
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        CancelPrefetch();
        var previous = Current;
        Current = null;
        _currentName = null;
        if (previous != null)
        {
            _destroy(previous);
        }
    }

    private void CheckThread()
    {
        if (Environment.CurrentManagedThreadId != _ownerThread)
        {
            throw new InvalidOperationException("Runtime music ownership must stay on its creating thread.");
        }
    }
}
