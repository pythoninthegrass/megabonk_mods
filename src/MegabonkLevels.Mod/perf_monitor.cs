using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Text.Json.Nodes;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Inventory__Items__Pickups;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Weapons;
using Il2CppAssets.Scripts.Managers;
using Il2CppAssets.Scripts.Utility;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Which mod per-frame tick a toggle targets. DevHarnessPoll stays on whatever a toggle asks for: it is the command channel.
public enum PerfTick
{
    DevHarnessPoll,
    LoadPump,
    StartupCover,
    MaxSlopeAngle,
    KillFloor,
    GrindAssist,
    LevelMusic,
    MenuNotice,
    PositionLabel,
    EditorMode,
    Console,
    RenderCull,
    PhysicsFreeze,
    AnimationCull,
}

// Harness-driven frame profiler: frame times, per-tick and per-patch timers, forced enemy counts and a held time scale.
// Everything is gated on DevHarness.Enabled, so a normal session pays nothing for it. See docs/development.md.
public static class PerfMonitor
{
    public const int Capacity = 8192;

    // A dense disc rather than a wide ring: at 20 per ring and 2 units apart, 240 enemies still land within 26 units of the player.
    private const int EnemiesPerRing = 20;
    private const float FirstRingRadius = 4f;
    private const float RingSpacing = 2f;
    private const int ConsecutiveNullSpawnsToStop = 10;
    private const float SpawnLiftY = 2f;
    private const float StateLogIntervalSeconds = 2f;
    private const string DefaultTimeScaleVariable = "MEGABONK_PERF_DEFAULT_TIME_SCALE";

    private static readonly FrameBuffer _frames = new(Capacity);
    private static readonly Dictionary<PerfTick, double> _tickMs = new();
    private static readonly Dictionary<PerfTick, long> _tickCalls = new();
    private static readonly Dictionary<PerfTick, double> _tickMax = new();
    private static readonly Dictionary<PerfTick, bool> _tickEnabled = new();
    private static readonly Dictionary<string, ProbeSlot> _probes = new();

    // The names perf_probes.cs registers, so `toggle all` also covers a probe whose method never ran in this session.
    private static readonly string[] KnownProbes =
    {
        "EnemyManager.Update",
        "EnemyManager.FixedUpdate",
        "Enemy.MyFixedUpdate",
        "EnemyMovementRb.MyFixedUpdate",
        "AnimatedMesh.Update",
        "EnemyDissolve.Update",
        "MinimapUi.Update",
        "AlwaysManager.Update",
    };

    private static MelonLogger.Instance _logger;
    private static int _windowId;
    private static int _enemiesMin;
    private static int _enemiesMax;
    private static bool _timeScaleHeld;
    private static float _heldTimeScale;
    private static bool _vSyncOverridden;
    private static int _originalVSyncCount = 1;
    private static int _originalTargetFrameRate = -1;
    private static float _nextStateLog = float.MinValue;
    private static bool _wasPaused;
    private static bool _pausedKnown;
    private static bool _playerOverridden;

    private sealed class ProbeSlot
    {
        public double TotalMs;

        public double MaxMs;

        public long Calls;

        public bool Enabled = true;
    }

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    public static bool Active => DevHarness.Enabled;

