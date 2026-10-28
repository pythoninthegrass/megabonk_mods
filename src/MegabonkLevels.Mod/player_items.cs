using System;
using System.Linq;
using System.Text.Json.Nodes;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Inventory__Items__Pickups;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Items;

namespace MegabonkLevels;

// Reads and sets the stack count of a player item; RemoveItem drops one stack per call, so lowering an amount repeats it.
public static class PlayerItems
{
    public static JsonObject Apply(ItemArgs args)
    {
        var inventory = Inventory() ?? throw new InvalidOperationException("no player: start a run first");
        var item = Resolve(args.Name);
        var before = inventory.GetAmount(item);
        if (args.Amount is { } amount)
        {
            SetAmount(inventory, item, amount);
        }

        return new JsonObject
        {
            ["item"] = args.Name,
            ["before"] = before,
            ["after"] = inventory.GetAmount(item),
        };
    }

    public static void SetAmount(ItemInventory inventory, EItem item, int amount)
    {
        var current = inventory.GetAmount(item);
        if (amount > current)
        {
            inventory.AddItem(item, amount - current);
            return;
        }

        for (var i = current; i > amount; i--)
        {
            inventory.RemoveItem(item, false);
        }
    }

    public static ItemInventory Inventory() => MyPlayer.Instance?.inventory?.itemInventory;

    private static EItem Resolve(string name)
    {
        if (!Enum.GetNames(typeof(EItem)).Contains(name))
        {
            throw new ArgumentException($"unknown item '{name}'; names are case-sensitive EItem members");
        }

        return (EItem)Enum.Parse(typeof(EItem), name);
    }
}
