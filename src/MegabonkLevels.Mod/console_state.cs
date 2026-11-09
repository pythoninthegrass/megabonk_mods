using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// How far through the open/close slide the panel has moved: 0 parked below the bottom edge, 1 fully in place.
public readonly record struct ConsoleSlide(float Progress, bool Moving)
{
    public static ConsoleSlide Parked { get; } = new(0f, false);

    public static ConsoleSlide Shown { get; } = new(1f, false);
}

// What opening the console has to override, read at the moment the console opens.
public readonly record struct ConsoleEntryState(bool RunActive, bool Paused, bool CursorVisible, bool CursorLocked);

public enum ConsoleToggle
{
    Open,
    Close,
    Stay,
}

// The decisions behind the console overlay: whether a toggle may run, what the slide does, and what pause and cursor
// state a close restores. Unity-free so each rule is unit tested; the overlay itself only applies them.
public static class ConsoleState
{
    public const float SlideSeconds = 0.12f;

    public const string DevVariable = "MEGABONK_DEV";

    // The game's own F10 DebugConsole and an open game menu each own the keyboard, so the toggle key does nothing then.
    public static ConsoleToggle Toggle(bool open, bool devConsoleActive, bool gameMenuOpen) =>
        devConsoleActive || gameMenuOpen ? ConsoleToggle.Stay : open ? ConsoleToggle.Close : ConsoleToggle.Open;

    // Opening pauses a live run and remembers whether it was already paused; the main menu has no run to pause.
    public static bool ShouldPauseOnOpen(bool runActive) => runActive;

    // A run the console did not pause (already frozen in the editor, or held by the death screen) stays as it was;
    // only a run the console itself paused is unpaused on close.
    public static bool ShouldUnpauseOnClose(ConsoleEntryState? entry) => entry is { } state && state.RunActive && !state.Paused;

    public static bool ShouldRestoreCursor(ConsoleEntryState? entry) => entry != null;

    // The slide advances on unscaled time so it still animates while MyTime is paused.
    public static ConsoleSlide StepSlide(ConsoleSlide slide, bool open, float dt)
    {
        if (dt <= 0f || float.IsNaN(dt))
        {
            return slide with { Moving = false };
        }

        var step = dt / SlideSeconds;
        if (open)
        {
            if (slide.Progress >= 1f)
            {
                return slide with { Progress = 1f, Moving = false };
            }

            var up = slide.Progress + step;
            return up >= 1f ? ConsoleSlide.Shown : new ConsoleSlide(up, true);
        }

        if (slide.Progress <= 0f)
        {
            return slide with { Progress = 0f, Moving = false };
        }

        var down = slide.Progress - step;
        return down <= 0f ? ConsoleSlide.Parked : new ConsoleSlide(down, true);
    }

    public static ConsoleDevState DevState(Func<string, string> readEnvironment) =>
        new(EnvFlag.IsEnabled(readEnvironment(DevVariable)));

    public static ConsoleToggleState Toggles(Func<bool> invulnerable, Func<bool> editor, Func<bool> hud, Func<bool> coordinates) =>
        new(invulnerable(), editor(), hud(), coordinates());

    public static ConsoleLinePlan Execute(string line, ConsoleDevState dev, ConsoleToggleState toggles, Func<HarnessCommand, HarnessResult> runCommand, IReadOnlyList<string> history = null, IReadOnlyList<string> levels = null)
    {
        var bind = ConsoleCommandRegistry.Default.Bind(line, dev, toggles, levels);
        var ok = bind.Ok;
        var plan = Plan(line, bind, command =>
        {
            var result = runCommand(command);
            ok = result.Ok;
            return ReplyFor(result);
        }, history);
        return plan with { Ok = ok };
    }

    // A line with no verb is a no-op; a refusal echoes the line and the reply; a console-only verb prints its own
    // reply (or clears); a bound line runs through the harness and echoes the line plus what came back.
    public static ConsoleLinePlan Plan(string line, ConsoleBindResult bind, Func<HarnessCommand, string> runCommand, IReadOnlyList<string> history = null)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return ConsoleLinePlan.Blank;
        }

        var echo = "> " + line.Trim();
        if (!bind.Ok)
        {
            return new ConsoleLinePlan(new[] { echo, bind.Error }, false, false);
        }

        if (bind.ListHistory)
        {
            return new ConsoleLinePlan(HistoryLines(history), false, true);
        }

        if (bind.Command == null)
        {
            var clear = string.IsNullOrEmpty(bind.Reply);
            return new ConsoleLinePlan(clear ? Array.Empty<string>() : new[] { bind.Reply }, clear, true);
        }

        return new ConsoleLinePlan(new[] { echo, runCommand(bind.Command.Value) }, false, true);
    }

    private static IReadOnlyList<string> HistoryLines(IReadOnlyList<string> history)
    {
        if (history == null || history.Count == 0)
        {
            return new List<string> { "history is empty" };
        }

        var lines = new List<string>();
        for (var i = 0; i < history.Count; i++)
        {
            lines.Add($"{i + 1,3}  {history[i]}");
        }

        return lines;
    }

    // The line the console prints for one harness result: the result's message lines, or a generic ok/failure line.
    public static string ReplyFor(HarnessResult result)
    {
        if (!result.Ok)
        {
            return "error: " + result.Error;
        }

        if (result.Result is JsonObject payload && payload["message"] is JsonValue message && message.TryGetValue(out string text))
        {
            return text;
        }

        return result.Result == null ? "ok" : result.Result.ToJsonString();
    }
}

// What the console prints for one submitted line, whether it cleared the scrollback, and whether the line is
// remembered in history.
public readonly record struct ConsoleLinePlan(IReadOnlyList<string> PrintLines, bool ClearScrollback, bool RememberHistory, bool Ok = true)
{
    public static ConsoleLinePlan Blank { get; } = new(Array.Empty<string>(), false, false);
}
