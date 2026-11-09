using System.Collections.Generic;
using Assets.Scripts.Actors.Player;
using Assets.Scripts.Utility;
using UnityEngine;

namespace MegabonkLevels;

// The generous half of the grind gate. On a level that asks for the slide button, holding it catches a rail within reach
// rather than leaving the start to the game's own catch, which needs the player's collider to touch the rail's. Sibling of
// GrindGatePatch, which does the refusing, and of RailHandoffPatch, which finds a rail the same way to chain onto.
public static class GrindAssistWatcher
{
    // A catch is one event per grind, but the search runs every frame, so the line is kept to this rate.
    private const int LogIntervalFrames = 60;

    private static ModLogger _logger;
    private static int _lastCatchLogFrame = -LogIntervalFrames;

    public static void Install(ModLogger logger)
    {
        _logger = logger;
    }

    public static void Tick()
    {
        // A frozen run (the editor, or the harness holding the game still) has no grinding to help with.
        if (MyTime.paused)
        {
            return;
        }

        var me = MyPlayer.Instance;
        var player = me?.playerMovement;
        if (player == null || me.inventory.playerHealth.hp <= 0)
        {
            return;
        }

        if (!GrindAssist.Assists(CustomLevelState.IsActive, LiveEditPatch.GrindRequiresSlide, GrindInput.IsSlideHeld(), player.IsGrinding()))
        {
            return;
        }

        CatchNearestRail(player);
    }

    private static void CatchNearestRail(PlayerMovement player)
    {
        var body = player.rb.position;
        var origin = new Vector3(body.x, player.playerCollider.bounds.min.y, body.z);
        var colliders = Physics.OverlapSphere(origin, GrindAssist.CatchRadius, ~0, QueryTriggerInteraction.Collide);
        var rails = new List<Rail>();
        var distances = new List<float>();
        var onCooldown = new List<bool>();
        foreach (var collider in colliders)
        {
            var rail = collider.GetComponent<Rail>();
            if (rail == null)
            {
                continue;
            }

            var nearest = collider.ClosestPoint(origin);
            if (!GrindAssist.WithinBand(nearest.y, origin.y))
            {
                continue;
            }

            rails.Add(rail);
            distances.Add(Vector3.Distance(nearest, origin));
            onCooldown.Add(rail.IsOnCooldown());
        }

        var pick = RailHandoff.PickNearest(distances, onCooldown, GrindAssist.CatchRadius);
        if (pick < 0)
        {
            return;
        }

        player.StartRail(rails[pick]);
        var direction = RailHandoff.DirectionForFreshCatch(player.progress);
        if (direction.HasValue)
        {
            player.railDirectionMultiplier = direction.Value;
        }

        LogCatch(player, rails[pick], distances[pick], direction);
    }

    private static void LogCatch(PlayerMovement player, Rail rail, float distance, float? direction)
    {
        if (Time.frameCount - _lastCatchLogFrame < LogIntervalFrames)
        {
            return;
        }

        _lastCatchLogFrame = Time.frameCount;
        var body = player.rb.position;
        var bar = rail.transform.position;
        var started = direction.HasValue ? $" running direction {direction.Value:F1}" : string.Empty;
        _logger?.Msg($"GrindAssist: caught the rail at ({bar.x:F1}, {bar.y:F1}, {bar.z:F1}) from {distance:F2} units at ({body.x:F1}, {body.y:F1}, {body.z:F1}), progress {player.progress:F3}{started}.");
    }
}