    // Called from MegabonkLevelsMod.OnUpdate: one unscaled frame delta per frame plus the held time scale.
    public static void Tick()
    {
        if (!DevHarness.Enabled)
        {
            return;
        }

        if (_timeScaleHeld && !MyTime.paused)
        {
            MyTime.timeScale = _heldTimeScale;
        }

        var paused = MyTime.paused;
        if (!_pausedKnown || paused != _wasPaused)
        {
            _pausedKnown = true;
            _wasPaused = paused;
            Log($"pause: {(paused ? "on" : "off")} window={_windowId} frames={_frames.Count} enemies={LiveEnemyCount()}");
        }

        if (paused)
        {
            _frames.Pause();
        }
        else
        {
            _frames.Record(Time.unscaledDeltaTime * 1000f);
            var enemies = LiveEnemyCount();
            if (enemies < _enemiesMin)
            {
                _enemiesMin = enemies;
            }

            if (enemies > _enemiesMax)
            {
                _enemiesMax = enemies;
            }
        }

        if (Time.unscaledTime >= _nextStateLog)
        {
            _nextStateLog = Time.unscaledTime + StateLogIntervalSeconds;
            Log(
                $"state: window={_windowId} frames={_frames.Count} paused={_frames.PausedFrames} " +
                $"enemies={LiveEnemyCount()} timeScale={Number(MyTime.timeScale)} held={_timeScaleHeld}");
        }

        // Timed like the other ticks: each control's own rescan is part of what its arm costs, so it has to be visible.
        Timed(PerfTick.RenderCull, EnemyRenderCull.Apply);
        Timed(PerfTick.PhysicsFreeze, EnemyPhysicsFreeze.Apply);
        Timed(PerfTick.AnimationCull, EnemyAnimationCull.Apply);
    }

    // Wraps one mod tick so its own cost is attributable. The guard keeps a session without the harness free of timing calls.
    public static void Timed(PerfTick tick, Action body)
    {
        if (!DevHarness.Enabled)
        {
            body();
            return;
        }

        // The harness's own control ticks stay on whatever a toggle asks for, like the command channel: switching the
        // mod's work off must not silently strand an armed render A/B with enemies hidden and nothing rescanning them.
        if (!IsUngated(tick) && IsTickOff(tick))
        {
            return;
        }

        var startedAt = (double)Stopwatch.GetTimestamp();
        body();
        RecordTick(tick, ElapsedMs(startedAt));
    }

    public static JsonObject StartWindow()
    {
        _frames.Clear();
        _windowId++;        _enemiesMin = int.MaxValue;
        _enemiesMax = 0;
        _tickMs.Clear();
        _tickCalls.Clear();
        _tickMax.Clear();
        foreach (var slot in _probes.Values)
        {
            slot.TotalMs = 0d;
            slot.MaxMs = 0d;
            slot.Calls = 0;
        }

        PerfGc.ClearWindow();

        Log($"start: window={_windowId}, frame buffer and timers cleared");
        return new JsonObject { ["started"] = true, ["window"] = _windowId };
    }

    public static JsonObject Report()
    {
        var summary = _frames.Summarize();
        var modMs = 0d;
        foreach (var pair in _tickMs)
        {
            modMs += pair.Value;
        }

        var frames = Math.Max(1, summary.Frames);
        var enemiesLast = LiveEnemyCount();
        var root = new JsonObject
        {
            ["window"] = _windowId,
            ["frames"] = summary.Frames,
            ["pausedFrames"] = _frames.PausedFrames,
            ["meanMs"] = Number(summary.MeanMs),
            ["p50Ms"] = Number(summary.MedianMs),
            ["p90Ms"] = Number(summary.P90Ms),
            ["p99Ms"] = Number(summary.P99Ms),
            ["maxMs"] = Number(summary.MaxMs),
            ["minMs"] = Number(summary.MinMs),
            ["modMsPerFrame"] = Number(modMs / frames),
            ["enemiesLast"] = enemiesLast,
            ["enemiesMin"] = _frames.Count == 0 ? 0 : _enemiesMin,
            ["enemiesMax"] = _enemiesMax,
            ["playerHp"] = LivePlayerHp(),
            ["timeScale"] = Number(MyTime.timeScale),
            ["paused"] = MyTime.paused,
            ["vSyncCount"] = QualitySettings.vSyncCount,
            ["targetFrameRate"] = Application.targetFrameRate,
            ["renderCull"] = RenderCullNode(),
            ["physicsFreeze"] = PhysicsFreezeNode(),
            ["animationCull"] = AnimationCullNode(),
            ["enemyPositionSum"] = Number(EnemyRenderCull.EnemyPositionSum()),
            ["ticks"] = TicksNode(),
            ["probes"] = ProbesNode(),
            ["probeAttach"] = PerfProbes.AttachNode(),
        };

        PerfGc.AddTo(root, summary.Frames);

        Log(
            $"report: window={_windowId} frames={summary.Frames} mean={Number(summary.MeanMs)}ms p50={Number(summary.MedianMs)}ms " +
            $"p90={Number(summary.P90Ms)}ms p99={Number(summary.P99Ms)}ms max={Number(summary.MaxMs)}ms " +
            $"enemies={enemiesLast}..{_enemiesMax} mod={Number(modMs / frames)}ms/frame");
        return root;
    }

