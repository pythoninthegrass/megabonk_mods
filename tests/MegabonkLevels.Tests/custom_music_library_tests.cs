namespace MegabonkLevels.Tests;

public class CustomMusicLibraryTests : IDisposable
{
    private readonly string _folder = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());

    public CustomMusicLibraryTests() => Directory.CreateDirectory(_folder);

    [Fact]
    public void Ordering_UsesIntegerComponentsThenOrdinalNames()
    {
        string[] names = ["Untitled", "14 Strobe", "06.10 Ten", "06.02 Two", "06.01 One", "6 Base", "002 B", "02 A", "2 A", "999999999999999999999999 Large", "Zebra", "١ NotAscii"];

        Assert.Equal(new[] { "002 B", "02 A", "2 A", "6 Base", "06.01 One", "06.02 Two", "06.10 Ten", "14 Strobe", "999999999999999999999999 Large", "Untitled", "Zebra", "١ NotAscii" }, names.OrderBy(x => x, TrackFileName.Comparer));
    }

    [Theory]
    [InlineData("06.02 Two", "06.10 Ten")]
    [InlineData("06 Base", "06.0 Sub")]
    [InlineData("6. End", "6.1 Next")]
    [InlineData("0 Zero", "No prefix")]
    [InlineData("99999999999999999999 A", "100000000000000000000 B")]
    public void Ordering_HandlesPrefixEdges(string before, string after)
    {
        Assert.True(TrackFileName.Comparer.Compare(before, after) < 0);
        Assert.True(TrackFileName.Comparer.Compare(after, before) > 0);
        Assert.Equal(0, TrackFileName.Comparer.Compare(before, before));
    }

    [Fact]
    public void Discover_FiltersTopLevelMp3sAndResolvesCaseInsensitively()
    {
        Write("14 Strobe.MP3");
        var expected = Write("06.01 Screamer.mp3");
        Write("notes.txt");
        Directory.CreateDirectory(Path.Combine(_folder, "nested"));
        File.WriteAllText(Path.Combine(_folder, "nested", "01 Hidden.mp3"), "");

        var library = CustomMusicLibrary.Discover(_folder);

        Assert.Equal(new[] { "06.01 Screamer", "14 Strobe" }, library.Names);
        Assert.Equal(expected, library.Resolve("06.01 SCREAMER"));
        Assert.Null(library.Resolve("06.01 Screamer.mp3"));
        Assert.Null(library.Resolve("missing"));
        Assert.Null(library.Resolve("../06.01 Screamer"));
        Assert.Null(library.Resolve("..\\06.01 Screamer"));
        Assert.Null(library.Resolve(null));
    }

    [Fact]
    public void Discover_MissingFolderIsEmpty()
    {
        var warnings = new List<string>();
        Assert.Empty(CustomMusicLibrary.Discover(Path.Combine(_folder, "missing"), warnings.Add).Names);
        Assert.Empty(warnings);
    }

    [Fact]
    public void Discover_IoFailureWarnsAndReturnsEmpty()
    {
        var warnings = new List<string>();
        var file = Write("not-a-directory");
        Assert.Empty(CustomMusicLibrary.Discover(file, warnings.Add).Names);
        Assert.Single(warnings);
    }

    [Fact]
    public void Discover_UnreadableFolderWarnsWithoutThrowing()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var permissions = File.GetUnixFileMode(_folder);
        try
        {
            File.SetUnixFileMode(_folder, UnixFileMode.None);
            var warnings = new List<string>();
            Assert.Empty(CustomMusicLibrary.Discover(_folder, warnings.Add).Names);
            Assert.Single(warnings);
        }
        finally
        {
            File.SetUnixFileMode(_folder, permissions);
        }
    }

    [Fact]
    public void Discover_CaseCollisionsAreExcludedRegardlessOfEnumerationOrder()
    {
        string[] files = [Path.Combine(_folder, "01 Song.mp3"), Path.Combine(_folder, "01 SONG.MP3"), Path.Combine(_folder, "02 Next.mp3")];
        var warnings = new List<string>();
        var library = CustomMusicLibrary.FromFiles(files, warnings.Add);
        var reversedWarnings = new List<string>();
        var reversed = CustomMusicLibrary.FromFiles(files.Reverse(), reversedWarnings.Add);
        Assert.Equal(new[] { "02 Next" }, library.Names);
        Assert.Equal(library.Names, reversed.Names);
        Assert.Null(library.Resolve("01 song"));
        Assert.Single(warnings);
        Assert.Equal(warnings, reversedWarnings);
    }

    [Fact]
    public void Discover_DoesNotFollowFileSymlinks()
    {
        var target = Write("source.txt");
        File.CreateSymbolicLink(Path.Combine(_folder, "01 Linked.mp3"), target);
        var warnings = new List<string>();
        Assert.Empty(CustomMusicLibrary.Discover(_folder, warnings.Add).Names);
        Assert.Single(warnings);
    }

    private string Write(string name)
    {
        var path = Path.Combine(_folder, name);
        File.WriteAllText(path, "");
        return path;
    }

    public void Dispose() => Directory.Delete(_folder, recursive: true);
}
