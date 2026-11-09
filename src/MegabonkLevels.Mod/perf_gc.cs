using System;
using System.Diagnostics;
using System.Diagnostics.Tracing;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Samples GC pause for each measurement window through the runtime's GC events — SuspendEEBegin..GCRestartEEEnd is
// exactly the pause GC.GetTotalPauseDuration sums, and that .NET 7 API is unavailable to a net6 mod. The listener is
// CoreCLR-side, so Unity's engine stripping (which removed the PlayerLoop and FrameTiming APIs from this build) can
// never touch it. Enabled once, kept on, snapshotted per window; the cost is two events per GC.
public static class PerfGc
{
    private static ModLogger _logger;
    private static GcPauseListener _listener;
    private static long _pauseStartTicks;
    private static int _collectionsStart;

    public static void Install(ModLogger logger) => _logger = logger;

    public static void ClearWindow()
    {
        EnsureListener();
        _pauseStartTicks = _listener?.PauseTicks ?? 0;
        _collectionsStart = _listener?.Collections ?? 0;
    }

    public static void AddTo(JsonObject root, int frames)
    {
        var pauseTicks = (_listener?.PauseTicks ?? 0) - _pauseStartTicks;
        var pauseMs = pauseTicks * 1000d / Stopwatch.Frequency;
        root["gcPauseMsPerFrame"] = Math.Round(PerfGcPlan.GcPauseMsPerFrame(pauseMs, frames), 4);
        root["gcCollections"] = (_listener?.Collections ?? 0) - _collectionsStart;
    }

    private static void EnsureListener()
    {
        if (_listener != null || _logger == null)
        {
            return;
        }

        try
        {
            _listener = new GcPauseListener();
        }
        catch (Exception e)
        {
            _listener = null;
            _logger.Msg($"Perf: GC listener unavailable, gcPauseMsPerFrame will read 0 ({e.GetType().Name})");
        }
    }

    private sealed class GcPauseListener : EventListener
    {
        public long PauseTicks;

        public int Collections;

        private long _suspendStart;

        protected override void OnEventSourceCreated(EventSource source)
        {
            if (source.Name == "Microsoft-Windows-DotNETRuntime")
            {
                EnableEvents(source, EventLevel.Informational, (EventKeywords)0x1);
            }
        }

        protected override void OnEventWritten(EventWrittenEventArgs eventArgs)
        {
            switch (eventArgs.EventName)
            {
                case "GCSuspendEEBegin":
                    Collections++;
                    _suspendStart = Stopwatch.GetTimestamp();
                    break;
                case "GCRestartEEEnd":
                    if (_suspendStart != 0)
                    {
                        PauseTicks += Stopwatch.GetTimestamp() - _suspendStart;
                        _suspendStart = 0;
                    }

                    break;
            }
        }
    }
}
