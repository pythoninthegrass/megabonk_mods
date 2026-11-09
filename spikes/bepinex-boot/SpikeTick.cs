using System;
using BepInEx.Logging;
using UnityEngine;

namespace BepInExBootSpike;

public class SpikeTick : MonoBehaviour
{
    public SpikeTick(IntPtr ptr) : base(ptr) { }

    private float _nextLog;

    private void Update()
    {
        if (Time.unscaledTime < _nextLog)
            return;
        _nextLog = Time.unscaledTime + 5f;
        SpikePlugin.LogSource.LogInfo($"Spike: tick t={Time.unscaledTime:F1}s");
    }
}
