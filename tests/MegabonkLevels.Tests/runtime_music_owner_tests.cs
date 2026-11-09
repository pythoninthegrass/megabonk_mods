namespace MegabonkLevels.Tests;

public class RuntimeMusicOwnerTests
{
    private static PcmAudio Audio() => PcmAudio.Read(1, 44100, new Reader().Read);

    private sealed class Reader
    {
        private bool _read;
        public int Read(float[] buffer, int count)
        {
            if (_read) return 0;
            _read = true;
            return 2;
        }
    }

    [Fact]
    public void RapidSwitches_KeepAtMostTwoResourcesDuringHandoff()
    {
        var live = new HashSet<string>();
        var peak = 0;
        var owner = new RuntimeMusicOwner<string>((_, _) => Audio(), (name, _) =>
        {
            live.Add(name);
            peak = Math.Max(peak, live.Count);
            return name;
        }, name => Assert.True(live.Remove(name)));

        for (var i = 0; i < 50; i++)
        {
            owner.Switch(i.ToString(), _ => { });
            Assert.Single(live);
        }

        owner.Dispose();
        Assert.Equal(2, peak);
        Assert.Empty(live);
    }

    [Fact]
    public void CanceledPrefetchResult_IsDiscardedEvenIfDecoderReturnsLate()
    {
        using var started = new ManualResetEventSlim();
        var created = new List<string>();
        using var owner = new RuntimeMusicOwner<string>((name, token) =>
        {
            if (name == "B")
            {
                started.Set();
                token.WaitHandle.WaitOne(TimeSpan.FromSeconds(5));
            }

            return Audio();
        }, (name, _) => { created.Add(name); return name; }, _ => { });
        owner.Prefetch("B");
        Assert.True(started.Wait(TimeSpan.FromSeconds(5)));
        owner.Switch("C", _ => { });
        Assert.Equal(new[] { "C" }, created);
    }

    [Fact]
    public void Owner_RejectsResourceOperationsFromAnotherThread()
    {
        using var owner = new RuntimeMusicOwner<string>((_, _) => Audio(), (name, _) => name, _ => { });
        Exception? failure = null;
        var thread = new Thread(() =>
        {
            try
            {
                Assert.Throws<InvalidOperationException>(() => owner.Switch("A", _ => { }));
                Assert.Throws<InvalidOperationException>(() => owner.Prefetch("A"));
                Assert.Throws<InvalidOperationException>(() => owner.Dispose());
            }
            catch (Exception ex)
            {
                failure = ex;
            }
        });
        thread.Start();
        Assert.True(thread.Join(TimeSpan.FromSeconds(5)));
        Assert.Null(failure);
    }

    [Fact]
    public void Switch_PlaysBeforeReleasingOldResourceAndDisposeIsIdempotent()
    {
        var events = new List<string>();
        using var owner = new RuntimeMusicOwner<string>((_, _) => Audio(), (name, _) => name, name => events.Add("destroy " + name));
        owner.Switch("A", name => events.Add("play " + name));
        owner.Switch("B", name => events.Add("play " + name));
        owner.Dispose();
        owner.Dispose();
        Assert.Equal(new[] { "play A", "play B", "destroy A", "destroy B" }, events);
        Assert.Throws<ObjectDisposedException>(() => owner.Switch("C", _ => { }));
    }

    [Fact]
    public void Prefetch_ReusesDecodeAndCreatesUnityResourceOnCallerThreadOnly()
    {
        var caller = Environment.CurrentManagedThreadId;
        var decoded = new List<string>();
        using var ready = new ManualResetEventSlim();
        using var owner = new RuntimeMusicOwner<string>((name, _) =>
        {
            lock (decoded) decoded.Add(name);
            ready.Set();
            return Audio();
        }, (name, _) => { Assert.Equal(caller, Environment.CurrentManagedThreadId); return name; }, _ => Assert.Equal(caller, Environment.CurrentManagedThreadId));

        owner.Prefetch("B");
        Assert.True(ready.Wait(TimeSpan.FromSeconds(5)));
        owner.Switch("B", _ => { });
        Assert.Equal(new[] { "B" }, decoded);
        Assert.Equal("B", owner.Current);
    }

    [Fact]
    public void Prefetch_ReplacementCancelsAndJoinsPreviousWorker()
    {
        using var started = new ManualResetEventSlim();
        var canceled = false;
        using var owner = new RuntimeMusicOwner<string>((name, token) =>
        {
            if (name == "B")
            {
                started.Set();
                token.WaitHandle.WaitOne(TimeSpan.FromSeconds(5));
                canceled = token.IsCancellationRequested;
                token.ThrowIfCancellationRequested();
            }
            return Audio();
        }, (name, _) => name, _ => { });

        owner.Prefetch("B");
        Assert.True(started.Wait(TimeSpan.FromSeconds(5)));
        owner.Prefetch("C");
        Assert.True(canceled);
        owner.Switch("C", _ => { });
        Assert.Equal("C", owner.Current);
    }

    [Fact]
    public void Switch_FailedPlayDestroysCandidateButKeepsCurrent()
    {
        var destroyed = new List<string>();
        using var owner = new RuntimeMusicOwner<string>((_, _) => Audio(), (name, _) => name, destroyed.Add);
        owner.Switch("A", _ => { });
        Assert.Throws<IOException>(() => owner.Switch("B", _ => throw new IOException("play")));
        Assert.Equal("A", owner.Current);
        Assert.Equal(new[] { "B" }, destroyed);
    }

    [Fact]
    public void Switch_DecodeAndCreateFailuresKeepCurrentAndSurfacePrefetchErrors()
    {
        using var owner = new RuntimeMusicOwner<string>((name, _) => name == "bad" ? throw new InvalidDataException("decode") : Audio(),
            (name, _) => name == "fail" ? throw new IOException("create") : name, _ => { });
        owner.Switch("A", _ => { });
        owner.Prefetch("bad");
        Assert.Throws<InvalidDataException>(() => owner.Switch("bad", _ => { }));
        Assert.Throws<IOException>(() => owner.Switch("fail", _ => { }));
        Assert.Equal("A", owner.Current);
    }

    [Fact]
    public void Dispose_CancelsPrefetchAndNeverCreatesItsResource()
    {
        using var started = new ManualResetEventSlim();
        var created = 0;
        var owner = new RuntimeMusicOwner<string>((_, token) =>
        {
            started.Set();
            token.WaitHandle.WaitOne(TimeSpan.FromSeconds(5));
            token.ThrowIfCancellationRequested();
            return Audio();
        }, (name, _) => { created++; return name; }, _ => { });
        owner.Prefetch("A");
        Assert.True(started.Wait(TimeSpan.FromSeconds(5)));
        owner.Dispose();
        Assert.Equal(0, created);
        Assert.Null(owner.Current);
        Assert.Throws<ObjectDisposedException>(() => owner.Prefetch("B"));
    }
}
