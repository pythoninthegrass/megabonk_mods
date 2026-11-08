using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;

namespace MegabonkLevels;

// Whether MEGABONK_DEV is on in the game's environment, which gates the cheat and debug verbs.
public readonly record struct ConsoleDevState(bool DevEnabled);

// The state a toggle verb flips when typed with no argument, read from the mod's live state.
public readonly record struct ConsoleToggleState(bool Invulnerable, bool Editor, bool Hud, bool Coordinates);

// The outcome of binding one console line: Command is what the console hands to the harness, Reply is text to print,
// and Error is a refusal or a usage line. Ok means nothing was refused. ListHistory asks the console to print the
// remembered lines, which only the console holds.
public readonly record struct ConsoleBindResult(HarnessCommand? Command, string Reply, string Error, bool ListHistory = false)
{
    public bool Ok => Error == null;
}

// One console verb: how to bind its arguments to a harness command, plus the help, usage and gating the console shows.
public sealed class ConsoleVerb
{
    private readonly Func<IReadOnlyList<string>, ConsoleToggleState, IReadOnlyList<string>, ConsoleBindResult> _bind;

    public ConsoleVerb(string name, string help, bool gated, Func<IReadOnlyList<string>, ConsoleToggleState, IReadOnlyList<string>, ConsoleBindResult> bind, string usage = null)
    {
        Name = name;
        Help = help;
        Gated = gated;
        _bind = bind;
        Usage = usage ?? "usage: " + name;
    }

    public string Name { get; }

    public string Help { get; }

    public bool Gated { get; }

    public string Usage { get; }

    public string[] Aliases { get; private set; } = Array.Empty<string>();

    // A verb whose binding raises its own message (level.load's title errors) keeps it instead of the usage line.
    public bool RawError { get; private set; }

    public ConsoleVerb WithRawError()
    {
        RawError = true;
        return this;
    }

    public ConsoleVerb WithAliases(params string[] aliases)
    {
        Aliases = aliases;
        return this;
    }

    internal ConsoleBindResult Bind(IReadOnlyList<string> args, ConsoleToggleState toggles, IReadOnlyList<string> levels) => _bind(args, toggles, levels);
}

// The prefixes Tab completes over, and which match the key is cycling through. Index is -1 when nothing matches.
public readonly record struct ConsoleCompletion(IReadOnlyList<string> Matches, int Index, string Prefix)
{
    public string Text => Matches is { Count: > 0 } m && Index >= 0 && Index < m.Count ? m[Index] : "";

    // The characters to insert after the prefix to complete the word.
    public string Completion => Text.Length >= Prefix.Length ? Text.Substring(Prefix.Length) : "";

    // Tab cycles the matches and wraps at the ends; an empty match set stays empty.
    public ConsoleCompletion Next() => Matches is { Count: > 0 } m ? this with { Index = (Index + 1) % m.Count } : this;

    public ConsoleCompletion Prev() => Matches is { Count: > 0 } m ? this with { Index = (Index - 1 + m.Count) % m.Count } : this;
}

// The console's command language: every verb, its aliases, its gating flag, and the binding from typed arguments to
// the same JSON payload run.py sends, which HarnessCommand.TryParse then validates.
public sealed class ConsoleCommandRegistry
{
    public const string GatedReply = "requires MEGABONK_DEV";

    private const int MinDamageAmount = 1;

    private const int MaxDamageAmount = 99;

    private static readonly string[] PerfActions = { "report", "status", "start", "reset", "spawn", "timescale", "toggle", "vsync", "render", "physics", "animation", "health", "census" };

    private readonly Dictionary<string, ConsoleVerb> _byName = new(StringComparer.OrdinalIgnoreCase);

    private readonly List<ConsoleVerb> _verbs = new();

    public static ConsoleCommandRegistry Default { get; } = Build();

    public IReadOnlyList<ConsoleVerb> Verbs => _verbs;

    public ConsoleVerb Find(string name) => name != null && _byName.TryGetValue(name, out var verb) ? verb : null;

