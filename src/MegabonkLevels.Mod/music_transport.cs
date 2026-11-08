using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace MegabonkLevels;

// The actions of the music harness command and the console verbs bound to it.
public static class MusicActions
{
    public const string Play = "play";
    public const string Pause = "pause";
    public const string Next = "next";
    public const string Prev = "prev";
    public const string Track = "track";
    public const string List = "list";
    public const string Now = "now";

    public static readonly string[] Names = { Play, Pause, Next, Prev, Track, List, Now };
}

// One music transport request: the action, and the 1-based track number when the action is track.
public sealed class MusicArgs
{
    public string Action { get; init; }

    public int Track { get; init; }
}

// The console text for each music transport outcome; numbers are 1-based and 0 means no track is chosen.
public static class MusicTransportReply
{
    public const string NoPlaylist = "no custom playlist on this stage";

    private static readonly Regex LeadingFileNumber = new(@"^\d+(?:[._]\d+)*[ _.\-]+(?=.)", RegexOptions.Compiled);

    // A clip's own file number (06_01, 37) differs from its playlist position, so the console shows the name without it.
    public static string DisplayName(string name) => LeadingFileNumber.Replace(name, "");

    public static string List(IReadOnlyList<string> names, int current) =>
        string.Join("\n", names.Select((name, at) => $" {(at + 1 == current ? ">" : " ")}{at + 1,2}  {DisplayName(name)}"));

    public static string Now(IReadOnlyList<string> names, int current) =>
        current < 1 ? "no track chosen yet" : $"{current}/{names.Count}  {DisplayName(names[current - 1])}";

    public static string Changed(IReadOnlyList<string> names, int current) => "playing " + Now(names, current);

    // UnPause on a stopped source starts nothing, so the reply follows whether the source is playing afterwards.
    public static string Resume(bool wasPlaying, bool nowPlaying) =>
        wasPlaying ? "music is already playing" : nowPlaying ? "music resumed" : "no paused music to resume";

    public static string Pause(bool wasPlaying) => wasPlaying ? "music paused" : "music is not playing";

    public static string OutOfRange(int number, int count) => $"track {number} is not between 1 and {count}";
}
