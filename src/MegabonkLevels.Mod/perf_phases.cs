using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Diagnostics.Tracing;
using System.Runtime.InteropServices;
using System.Text.Json.Nodes;
using Il2CppInterop.Runtime;
using MelonLoader;
using UnityEngine.LowLevel;

namespace MegabonkLevels;

// Wraps every PlayerLoop subsystem with a timer so a window's frame time splits into engine phases, and samples GC
// pause through the runtime's GC events (the net6 shape of GC.GetTotalPauseDuration). Installed only by
// `perf phases on`; `off` restores the loop Unity was started with. Wrap paths and report math: perf_phase_plan.cs.
public static class PerfPhases
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void NativeUpdate();

    private static MelonLogger.Instance _logger;
    private static PlayerLoopSystem _original;
    private static readonly Dictionary<string, PhaseSlot> Slots = new();
    private static GcPauseListener _gc;
    private static long _gcPauseStartTicks;
    private static int _gcCollectionsStart;

    public static bool Installed => _original != null;

    public static void Install(MelonLogger.Instance logger) => _logger = logger;

    public static JsonObject Enable()
    {
        if (_original != null)
        {
            return new JsonObject { ["phases"] = "on", ["already"] = true };
        }

        _original = PlayerLoop.GetCurrentPlayerLoop();
        var root = _original;
        var wrapped = 0;
        if (root.subSystemList is { Length: > 0 })
        {
            root.subSystemList = WrapAll(root.subSystemList, "");
            wrapped = root.subSystemList.Length;
        }

        PlayerLoop.SetPlayerLoop(root);
        EnsureGcListener();
        Log($"phases: on, wrapping {wrapped} root subsystems");
        return new JsonObject { ["phases"] = "on", ["subsystems"] = wrapped };
    }

    public static JsonObject Disable()
    {
        if (_original == null)
        {
            return new JsonObject { ["phases"] = "off", ["already"] = true };
        }

        PlayerLoop.SetPlayerLoop(_original);
        _original = default;
        Log("phases: off, original player loop restored");
        return new JsonObject { ["phases"] = "off" };
    }

    // Always restore the engine's own loop when the mod unloads; a wrapped loop outliving the mod crashes the game.
    public static void Shutdown()
    {
        if (_original.subSystemList != null)
        {
            PlayerLoop.SetPlayerLoop(_original);
            _original = default;
            Log("phases: player loop restored at shutdown");
        }
    }

    public static void ClearWindow()
    {
        foreach (var slot in Slots.Values)
        {
            slot.Calls = 0;
            slot.TotalMs = 0d;
            slot.MaxMs = 0d;
        }

        EnsureGcListener();
        _gcPauseStartTicks = _gc?.PauseTicks ?? 0;
        _gcCollectionsStart = _gc?.Collections ?? 0;
    }

    public static JsonArray ReportNode()
    {
        if (_original.subSystemList == null)
        {
            return null;
        }

        var phases = new JsonArray();
        foreach (var pair in Slots)
        {
            phases.Add(new JsonObject
            {
                ["name"] = pair.Key,
                ["ms"] = Math.Round(pair.Value.TotalMs, 3),
                ["calls"] = pair.Value.Calls,
                ["maxMs"] = Math.Round(pair.Value.MaxMs, 3),
            });
        }

        return phases;
    }

    public static void AddGcTo(JsonObject root, int frames)
    {
        var pauseTicks = (_gc?.PauseTicks ?? 0) - _gcPauseStartTicks;
        var pauseMs = pauseTicks * 1000d / Stopwatch.Frequency;
        root["gcPauseMsPerFrame"] = Math.Round(PerfPhasePlan.GcPauseMsPerFrame(pauseMs, frames), 4);
        root["gcCollections"] = (_gc?.Collections ?? 0) - _gcCollectionsStart;
    }

    private static PlayerLoopSystem[] WrapAll(PlayerLoopSystem[] systems, string prefix)
    {
        var result = new PlayerLoopSystem[systems.Length];
        for (var i = 0; i < systems.Length; i++)
        {
            var system = systems[i];
            var name = system.type != null ? system.type.Name : $"system_{i}";
            var path = prefix.Length == 0 ? name : $"{prefix}.{name}";
            var slot = SlotFor(path);

            if (system.subSystemList is { Length: > 0 })
            {
                system.subSystemList = WrapAll(system.subSystemList, path);
            }

            var originalDelegate = system.updateDelegate;
            var originalFunction = system.updateFunction;
            if (originalDelegate == null && originalFunction == IntPtr.Zero)
            {
                result[i] = system;
                continue;
            }

            NativeUpdate native = null;
            if (originalDelegate == null)
            {
                native = Marshal.GetDelegateForFunctionPointer<NativeUpdate>(originalFunction);
            }

            PlayerLoopSystem.UpdateFunction wrapped = null;
            wrapped = DelegateSupport.ConvertDelegate<PlayerLoopSystem.UpdateFunction>((Action)(() =>
            {
                var startedAt = Stopwatch.GetTimestamp();
                try
                {
                    if (native != null)
                    {
                        native();
                    }
                    else
                    {
                        originalDelegate.Invoke();
                    }
                }
                finally
                {
                    PerfPhasePlan.Accumulate(slot, ElapsedMs(startedAt));
                }
            }));
            system.updateDelegate = wrapped;
            system.updateFunction = IntPtr.Zero;
            result[i] = system;
        }

        return result;
    }

    // GC pause measurement via the runtime event source: SuspendEEBegin..GCRestartEEEnd is exactly the pause
    // GetTotalPauseDuration sums. Enabled once, kept on, and snapshotted per window; two events per GC is the cost.
    private static void EnsureGcListener()
    {
        if (_gc != null)
        {
            return;
        }

        try
        {
            _gc = new GcPauseListener();
        }
        catch (Exception e)
        {
            _gc = null;
            Log($"phases: GC listener unavailable, gcPauseMsPerFrame will read 0 ({e.GetType().Name})");
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

    private static PhaseSlot SlotFor(string path)
    {
        if (!Slots.TryGetValue(path, out var slot))
        {
            slot = new PhaseSlot { Path = path };
            Slots[path] = slot;
        }

        return slot;
    }

    private static double ElapsedMs(double startedAt) => (Stopwatch.GetTimestamp() - startedAt) * 1000d / Stopwatch.Frequency;

    private static void Log(string message) => _logger?.Msg($"Perf: {message}");
}