    public ConsoleBindResult Bind(string line, ConsoleDevState dev, ConsoleToggleState toggles, IReadOnlyList<string> levels = null)
    {
        var tokens = ConsoleCommandTokenizer.Tokenize(line);
        if (tokens.Tokens == null)
        {
            return new ConsoleBindResult(null, null, tokens.Error);
        }

        if (tokens.IsBlank)
        {
            return new ConsoleBindResult(null, null, null);
        }

        var verb = Find(tokens.Verb);
        if (verb == null)
        {
            return new ConsoleBindResult(null, null, UnknownVerb(tokens.Verb));
        }

        if (verb.Gated && !dev.DevEnabled)
        {
            return new ConsoleBindResult(null, null, GatedReply);
        }

        // help reads the whole verb table and hides gated verbs when the dev flag is off, so it is produced here where dev is known.
        if (verb.Name == "help")
        {
            return tokens.Arguments.Count <= 1
                ? new ConsoleBindResult(null, Help(tokens.Arguments.Count == 1 ? tokens.Arguments[0] : null, dev.DevEnabled), null)
                : new ConsoleBindResult(null, null, verb.Usage);
        }

        var result = verb.Bind(tokens.Arguments, toggles, levels);
        if (result.Error == "no match")
        {
            return new ConsoleBindResult(null, null, verb.Usage);
        }

        if (result.Error != null && !verb.RawError && !result.Error.StartsWith("usage:", StringComparison.Ordinal))
        {
            return new ConsoleBindResult(null, null, result.Error + "\n" + verb.Usage);
        }

        return result;
    }

    // The verbs and aliases a Tab should offer for a prefix. Cycling lives in the returned value, so a fresh prefix starts at the first match.
    public ConsoleCompletion Complete(string prefix) =>
        new(MatchNames(prefix ??= ""), 0, prefix);