    public static JsonObject Status()
    {
        return new JsonObject
        {
            ["active"] = DevHarness.Enabled,
            ["window"] = _windowId,
            ["frames"] = _frames.Count,
            ["pausedFrames"] = _frames.PausedFrames,
            ["capacity"] = Capacity,
            ["enemiesLast"] = LiveEnemyCount(),
            ["playerHp"] = LivePlayerHp(),
            ["timeScale"] = Number(MyTime.timeScale),
            ["paused"] = MyTime.paused,
            ["heldTimeScale"] = _timeScaleHeld ? Number(_heldTimeScale) : null,
            ["defaultTimeScale"] = Number(DefaultTimeScale()),
            ["renderCull"] = RenderCullNode(),
            ["physicsFreeze"] = PhysicsFreezeNode(),
            ["animationCull"] = AnimationCullNode(),
            ["enemyPositionSum"] = Number(EnemyRenderCull.EnemyPositionSum()),
            ["ticks"] = TicksNode(),
            ["probes"] = ProbesNode(),
            ["probeAttach"] = PerfProbes.AttachNode(),
        };
    }

    // Clears the window, the timers and every toggle, and gives time scale back to the game. It never unpauses: freeze stays its own verb.
    public static JsonObject Reset()
    {
        _timeScaleHeld = false;
        _heldTimeScale = 0f;
        MyTime.timeScale = DefaultTimeScale();
        _tickMs.Clear();
        _tickCalls.Clear();
        _tickMax.Clear();
        _tickEnabled.Clear();
        foreach (var slot in _probes.Values)
        {
            slot.Enabled = true;
        }

        var wasCulled = EnemyRenderCull.Armed;
        if (wasCulled)
        {
            EnemyRenderCull.Set(true, _logger);
        }

        var wasFrozen = EnemyPhysicsFreeze.Armed;
        if (wasFrozen)
        {
            EnemyPhysicsFreeze.Set(true, _logger);
        }

        var wasAnimationCulled = EnemyAnimationCull.Armed;
        if (wasAnimationCulled)
        {
            EnemyAnimationCull.Set(true, _logger);
        }

        StartWindow();
        var restoredPlayer = _playerOverridden;
        if (_playerOverridden)
        {
            _playerOverridden = false;
            PlayerInvulnerability.Set(false, _logger);
        }

        Log(
            $"reset: timers cleared, timeScale={Number(MyTime.timeScale)}, all ticks and probes enabled, player grant restored={restoredPlayer}, " +
            $"render cull restored={wasCulled}, physics freeze restored={wasFrozen}, animation cull restored={wasAnimationCulled}");
        return new JsonObject
        {
            ["reset"] = true,
            ["timeScale"] = Number(MyTime.timeScale),
            ["playerGrantRestored"] = restoredPlayer,
            ["renderCullRestored"] = wasCulled,
            ["physicsFreezeRestored"] = wasFrozen,
            ["animationCullRestored"] = wasAnimationCulled,
        };
    }

