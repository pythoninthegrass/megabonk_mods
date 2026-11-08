namespace MegabonkLevels.Tests;

public class RuntimeMusicSessionTests
{
    private sealed class Resource(string name)
    {
        public string Name { get; } = name;
        public int Releases { get; set; }
    }

    private static PcmAudio Tone()
    {
        var read = false;
        return PcmAudio.Read(1, 8000, (buffer, count) =>
        {
            if (read) return 0;
            read = true;
            buffer[0] = 0.1f;
            return 1;
        });
    }

    [Fact]
    public void Selection_UsesCanonicalNameAndNumericSuccessors_ThenWraps()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/14 Strobe.mp3", "/music/6 Base.mp3", "/music/06.10 Ten.mp3", "/music/06.02 Two.mp3" });
        var decoded = new System.Collections.Concurrent.ConcurrentQueue<string>();
        var resources = new List<Resource>();
        var owner = new RuntimeMusicOwner<Resource>((path, token) =>
        {
            decoded.Enqueue(path);
            return Tone();
        }, (path, audio) =>
        {
            var resource = new Resource(Path.GetFileNameWithoutExtension(path));
            resources.Add(resource);
            return resource;
        }, resource => resource.Releases++);
        using (var session = new RuntimeMusicSession<Resource>(library, owner))
        {
            session.Select("06.02 two", _ => { });
            Assert.Equal("06.02 Two", session.Current!.Name);
            Assert.True(SpinWait.SpinUntil(() => decoded.Count == 2, 5000));
            Assert.Equal("/music/06.10 Ten.mp3", decoded.Last());
            session.PlayNext(_ => { });
            Assert.Equal("06.10 Ten", session.Current.Name);
            session.PlayNext(_ => { });
            Assert.Equal("14 Strobe", session.Current.Name);
            session.PlayNext(_ => { });
            Assert.Equal("6 Base", session.Current.Name);
        }
        Assert.All(resources, resource => Assert.Equal(1, resource.Releases));
    }

    private static RuntimeMusicSession<Resource> ThreeTrackSession()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/1 One.mp3", "/music/2 Two.mp3", "/music/3 Three.mp3" });
        return new RuntimeMusicSession<Resource>(library,
            new RuntimeMusicOwner<Resource>((path, token) => Tone(),
                (path, audio) => new Resource(Path.GetFileNameWithoutExtension(path)), _ => { }));
    }

    [Fact]
    public void Transport_ExposesOrderedNamesAndTheCurrentNumber()
    {
        using var session = ThreeTrackSession();

        session.Select("2 Two", _ => { });

        Assert.Equal(new[] { "1 One", "2 Two", "3 Three" }, session.Names);
        Assert.Equal(2, session.CurrentNumber);
    }

    [Fact]
    public void PlayPrevious_StepsBackAndWraps()
    {
        using var session = ThreeTrackSession();
        session.Select("1 One", _ => { });

        session.PlayPrevious(_ => { });
        Assert.Equal("3 Three", session.Current.Name);
        session.PlayPrevious(_ => { });
        Assert.Equal("2 Two", session.Current.Name);
    }

    [Fact]
    public void PlayTrack_JumpsToTheNumberAndNextContinuesFromIt()
    {
        using var session = ThreeTrackSession();
        session.Select("1 One", _ => { });

        session.PlayTrack(3, _ => { });
        Assert.Equal("3 Three", session.Current.Name);
        Assert.Equal(3, session.CurrentNumber);
        session.PlayNext(_ => { });
        Assert.Equal("1 One", session.Current.Name);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(4)]
    public void PlayTrack_RejectsAnOutOfRangeNumberWithoutChangingTheTrack(int number)
    {
        using var session = ThreeTrackSession();
        session.Select("2 Two", _ => { });

        Assert.Throws<ArgumentOutOfRangeException>(() => session.PlayTrack(number, _ => { }));
        Assert.Equal("2 Two", session.Current.Name);
        Assert.Equal(2, session.CurrentNumber);
    }

    [Fact]
    public void FailedSuccessor_IsSurfacedAndCanBeCleanedUpWithoutLeaking()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/1 Good.mp3", "/music/2 Bad.mp3" });
        var resource = new Resource("good");
        var owner = new RuntimeMusicOwner<Resource>((path, token) => path.Contains("Bad") ? throw new InvalidDataException("bad mp3") : Tone(),
            (path, audio) => resource, current => current.Releases++);
        var session = new RuntimeMusicSession<Resource>(library, owner);
        session.Select("1 Good", _ => { });
        Assert.Throws<InvalidDataException>(() => session.PlayNext(_ => { }));
        Assert.Same(resource, session.Current);
        session.Dispose();
        session.Dispose();
        Assert.Equal(1, resource.Releases);
    }

    [Fact]
    public void UnknownTrack_NeverDecodesAnArbitraryPath()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/1 Good.mp3" });
        var calls = 0;
        var owner = new RuntimeMusicOwner<Resource>((path, token) => { calls++; return Tone(); },
            (path, audio) => new Resource(path), _ => { });
        using var session = new RuntimeMusicSession<Resource>(library, owner);
        Assert.Throws<FileNotFoundException>(() => session.Select("../outside", _ => { }));
        Assert.Equal(0, calls);
    }

    [Fact]
    public void SingleTrack_ProgressionReplaysAndDoesNotPrefetchItself()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/14 Strobe.mp3" });
        var calls = 0;
        using var session = new RuntimeMusicSession<Resource>(library,
            new RuntimeMusicOwner<Resource>((path, token) => { calls++; return Tone(); },
                (path, audio) => new Resource(path), _ => { }));
        session.Select("14 strobe", _ => { });
        Assert.Equal(1, calls);
        session.PlayNext(_ => { });
        Assert.Equal(2, calls);
    }

    [Fact]
    public void LeavingSession_CancelsAndJoinsSuccessorBeforeReleasingCurrent()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/1 Current.mp3", "/music/2 Next.mp3" });
        using var started = new ManualResetEventSlim();
        var cancelled = false;
        var releasedAfterCancel = false;
        var owner = new RuntimeMusicOwner<Resource>((path, token) =>
        {
            if (!path.Contains("Next")) return Tone();
            started.Set();
            token.WaitHandle.WaitOne();
            cancelled = true;
            token.ThrowIfCancellationRequested();
            return Tone();
        }, (path, audio) => new Resource(path), _ => releasedAfterCancel = cancelled);
        using var session = new RuntimeMusicSession<Resource>(library, owner);
        session.Select("1 Current", _ => { });
        Assert.True(started.Wait(5000));
        session.Dispose();
        Assert.True(cancelled);
        Assert.True(releasedAfterCancel);
        Assert.Null(session.Current);
    }

    [Fact]
    public void ReselectAfterExternalUnload_RecreatesCurrentAndPreservesSuccessor()
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/1 Current.mp3", "/music/2 Next.mp3" });
        using var session = new RuntimeMusicSession<Resource>(library,
            new RuntimeMusicOwner<Resource>((path, token) => Tone(),
                (path, audio) => new Resource(Path.GetFileNameWithoutExtension(path)), resource => resource.Releases++));
        session.Select("1 Current", _ => { });
        var unloaded = session.Current;
        session.Select("1 Current", _ => { });
        Assert.NotSame(unloaded, session.Current);
        Assert.Equal(1, unloaded.Releases);
        Assert.Equal("1 Current", session.Current.Name);
        session.PlayNext(_ => { });
        Assert.Equal("2 Next", session.Current.Name);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void FailedInitialDecode_CanBeDisposedAndReplaced(bool denied)
    {
        var library = CustomMusicLibrary.FromFiles(new[] { "/music/1 Track.mp3" });
        var creates = 0;
        using (var failed = new RuntimeMusicSession<Resource>(library,
            new RuntimeMusicOwner<Resource>((path, token) => throw (denied
                    ? new UnauthorizedAccessException("denied")
                    : new FileNotFoundException("removed after discovery")),
                (path, audio) => { creates++; return new Resource(path); }, _ => { })))
        {
            Assert.ThrowsAny<Exception>(() => failed.Select("1 Track", _ => { }));
            Assert.Null(failed.Current);
            Assert.Equal(0, creates);
        }

        using var replacement = new RuntimeMusicSession<Resource>(library,
            new RuntimeMusicOwner<Resource>((path, token) => Tone(),
                (path, audio) => new Resource(path), _ => { }));
        replacement.Select("1 Track", _ => { });
        Assert.NotNull(replacement.Current);
    }
}