    private List<string> MatchNames(string prefix) =>
        _verbs
            .SelectMany(VerbNames)
            .Where(name => name.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(name => name, StringComparer.Ordinal)
            .ToList();

    // help [filter]: one aligned line per verb the caller may use, with its aliases; gated verbs need the dev flag.
    private string Help(string filter, bool dev)
    {
        var rows = _verbs
            .Where(verb => (dev || !verb.Gated)
                && (filter == null || verb.Name.StartsWith(filter, StringComparison.OrdinalIgnoreCase)
                    || verb.Aliases.Any(a => a.StartsWith(filter, StringComparison.OrdinalIgnoreCase))))
            .Select(verb => (Names: verb.Name + (verb.Aliases.Length > 0 ? ", " + string.Join(", ", verb.Aliases) : ""), verb.Help))
            .ToList();

        return rows.Count == 0
            ? "no verb matches " + filter
            : string.Join("\n", rows.Select(row => row.Names.PadRight(rows.Max(r => r.Names.Length) + 2) + row.Help));
    }

    private string UnknownVerb(string typed)
    {
        var suggestions = Suggest(typed);
        var message = $"unknown verb '{typed}'";
        return suggestions.Count == 0 ? message : message + "; did you mean " + string.Join(", ", suggestions) + "?";
    }

    // The nearest verb names from the whole table, so a refusal on a gated verb still names the right one.
    private static IEnumerable<string> VerbNames(ConsoleVerb verb)
    {
        yield return verb.Name;
        foreach (var alias in verb.Aliases)
        {
            yield return alias;
        }
    }

    private List<string> Suggest(string typed)
    {
        var lower = typed.ToLowerInvariant();
        var threshold = Math.Max(2, typed.Length / 2);

        return _verbs
            .SelectMany(VerbNames)
            .Select(name => (name, distance: Distance(lower, name.ToLowerInvariant())))
            .Where(row => row.distance <= threshold || row.name.StartsWith(typed, StringComparison.OrdinalIgnoreCase))
            .OrderBy(row => row.distance)
            .ThenBy(row => row.name, StringComparer.Ordinal)
            .Select(row => row.name)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(3)
            .ToList();
    }

    private static int Distance(string a, string b)
    {
        var previous = new int[b.Length + 1];
        var current = new int[b.Length + 1];
        for (var j = 0; j <= b.Length; j++)
        {
            previous[j] = j;
        }

        for (var i = 1; i <= a.Length; i++)
        {
            current[0] = i;
            for (var j = 1; j <= b.Length; j++)
            {
                var cost = a[i - 1] == b[j - 1] ? 0 : 1;
                current[j] = Math.Min(Math.Min(current[j - 1] + 1, previous[j] + 1), previous[j - 1] + cost);
            }

            (previous, current) = (current, previous);
        }

        return previous[b.Length];
    }

    private ConsoleVerb Add(ConsoleVerb verb)
    {
        _verbs.Add(verb);
        _byName[verb.Name] = verb;
        foreach (var alias in verb.Aliases)
        {
            _byName[alias] = verb;
        }

        return verb;
    }

    // The verb table; music transport verbs plug into this same table.
    private static ConsoleCommandRegistry Build()
    {
        var registry = new ConsoleCommandRegistry();

        registry.Add(new ConsoleVerb("help", "list verbs, aliases and one line of help", false, (args, _, _) =>
            args.Count <= 1 ? new ConsoleBindResult(null, null, null) : NoMatch())
            .WithAliases("?"));
        registry.Add(new ConsoleVerb("clear", "clear the console scrollback", false, (_, _, _) => NoCommand()).WithAliases("cls"));
        registry.Add(new ConsoleVerb("history", "list the lines typed in earlier sessions and this one", false,
            (_, _, _) => new ConsoleBindResult(null, "", null, ListHistory: true)));

        registry.Add(new ConsoleVerb("state", "read the game's current state", false, (_, _, _) => Command(HarnessCommandKind.State)));

        registry.Add(new ConsoleVerb("player.teleport", "move the player to a world position", true, (args, _, _) =>
            args.Count == 3 && Floats(args, out var position)
                ? Command(new HarnessCommand(HarnessCommandKind.Teleport, null, Teleport: new TeleportArgs { Position = position }))
                : NoMatch(), "usage: player.teleport x y z")
            .WithAliases("tp"));
        registry.Add(new ConsoleVerb("player.teleport_cell", "move the player to a grid cell", true, (args, _, _) =>
            args.Count == 2 && Ints(args, out var cell)
                ? Command(new HarnessCommand(HarnessCommandKind.Teleport, null, Teleport: new TeleportArgs { Cell = cell }))
                : NoMatch()));
        registry.Add(new ConsoleVerb("player.god", "make the player survive damage", true, (args, toggles, _) =>
            Flag(args, toggles.Invulnerable) is bool invulnerable
                ? Enabled(invulnerable ? HarnessCommandKind.Invulnerable : HarnessCommandKind.Vulnerable, invulnerable)
                : NoMatch())
            .WithAliases("tgm"));
        registry.Add(new ConsoleVerb("player.kill", "end the run at once", true, (_, _, _) => Command(HarnessCommandKind.Kill)));
        registry.Add(new ConsoleVerb("player.damage", "apply 1-99 damage, fatal with 'lethal'", true, (args, _, _) =>
            args.Count is 1 or 2 && Int(args[0], MinDamageAmount, MaxDamageAmount, out var amount) && Nonlethal(args) is bool nonlethal
                ? Command(new HarnessCommand(HarnessCommandKind.Damage, null, Damage: new DamageArgs { Amount = amount, Nonlethal = nonlethal }))
                : NoMatch()));
        registry.Add(new ConsoleVerb("player.add_item", "read or set an item amount", true, (args, _, _) =>
        {
            var amount = 0;
            return args.Count is 1 or 2 && args[0].Length > 0 && (args.Count == 1 || Int(args[1], 0, HarnessCommand.MaxItemAmount, out amount))
                ? Command(new HarnessCommand(HarnessCommandKind.Item, null, Item: new ItemArgs { Name = args[0], Amount = args.Count == 2 ? amount : (int?)null }))
                : NoMatch();
        }));
        registry.Add(new ConsoleVerb("player.fall_damage", "read the live fall-damage inputs", true, (_, _, _) => Command(HarnessCommandKind.FallDamage)));

        registry.Add(new ConsoleVerb("enemies.kill", "kill nearest, all or bosses", true, (args, _, _) =>
        {
            // killall is the bare alias for the all target; the verb itself names the target.
            var target = args.Count == 0 ? EnemyKillTargets.All : args[0].ToLowerInvariant();
            return Array.IndexOf(EnemyKillTargets.Names, target) >= 0
                ? Command(new HarnessCommand(HarnessCommandKind.KillEnemies, null, KillTarget: target))
                : NoMatch();
        })
            .WithAliases("killall"));
        registry.Add(new ConsoleVerb("enemies.spawns", "allow or stop new enemy spawns", true, (args, _, _) =>
            Flag(args, true) is bool spawns ? Enabled(HarnessCommandKind.Spawns, spawns) : NoMatch()));

        registry.Add(new ConsoleVerb("run.freeze", "stop gameplay", true, (_, _, _) => Command(HarnessCommandKind.Freeze)));
        registry.Add(new ConsoleVerb("run.resume", "start gameplay again", true, (_, _, _) => Command(HarnessCommandKind.Resume)));
        registry.Add(new ConsoleVerb("run.restart", "run the death screen's Retry", true, (_, _, _) => Command(HarnessCommandKind.RestartRun)));
        registry.Add(new ConsoleVerb("run.dismiss_levelup", "pick an upgrade in the level-up dialog", true, (args, _, _) =>
        {
            var choice = 0;
            return args.Count <= 1 && (args.Count == 0 || Int(args[0], 0, int.MaxValue, out choice))
                ? Command(new HarnessCommand(HarnessCommandKind.DismissLevelUp, null, Choice: args.Count == 1 ? choice : 0))
                : NoMatch();
        }));
        registry.Add(new ConsoleVerb("run.dismiss_offers", "close, pick or skip the open reward window", true, (args, _, _) =>
            args.Count switch
            {
                0 => Command(new HarnessCommand(HarnessCommandKind.DismissOffers, null)),
                1 when args[0] == "skip" => Command(new HarnessCommand(HarnessCommandKind.DismissOffers, null, Skip: true)),
                1 when Int(args[0], 0, int.MaxValue, out var offer) => Command(new HarnessCommand(HarnessCommandKind.DismissOffers, null, Offer: offer)),
                _ => NoMatch(),
            }));
        registry.Add(new ConsoleVerb("run.interact", "activate the nearest interactable, or one type", true, (args, _, _) =>
            args.Count <= 1 && (args.Count == 0 || args[0].Length > 0)
                ? Command(new HarnessCommand(HarnessCommandKind.Interact, null, Interact: new InteractArgs { Type = args.Count == 1 ? args[0] : null }))
                : NoMatch()));
        registry.Add(new ConsoleVerb("run.press_death_confirm", "press the death screen's confirm", true, (_, _, _) => Command(HarnessCommandKind.PressDeathConfirm)));
        registry.Add(new ConsoleVerb("run.press_summary_restart", "press the run summary's restart", true, (_, _, _) => Command(HarnessCommandKind.PressSummaryRestart)));

        registry.Add(new ConsoleVerb("level.list", "list the saved custom-level files", false, (_, _, _) => Command(HarnessCommandKind.ListLevels)));
        registry.Add(new ConsoleVerb("level.load", "load a level by path or title, with map/stage/tier/seed/noseed", true, (args, _, levels) => LoadLevel(args, levels))
            .WithAliases("coc").WithRawError());
        registry.Add(new ConsoleVerb("level.save", "save the editor's level, optionally under a name", true, (args, _, _) =>
            args.Count <= 1 && (args.Count == 0 || args[0].Trim().Length > 0)
                ? Command(new HarnessCommand(HarnessCommandKind.SaveLevel, args.Count == 1 ? args[0] : null))
                : NoMatch()));
        registry.Add(new ConsoleVerb("level.new", "write a blank level and edit it, with map/stage/tier/size", true, (args, _, _) => NewLevel(args)));

        registry.Add(new ConsoleVerb("editor", "enter or leave editor mode", true, (args, toggles, _) =>
            Flag(args, toggles.Editor) is bool editor ? Enabled(HarnessCommandKind.Editor, editor) : NoMatch())
            .WithAliases("tfc"));
        registry.Add(new ConsoleVerb("camera.set", "hold the camera at a pose", true, (args, _, _) =>
            args.Count == 6 && Floats(args, out var pose)
                ? Command(new HarnessCommand(HarnessCommandKind.Camera, null, new CameraPose(pose[0], pose[1], pose[2], pose[3], pose[4], pose[5])))
                : NoMatch()));
        registry.Add(new ConsoleVerb("camera.clear", "return the camera to the game", true, (_, _, _) => Command(HarnessCommandKind.CameraClear)));

        registry.Add(new ConsoleVerb("ui.hud", "show or hide the stock HUD", false, (args, toggles, _) =>
            Flag(args, toggles.Hud) is bool hud ? Enabled(HarnessCommandKind.Hud, hud) : NoMatch())
            .WithAliases("tm"));
        registry.Add(new ConsoleVerb("ui.coordinates", "show or hide coordinates", false, (args, toggles, _) =>
            Flag(args, toggles.Coordinates) is bool coordinates ? Enabled(HarnessCommandKind.Coordinates, coordinates) : NoMatch()));

        foreach (var action in PerfActions)
        {
            registry.Add(new ConsoleVerb("perf." + action, PerfHelp(action), true, (args, _, _) => Perf(action, args), PerfUsage(action)));
        }

        registry.Add(new ConsoleVerb("time_scale", "hold MyTime.timeScale, or release it with no value", true, (args, _, _) => Perf("timescale", args), "usage: time_scale [value]"));

        registry.Add(new ConsoleVerb("debug.screenshot", "save the rendered frame as a PNG", true, (args, _, _) =>
            args.Count == 1 && args[0].Trim().Length > 0
                ? Command(new HarnessCommand(HarnessCommandKind.Screenshot, args[0]))
                : NoMatch()));
        registry.Add(new ConsoleVerb("debug.query_objects", "list loaded objects of a type with chosen fields", true, (args, _, _) =>
            args.Count >= 1 && args[0].Length > 0 && args.Skip(1).All(f => f.Length > 0)
                ? Command(new HarnessCommand(HarnessCommandKind.QueryObjects, null, Query: new QueryArgs { TypeName = args[0], Fields = args.Skip(1).ToArray() }))
                : NoMatch()));
        registry.Add(new ConsoleVerb("debug.material_dump", "dump the materials under the named objects", true, (args, _, _) =>
            args.Count <= 1 && (args.Count == 0 || args[0].Trim().Length > 0)
                ? Command(new HarnessCommand(HarnessCommandKind.MaterialDump, args.Count == 1 ? args[0] : null))
                : NoMatch()));
        registry.Add(new ConsoleVerb("debug.shader_report", "list the shaders the game ships and uses", true, (_, _, _) => Command(HarnessCommandKind.ShaderReport)));
        registry.Add(new ConsoleVerb("debug.heartbeat", "start or stop the kill-floor heartbeat", true, (args, _, _) =>
            Flag(args, true) is bool heartbeat ? Enabled(HarnessCommandKind.Heartbeat, heartbeat) : NoMatch()));
        registry.Add(new ConsoleVerb("debug.cells", "start or stop the cell-change log", true, (args, _, _) =>
            Flag(args, true) is bool cells ? Enabled(HarnessCommandKind.Cells, cells) : NoMatch()));
        registry.Add(new ConsoleVerb("debug.ui_tree", "list the editor widgets, or the one at a pixel", true, (args, _, _) =>
            args.Count switch
            {
                0 => Command(new HarnessCommand(HarnessCommandKind.UiTree, null, Input: new InputArgs { Action = "ui-tree" })),
                2 when Float(args[0], out var x) && Float(args[1], out var y) => Command(new HarnessCommand(HarnessCommandKind.UiTree, null, Input: new InputArgs { Action = "ui-tree", X = x, Y = y })),
                _ => NoMatch(),
            }));
        registry.Add(new ConsoleVerb("debug.click_widget", "click the named editor widget", true, (args, _, _) =>
            args.Count == 1 && args[0].Length > 0
                ? Command(new HarnessCommand(HarnessCommandKind.ClickWidget, null, Input: new InputArgs { Action = "click-widget", Text = args[0] }))
                : NoMatch()));

        registry.Add(new ConsoleVerb("app.quit", "quit the game", true, (_, _, _) => Command(HarnessCommandKind.Quit))
            .WithAliases("qqq"));

        registry.Add(new ConsoleVerb("music.play", "resume paused music", false, (args, _, _) => MusicTransport(args, MusicActions.Play)));
        registry.Add(new ConsoleVerb("music.pause", "pause the current music", false, (args, _, _) => MusicTransport(args, MusicActions.Pause)));
        registry.Add(new ConsoleVerb("music.next", "go to the next track", false, (args, _, _) => MusicTransport(args, MusicActions.Next)));
        registry.Add(new ConsoleVerb("music.prev", "go to the previous track", false, (args, _, _) => MusicTransport(args, MusicActions.Prev)));
        registry.Add(new ConsoleVerb("music.track", "jump to track n", false, (args, _, _) =>
            args.Count == 1 && Int(args[0], 1, int.MaxValue, out var track)
                ? Command(new HarnessCommand(HarnessCommandKind.Music, null, Music: new MusicArgs { Action = MusicActions.Track, Track = track }))
                : NoMatch(), "usage: music.track n"));
        registry.Add(new ConsoleVerb("music.list", "list the tracks, marking the current one", false, (args, _, _) => MusicTransport(args, MusicActions.List)));
        registry.Add(new ConsoleVerb("music.now", "show the current track", false, (args, _, _) => MusicTransport(args, MusicActions.Now)));

        return registry;
    }

    private static ConsoleBindResult MusicTransport(IReadOnlyList<string> args, string action) =>
        args.Count == 0 ? Command(new HarnessCommand(HarnessCommandKind.Music, null, Music: new MusicArgs { Action = action })) : NoMatch();

    // Console-only verbs produce no harness command; the console handles them itself.
    private static ConsoleBindResult NoCommand() => new(null, "", null);

    // The binding rejects the arguments; Bind turns this sentinel into the verb's usage line.
    private static ConsoleBindResult NoMatch() => new(null, null, "no match");

    private static ConsoleBindResult Command(HarnessCommandKind kind) => new(new HarnessCommand(kind, null), null, null);

    private static ConsoleBindResult Command(HarnessCommand command) => new(command, null, null);

    private static ConsoleBindResult Enabled(HarnessCommandKind kind, bool enabled) => new(new HarnessCommand(kind, null, Enabled: enabled), null, null);

    private static string PerfHelp(string action) => action switch
    {
        "report" => "frame percentiles for the last window",
        "status" => "the live profiler toggles",
        "start" => "clear the window and start measuring",
        "reset" => "restore every profiler setting",
        "spawn" => "add enemies around the player",
        "timescale" => "hold or release MyTime.timeScale",
        "toggle" => "switch one tick or patch probe",
        "vsync" => "lift or restore the vsync cap",
        "render" => "hide or show enemy renderers",
        "physics" => "freeze or unfreeze enemy rigidbodies",
        "animation" => "stop or resume enemy animation",
        "health" => "park the player's hit points",
        "census" => "count components by type",
        _ => "frame profiler",
    };

    private static string PerfUsage(string action) => action switch
    {
        "toggle" => "usage: perf.toggle <target> <on|off>",
        "vsync" or "render" or "physics" or "animation" => $"usage: perf.{action} <on|off>",
        "spawn" => $"usage: perf.spawn <1-{PerfSpawnPlan.MaxEnemies}>",
        "timescale" => "usage: perf.timescale [value]",
        "health" => "usage: perf.health [hp]",
        _ => $"usage: perf.{action}",
    };

    private static ConsoleBindResult Perf(string action, IReadOnlyList<string> args)
    {
        switch (action)
        {
            case "spawn":
                return args.Count == 1 && Int(args[0], 1, PerfSpawnPlan.MaxEnemies, out var count)
                    ? Command(new HarnessCommand(HarnessCommandKind.Perf, null, Perf: new PerfArgs { Action = action, Count = count }))
                    : NoMatch();
            case "timescale":
                var value = 0f;
                return args.Count <= 1 && (args.Count == 0 || (Float(args[0], out value) && PerfLimits.ValidTimeScale(value)))
                    ? Command(new HarnessCommand(HarnessCommandKind.Perf, null, Perf: new PerfArgs { Action = action, Value = args.Count == 1 ? value : (float?)null }))
                    : NoMatch();
            case "toggle":
                return args.Count == 2 && args[0].Length > 0 && OnOff(args[1]) is bool target
                    ? Command(new HarnessCommand(HarnessCommandKind.Perf, null, Perf: new PerfArgs { Action = action, Target = args[0], Enabled = target }))
                    : NoMatch();
            case "vsync" or "render" or "physics" or "animation":
                return args.Count == 1 && OnOff(args[0]) is bool flag
                    ? Command(new HarnessCommand(HarnessCommandKind.Perf, null, Perf: new PerfArgs { Action = action, Enabled = flag }))
                    : NoMatch();
            case "health":
                var hp = 0;
                return args.Count <= 1 && (args.Count == 0 || Int(args[0], 1, PerfLimits.MaxPlayerHp, out hp))
                    ? Command(new HarnessCommand(HarnessCommandKind.Perf, null, Perf: new PerfArgs { Action = action, Hp = args.Count == 1 ? hp : (int?)null }))
                    : NoMatch();
            default:
                return args.Count == 0
                    ? Command(new HarnessCommand(HarnessCommandKind.Perf, null, Perf: new PerfArgs { Action = action }))
                    : NoMatch();
        }
    }

    private static ConsoleBindResult LoadLevel(IReadOnlyList<string> args, IReadOnlyList<string> levels)
    {
        if (args.Count == 0 || string.IsNullOrWhiteSpace(args[0]))
        {
            return NoMatch();
        }

        var resolved = ResolveLevelTarget(args[0], levels, out var error);
        if (resolved == null)
        {
            return new ConsoleBindResult(null, null, error);
        }

        var overrides = ParseOverrides(args.Skip(1).ToArray(), false);
        return overrides.Bad
            ? NoMatch()
            : Command(new HarnessCommand(HarnessCommandKind.LoadLevel, resolved, Overrides: new LoadOverrides(overrides.Map, overrides.Stage, overrides.Tier, overrides.Seed, null, overrides.Unseeded)));
    }

    private static ConsoleBindResult NewLevel(IReadOnlyList<string> args)
    {
        var name = args.Count > 0 && args[0].Trim().Length > 0 ? args[0] : null;
        var overrides = ParseOverrides(args.Skip(name == null ? 0 : 1).ToArray(), true);
        return overrides.Bad
            ? NoMatch()
            : Command(new HarnessCommand(
                HarnessCommandKind.NewLevel,
                name,
                NewLevel: new NewLevelArgs(overrides.Map ?? (int)EMap.Forest, overrides.Stage ?? 0, overrides.Tier ?? 0, overrides.Size ?? BlankLevel.DefaultSize)));
    }

    private readonly record struct OptionSet(int? Map, int? Stage, int? Tier, int? Seed, int? Size, bool Unseeded, bool Bad)
    {
        public static OptionSet Rejected { get; } = new(null, null, null, null, null, false, true);
    }

    // map/stage/tier/seed/noseed pairs, the fields load-level carries; an odd token or a bad value is Bad.
    private static OptionSet ParseOverrides(IReadOnlyList<string> args, bool allowSize)
    {
        int? map = null, stage = null, tier = null, seed = null, size = null;
        var unseeded = false;

        for (var i = 0; i < args.Count; i++)
        {
            var last = i == args.Count - 1;
            if (args[i] == "noseed" && last)
            {
                unseeded = true;
                continue;
            }

            if (last)
            {
                return OptionSet.Rejected;
            }

            var ok = true;
            switch (args[i])
            {
                case "map":
                    ok = Int(args[i + 1], 0, int.MaxValue, out var m) && ValidMap(m) && Set(m, v => map = v);
                    break;
                case "stage":
                    ok = Int(args[i + 1], 0, int.MaxValue, out var s) && Set(s, v => stage = v);
                    break;
                case "tier":
                    ok = Int(args[i + 1], 0, int.MaxValue, out var t) && Set(t, v => tier = v);
                    break;
                case "seed":
                    ok = Int(args[i + 1], int.MinValue, int.MaxValue, out var d) && Set(d, v => seed = v);
                    break;
                case "size" when allowSize:
                    ok = Int(args[i + 1], BlankLevel.MinimumSize, int.MaxValue, out var z) && Set(z, v => size = v);
                    break;
                default:
                    ok = false;
                    break;
            }

            if (!ok)
            {
                return OptionSet.Rejected;
            }

            i++;
        }

        return new OptionSet(map, stage, tier, seed, size, unseeded, false);
    }

    private static bool Set<T>(T value, Action<T> assign)
    {
        assign(value);
        return true;
    }

    private static bool ValidMap(int value) => Enum.GetValues<EMap>().Any(m => m != EMap.None && (int)m == value);

    // A target is a file name (as typed, or with the level extension added) or a title matched against the level list
    // ignoring case, spaces and punctuation. A path that already exists on disk is left exactly as typed.
    private static string ResolveLevelTarget(string target, IReadOnlyList<string> levels, out string error)
    {
        error = null;
        var hasExtension = target.EndsWith(".json", StringComparison.OrdinalIgnoreCase);

        if (target.Contains('/') || target.Contains('\\'))
        {
            return target;
        }

        var fileName = hasExtension ? target : target + ".mblevel.json";
        if (levels == null || levels.Count == 0)
        {
            return fileName;
        }

        // Match a level title first (case, spaces and punctuation ignored); a file whose whole name equals the target is the fallback.
        var wanted = Normalize(target);
        var matches = levels.Where(l => Normalize(LevelStem(l)) == wanted).ToList();

        if (matches.Count == 1)
        {
            return matches[0];
        }

        if (matches.Count > 1)
        {
            error = $"'{target}' is ambiguous: {string.Join(", ", matches)}";
            return null;
        }

        var exact = levels.FirstOrDefault(l => string.Equals(l, fileName, StringComparison.OrdinalIgnoreCase));
        if (exact != null)
        {
            return exact;
        }

        error = $"no level named '{target}'; run level.list";
        return null;
    }

    private static string Normalize(string value) =>
        new((value ?? "").Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());

    // "foo.mblevel.json" and "foo.json" both reduce to the stem "foo"; a title matches that stem.
    private static string LevelStem(string fileName)
    {
        var stem = Path.GetFileNameWithoutExtension(fileName);
        return stem.EndsWith(".mblevel", StringComparison.OrdinalIgnoreCase)
            ? stem.Substring(0, stem.Length - ".mblevel".Length)
            : stem;
    }

    // "on"/"off" set the state directly; a bare verb flips the current state. The current state is only read when no argument is given.
    private static bool? Flag(IReadOnlyList<string> args, bool current) =>
        args.Count == 1 ? OnOff(args[0]) : args.Count == 0 ? !current : null;

    private static bool? OnOff(string value) =>
        string.Equals(value, "on", StringComparison.OrdinalIgnoreCase)
            ? true
            : string.Equals(value, "off", StringComparison.OrdinalIgnoreCase) ? false : (bool?)null;

    // "lethal" makes the damage fatal; an explicit on/off sets the nonlethal field; a single amount keeps 1 HP.
    private static bool? Nonlethal(IReadOnlyList<string> args) => args.Count switch
    {
        1 => true,
        2 when string.Equals(args[1], "lethal", StringComparison.OrdinalIgnoreCase) => false,
        2 when string.Equals(args[1], "nonlethal", StringComparison.OrdinalIgnoreCase) => true,
        2 => OnOff(args[1]),
        _ => null,
    };

    private static bool Int(string value, int min, int max, out int parsed) =>
        int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out parsed) && parsed >= min && parsed <= max;

    private static bool Ints(IReadOnlyList<string> args, out int[] values)
    {
        values = null;
        if (args.Count != 2)
        {
            return false;
        }

        values = new int[2];
        return Int(args[0], int.MinValue, int.MaxValue, out values[0]) && Int(args[1], int.MinValue, int.MaxValue, out values[1]);
    }

    private static bool Float(string value, out float parsed) =>
        float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out parsed) && !float.IsNaN(parsed) && !float.IsInfinity(parsed);

    private static bool Floats(IReadOnlyList<string> args, out float[] values)
    {
        values = null;
        var parsed = new float[args.Count];
        for (var i = 0; i < args.Count; i++)
        {
            if (!Float(args[i], out parsed[i]))
            {
                return false;
            }
        }

        values = parsed;
        return true;
    }
}