    // Spawns `count` enemies in rings around the player at the kill floor's ground line, bounded by the game's own pool cap.
    public static JsonObject Spawn(int count)
    {
        var manager = EnemyManager.Instance;
        if (manager == null)
        {
            throw new InvalidOperationException("no EnemyManager in the scene, load a level first");
        }

        var data = LiveEnemyData(manager) ?? manager.testEnemy;
        if (data == null)
        {
            throw new InvalidOperationException("no EnemyData to spawn: no live enemy and EnemyManager.testEnemy is empty");
        }

        var player = MyPlayer.Instance;
        var origin = player != null ? player.transform.position : new Vector3(0f, SpawnLiftY, 0f);
        var before = manager.numEnemies;
        var spawned = 0;
        var points = PerfSpawnPlan.Ring(origin.x, origin.z, count, EnemiesPerRing, FirstRingRadius, RingSpacing);

        // forceSpawn bypasses the game's soft cap; an exhausted pool hands back null, so stop once it keeps doing that.
        var nulls = 0;
        for (var i = 0; i < points.Length && nulls < ConsecutiveNullSpawnsToStop; i++)
        {
            var enemy = manager.SpawnEnemy(data, new Vector3(points[i].X, origin.y + SpawnLiftY, points[i].Z), 1, true, EEnemyFlag.None, false, 1f);
            if (enemy == null)
            {
                nulls++;
                continue;
            }

            nulls = 0;
            spawned++;
        }

        Log($"spawn: requested={count} spawned={spawned} enemies={before}->{manager.numEnemies} around ({Number(origin.x)}, {Number(origin.y)}, {Number(origin.z)})");
        return new JsonObject
        {
            ["requested"] = count,
            ["spawned"] = spawned,
            ["enemiesBefore"] = before,
            ["enemies"] = manager.numEnemies,
            ["poolMax"] = manager.GetNumMaxEnemies(),
            ["centreX"] = Number(origin.x),
            ["centreZ"] = Number(origin.z),
        };
    }

    // Keeps the player alive through a measurement window: the harness's invulnerability grant (Mirror and Feathers
    // stacks absorb hits and revive) plus hit points above anything a swarm can chew through. A death screen pauses the
    // run, and a paused window is a useless sample.
    public static JsonObject SetPlayerHealth(int hp)
    {
        var health = CurrentPlayerHealth();
        if (health == null)
        {
            throw new InvalidOperationException("no PlayerHealth in the scene, load a level first");
        }

        PlayerInvulnerability.Set(true, _logger);
        _playerOverridden = true;
        var before = health.hp;
        health.maxHp = Math.Max(health.maxHp, hp);
        health.hp = hp;
        Log($"health: player hp {before}->{health.hp}, maxHp={health.maxHp}, invulnerable={PlayerInvulnerability.Active}");
        return new JsonObject
        {
            ["hpBefore"] = before,
            ["hp"] = health.hp,
            ["maxHp"] = health.maxHp,
            ["invulnerable"] = PlayerInvulnerability.Active,
        };
    }

    public static JsonObject SetTimeScale(float? value)
    {
        if (value.HasValue)
        {
            _timeScaleHeld = true;
            _heldTimeScale = value.Value;
            MyTime.timeScale = _heldTimeScale;
            Log($"timescale: held at {Number(_heldTimeScale)}");
            return new JsonObject { ["held"] = true, ["timeScale"] = Number(_heldTimeScale) };
        }

        _timeScaleHeld = false;
        _heldTimeScale = 0f;
        MyTime.timeScale = DefaultTimeScale();
        Log($"timescale: released to {Number(MyTime.timeScale)}");
        return new JsonObject { ["held"] = false, ["timeScale"] = Number(MyTime.timeScale) };
    }

