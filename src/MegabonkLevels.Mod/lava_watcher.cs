using System.Collections.Generic;
using Assets.Scripts.Actors.Player;
using UnityEngine;

namespace MegabonkLevels;

// Hurts a player who stands on one of the level's lava zones: every zone interval a standing player takes the zone's damage. The lava look comes from a ground zone using the Lava material.
public static class LavaWatcher
{
    private const string DamageSource = "Lava";

    private static ModLogger _logger;
    private static readonly Dictionary<int, float> s_nextHurt = new();
    private static bool _loggedFirstHurt;

    public static void Install(ModLogger logger) => _logger = logger;

    public static void Tick()
    {
        if (!CustomLevelState.IsActive || EditorMode.Active || Time.timeScale <= 0f) return;
        var zones = LiveEditPatch.CurrentSettings.LavaZones;
        if (zones == null || zones.Count == 0) return;
        var player = MyPlayer.Instance;
        var tileGen = LiveEditPatch.TileGen;
        var health = player?.inventory?.playerHealth;
        if (health == null || tileGen?.proceduralTiles == null) return;

        var at = player.transform.position;
        var width = tileGen.currentMapParameters.scaledTileWidth;
        for (var i = 0; i < zones.Count; i++)
        {
            var zone = zones[i];
            if (!TryBounds(tileGen, zone, width, out var minX, out var maxX, out var minZ, out var maxZ, out var surfaceY)) continue;
            if (!LavaZones.Contains(minX, maxX, minZ, maxZ, surfaceY, at.x, at.y, at.z)) continue;
            if (Time.time < (s_nextHurt.TryGetValue(i, out var next) ? next : 0f)) continue;
            s_nextHurt[i] = Time.time + zone.Interval;
            if (!health.CanTakeDamage()) continue;
            health.DamagePlayerExternal(zone.Damage, 0f, Vector3.zero, false, DamageSource, 0, 0, null);
            if (!_loggedFirstHurt)
            {
                _loggedFirstHurt = true;
                _logger?.Msg($"Lava: zone {i} hurt the player for {zone.Damage} at ({at.x:0.#}, {at.y:0.#}, {at.z:0.#})");
            }
        }
    }

    // The world rectangle of the zone's cells from the live tiles, and the surface height of its first cell.
    private static bool TryBounds(ProceduralTileGeneration tileGen, LavaZone zone, float width, out float minX, out float maxX, out float minZ, out float maxZ, out float surfaceY)
    {
        minX = maxX = minZ = maxZ = surfaceY = 0f;
        var columns = tileGen.proceduralTiles;
        if (zone.MaxX >= columns.Length || zone.MaxZ >= columns[0].Length) return false;
        var first = columns[zone.MinX][zone.MinZ];
        var last = columns[zone.MaxX][zone.MaxZ];
        if (first == null || last == null) return false;
        var a = first.transform.position;
        var b = last.transform.position;
        minX = a.x - width / 2f;
        minZ = a.z - width / 2f;
        maxX = b.x + width / 2f;
        maxZ = b.z + width / 2f;
        surfaceY = a.y;
        return true;
    }
}