    // Turns the vsync cap off so cost inside the 60 fps budget becomes visible; `on` restores what the game had when it was first overridden.
    public static JsonObject SetVSync(bool enabled)
    {
        if (!_vSyncOverridden && !enabled)
        {
            _originalVSyncCount = QualitySettings.vSyncCount;
            _originalTargetFrameRate = Application.targetFrameRate;
            _vSyncOverridden = true;
        }

        QualitySettings.vSyncCount = enabled ? _originalVSyncCount : 0;
        Application.targetFrameRate = enabled ? _originalTargetFrameRate : 0;
        Log(
            enabled
                ? $"vsync: restored to vSyncCount={_originalVSyncCount} targetFrameRate={_originalTargetFrameRate}"
                : "vsync: off, vSyncCount=0 targetFrameRate=0 (uncapped)");
        return new JsonObject
        {
            ["vsync"] = enabled,
            ["vSyncCount"] = QualitySettings.vSyncCount,
            ["targetFrameRate"] = Application.targetFrameRate,
        };
    }

    // The render-only control: enabled=false hides every enemy renderer (submission side) with AI, physics and animation running;
    // enabled=true restores them. It is the A/B against count_240, so it lives beside the vsync and health controls.
    public static JsonObject SetEnemyRenderers(bool enabled) => EnemyRenderCull.Set(enabled, _logger);

    // The physics-side control: enabled=false makes every Rigidbody under the live enemies kinematic, taking them out of the
    // solver with AI, renderers and animation running; enabled=true puts each body back on the value it had.
    public static JsonObject SetEnemyPhysics(bool enabled) => EnemyPhysicsFreeze.Set(enabled, _logger);

    // The animation-side control: enabled=false stops the enemies' AnimatedMesh/Animator updates with renderers and physics
    // running; enabled=true re-enables exactly the components it stopped.
    public static JsonObject SetEnemyAnimation(bool enabled) => EnemyAnimationCull.Set(enabled, _logger);

    public static JsonObject Toggle(string target, bool enabled)
    {
        if (string.Equals(target, "all", StringComparison.OrdinalIgnoreCase))
        {
            foreach (PerfTick entry in Enum.GetValues(typeof(PerfTick)))
            {
                if (IsUngated(entry) && !enabled)
                {
                    continue;
                }

                _tickEnabled[entry] = enabled;
            }

            foreach (var name in KnownProbes)
            {
                SlotFor(name).Enabled = enabled;
            }

            Log($"toggle: all {(enabled ? "on" : "off")}");
            return new JsonObject { ["target"] = "all", ["kind"] = "tick+probe", ["enabled"] = enabled };
        }

        if (TryParseTick(target, out var tick))
        {
            if (IsUngated(tick) && !enabled)
            {
                Log($"toggle: {tick} stays on, it is a harness control rather than mod work");
                return new JsonObject { ["target"] = target, ["enabled"] = true, ["ignored"] = true };
            }

            _tickEnabled[tick] = enabled;
            Log($"toggle: tick {tick} {(enabled ? "on" : "off")}");
            return new JsonObject { ["target"] = tick.ToString(), ["kind"] = "tick", ["enabled"] = enabled };
        }

        var slot = SlotFor(target);
        slot.Enabled = enabled;
        Log($"toggle: probe {target} {(enabled ? "on" : "off")}");
        return new JsonObject { ["target"] = target, ["kind"] = "probe", ["enabled"] = enabled };
    }

    // One-shot component census: scene = components on active game objects, live = also enabled and active in hierarchy,
    // any = everything Resources sees, prefabs and inactive included. Settled that EnemyHpBar and VisualizeTargeting never
    // spawn (prefab-only / absent), so probes on their Update would time nothing; a game update that changes this shows up here.
    public static JsonObject Census()
    {
        var rows = new List<(string, int, int, int)>
        {
            CensusRow("Enemy", CountBy<Enemy>()),
            CensusRow("EnemyHpBar", CountBy<EnemyHpBar>()),
            CensusRow("VisualizeTargeting", CountBy<VisualizeTargeting>()),
            CensusRow("AnimatedMesh", CountBy<AnimatedMesh>()),
        };

        var line = "census:";
        foreach (var (name, scene, live, any) in rows)
        {
            line += $" {name}={scene}/{live}/{any}";
        }

        Log(line);
        return new JsonObject { ["census"] = PerfProbePlan.CensusNode(rows) };
    }

    private static (string, int, int, int) CensusRow(string name, (int Scene, int Live, int Any) counts)
        => (name, counts.Scene, counts.Live, counts.Any);

    private static (int Scene, int Live, int Any) CountBy<T>() where T : Behaviour
    {
        var scene = UnityEngine.Object.FindObjectsOfType<T>();
        var all = Resources.FindObjectsOfTypeAll<T>();
        var live = 0;
        if (all != null)
        {
            foreach (var behaviour in all)
            {
                if (behaviour.enabled && behaviour.gameObject.activeInHierarchy)
                {
                    live++;
                }
            }
        }

        return (scene?.Length ?? 0, live, all?.Length ?? 0);
    }

    // Prefix half of a patch probe; a zero start means the postfix has nothing to time.
    public static void ProbeEnter(string name, out double startedAt)
    {
        startedAt = 0d;
        if (!DevHarness.Enabled)
        {
            return;
        }

        var slot = SlotFor(name);
        if (!slot.Enabled)
        {
            return;
        }

        slot.Calls++;
        startedAt = (double)Stopwatch.GetTimestamp();
    }

    public static void ProbeExit(string name, double startedAt)
    {
        if (startedAt == 0d || !DevHarness.Enabled)
        {
            return;
        }

        var elapsedMs = ElapsedMs(startedAt);
        var slot = SlotFor(name);
        slot.TotalMs += elapsedMs;
        if (elapsedMs > slot.MaxMs)
        {
            slot.MaxMs = elapsedMs;
        }
    }

    // Stopwatch, not Time: every Unity Time value is a per-frame snapshot, so a prefix/postfix pair would always read zero.
    private static double ElapsedMs(double startedAt) => ((double)Stopwatch.GetTimestamp() - startedAt) * 1000d / Stopwatch.Frequency;

    private static void RecordTick(PerfTick tick, double elapsedMs)
    {
        _tickMs[tick] = _tickMs.TryGetValue(tick, out var total) ? total + elapsedMs : elapsedMs;
        _tickCalls[tick] = _tickCalls.TryGetValue(tick, out var calls) ? calls + 1 : 1;
        _tickMax[tick] = _tickMax.TryGetValue(tick, out var max) ? Math.Max(max, elapsedMs) : elapsedMs;
    }

    private static bool IsTickOff(PerfTick tick) => _tickEnabled.TryGetValue(tick, out var enabled) && !enabled;

    // Harness controls rather than mod work: the command channel and the three live-enemy controls keep running whatever a
    // toggle asks for, so a mod-off control cannot strand an armed A/B with enemies hidden, frozen or unanimated.
    private static bool IsUngated(PerfTick tick) => tick is PerfTick.DevHarnessPoll or PerfTick.RenderCull or PerfTick.PhysicsFreeze or PerfTick.AnimationCull;

    private static ProbeSlot SlotFor(string name)
    {
        if (!_probes.TryGetValue(name, out var slot))
        {
            slot = new ProbeSlot();
            _probes[name] = slot;
        }

        return slot;
    }

    private static bool TryParseTick(string target, out PerfTick tick)
    {
        tick = default;
        if (string.IsNullOrEmpty(target) || char.IsDigit(target[0]))
        {
            return false;
        }

        return Enum.TryParse(target, out tick);
    }

    private static JsonObject RenderCullNode() => new()
    {
        ["armed"] = EnemyRenderCull.Armed,
        ["renderersOff"] = EnemyRenderCull.DisabledCount,
        ["suppresses"] = new JsonArray { "enemy draw submission", "those renderers' culling and shadow-pass work" },
    };

    private static JsonObject PhysicsFreezeNode() => new()
    {
        ["armed"] = EnemyPhysicsFreeze.Armed,
        ["rigidbodiesKinematic"] = EnemyPhysicsFreeze.FrozenCount,
        ["rigidbodiesFound"] = EnemyPhysicsFreeze.BodiesFound,
        ["enemies"] = LiveEnemyCount(),
        ["suppresses"] = SuppressesNode(EnemyPhysicsFreezePlan.Suppresses),
        ["fidelity"] = EnemyPhysicsFreezePlan.FidelityNote(),
    };

    private static JsonObject AnimationCullNode() => new()
    {
        ["armed"] = EnemyAnimationCull.Armed,
        ["behavioursOff"] = EnemyAnimationCull.StoppedCount,
        ["componentsFound"] = EnemyAnimationCull.ComponentsFound,
        ["byType"] = EnemyAnimationCull.StoppedByTypeNode(),
        ["enemies"] = LiveEnemyCount(),
        ["suppresses"] = SuppressesNode(EnemyAnimationCullPlan.Suppresses),
        ["fidelity"] = EnemyAnimationCullPlan.FidelityNote(),
    };

    private static JsonArray SuppressesNode(IReadOnlyList<string> lines)
    {
        var node = new JsonArray();
        foreach (var line in lines)
        {
            node.Add(line);
        }

        return node;
    }

    private static JsonArray TicksNode()
    {
        var ticks = new JsonArray();
        foreach (PerfTick tick in Enum.GetValues(typeof(PerfTick)))
        {
            _tickMs.TryGetValue(tick, out var total);
            _tickCalls.TryGetValue(tick, out var calls);
            _tickMax.TryGetValue(tick, out var max);
            ticks.Add(new JsonObject
            {
                ["name"] = tick.ToString(),
                ["ms"] = Number(total),
                ["calls"] = calls,
                ["maxMs"] = Number(max),
                ["enabled"] = !IsTickOff(tick),
            });
        }

        return ticks;
    }

    private static JsonArray ProbesNode()
    {
        var probes = new JsonArray();
        foreach (var pair in _probes)
        {
            probes.Add(new JsonObject
            {
                ["name"] = pair.Key,
                ["ms"] = Number(pair.Value.TotalMs),
                ["calls"] = pair.Value.Calls,
                ["maxMs"] = Number(pair.Value.MaxMs),
                ["enabled"] = pair.Value.Enabled,
            });
        }

        return probes;
    }

    private static EnemyData LiveEnemyData(EnemyManager manager)
    {
        var enemies = manager.enemies;
        if (enemies == null)
        {
            return null;
        }

        foreach (var enemy in enemies.Values)
        {
            if (enemy != null && enemy.enemyData != null)
            {
                return enemy.enemyData;
            }
        }

        return null;
    }

    private static int LiveEnemyCount()
    {
        var manager = EnemyManager.Instance;
        return manager == null ? 0 : manager.numEnemies;
    }

    private static PlayerHealth CurrentPlayerHealth()
    {
        var player = MyPlayer.Instance;
        return player == null ? null : player.inventory?.playerHealth;
    }

    // Live hit points, so a window's JSON says whether the player could have died inside it; 0 when there is no player.
    private static int LivePlayerHp()
    {
        var health = CurrentPlayerHealth();
        return health == null ? 0 : health.hp;
    }

    // The value a released time scale goes back to; 1 is the shipped default and the variable covers a mod that changes it.
    private static float DefaultTimeScale()
    {
        var raw = Environment.GetEnvironmentVariable(DefaultTimeScaleVariable);
        return float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) && PerfLimits.ValidTimeScale(value)
            ? value
            : 1f;
    }

    private static void Log(string message)
    {
        _logger?.Msg($"Perf: {message}");
    }

    private static double Number(double value) => Math.Round(value, 3);

    private static double Number(float value) => Math.Round(value, 3);
}
