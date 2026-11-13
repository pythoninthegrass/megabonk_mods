using System;
using System.Collections.Generic;
using System.IO;
using Assets.Scripts.Actors.Player;
using Assets.Scripts.Inventory__Items__Pickups.AbilitiesPassive;
using Assets.Scripts.Inventory__Items__Pickups.Stats;
using Assets.Scripts.Inventory__Items__Pickups.Weapons.Attacks;
using Assets.Scripts.Menu.Shop;
using Assets.Scripts.Saves___Serialization.Progression.Achievements;
using Assets.Scripts.Saves___Serialization.Progression.Unlocks;
using Assets.Scripts.Saves___Serialization.SaveFiles.Configs;
using HarmonyLib;
using UnityEngine;

namespace MegabonkLevels;

// Adds Squeaker to the game's character and skin tables when the squeaker pack is installed; see docs/characters.md.
public static class SqueakerRegistrationPatch
{
    private const string IconFileName = "squeaker_icon.png";

    private static GameObject _hiddenRoot;

    private static ModLogger Log => ModLogger.Default;

    [HarmonyPatch(typeof(DataManager), nameof(DataManager.Load), new Type[0])]
    private static class LoadPrefix
    {
        private static void Prefix(DataManager __instance)
        {
            try
            {
                Register(__instance);
            }
            catch (Exception e)
            {
                Log?.Warning($"Squeaker: registration failed, the character is not added: {e}");
            }
        }
    }

    [HarmonyPatch(typeof(Preferences), nameof(Preferences.Init))]
    private static class PreferencesInitPostfix
    {
        private static void Postfix(Preferences __instance)
        {
            var seeded = new List<int>();
            foreach (var key in __instance.characterSkins.Keys)
            {
                seeded.Add((int)key);
            }

            if (RegisteredCharacter != null && ModCharacterRegistration.NeedsSkinSeed(seeded, SqueakerCharacter.Id))
            {
                __instance.characterSkins[(ECharacter)SqueakerCharacter.Id] = 0;
            }
        }
    }

    private static CharacterData RegisteredCharacter;

    // Display text for the runtime-built assets, keyed by instance id; the cloned LocalizedStrings would otherwise show Calcium's text.
    private static readonly Dictionary<int, (string Name, string Description)> Texts = new();

    // The unlock checks the character grid and shop use; the mod's character has no save entry, so it counts as owned.
    [HarmonyPatch(typeof(MyAchievements), nameof(MyAchievements.IsPurchased))]
    private static class IsPurchasedPostfix
    {
        private static void Postfix(UnlockableBase unlockable, ref bool __result) => __result |= IsRegistered(unlockable);
    }

    [HarmonyPatch(typeof(MyAchievements), nameof(MyAchievements.IsAvailable))]
    private static class IsAvailablePostfix
    {
        private static void Postfix(UnlockableBase unlockable, ref bool __result) => __result |= IsRegistered(unlockable);
    }

    [HarmonyPatch(typeof(UnlockableBase), nameof(UnlockableBase.GetName))]
    private static class UnlockableNamePostfix
    {
        private static void Postfix(UnlockableBase __instance, ref string __result)
        {
            if (Texts.TryGetValue(__instance.GetInstanceID(), out var text))
            {
                __result = text.Name;
            }
        }
    }

    [HarmonyPatch(typeof(UnlockableBase), nameof(UnlockableBase.GetDescription))]
    private static class UnlockableDescriptionPostfix
    {
        private static void Postfix(UnlockableBase __instance, ref string __result)
        {
            if (Texts.TryGetValue(__instance.GetInstanceID(), out var text))
            {
                __result = text.Description;
            }
        }
    }

    [HarmonyPatch(typeof(PassiveData), nameof(PassiveData.GetName))]
    private static class PassiveNamePostfix
    {
        private static void Postfix(PassiveData __instance, ref string __result)
        {
            if (Texts.TryGetValue(__instance.GetInstanceID(), out var text))
            {
                __result = text.Name;
            }
        }
    }

    [HarmonyPatch(typeof(PassiveData), nameof(PassiveData.GetDescription))]
    private static class PassiveDescriptionPostfix
    {
        private static void Postfix(PassiveData __instance, ref string __result)
        {
            if (Texts.TryGetValue(__instance.GetInstanceID(), out var text))
            {
                __result = text.Description;
            }
        }
    }

    private static bool IsRegistered(UnlockableBase unlockable) =>
        RegisteredCharacter != null && unlockable != null && unlockable.GetInstanceID() == RegisteredCharacter.GetInstanceID();

    private static void Register(DataManager data)
    {
        var characters = data.unsortedCharacterData;
        var ids = new List<int>();
        CharacterData calcium = null;
        foreach (var entry in characters)
        {
            ids.Add((int)entry.eCharacter);
            if ((int)entry.eCharacter == CharacterOverride.CalciumId)
            {
                calcium = entry;
            }
        }

        if (!ModCharacterRegistration.ShouldAppend(ids, SqueakerCharacter.Id) || calcium == null)
        {
            return;
        }

        var model = PackPrefabs.TryResolve(CatalogId.Parse(SqueakerCharacter.ModelCatalogId));
        var cookie = PackPrefabs.TryResolve(CatalogId.Parse(SqueakerCharacter.CookieCatalogId));
        if (model == null || cookie == null)
        {
            Log?.Msg("Squeaker: the squeaker pack is not installed, the character is not added.");
            return;
        }

        var skin = BuildSkin(data, model);
        if (skin == null)
        {
            return;
        }

        var character = Pin(UnityEngine.Object.Instantiate(calcium));
        character.name = SqueakerCharacter.DisplayName;
        character.eCharacter = (ECharacter)SqueakerCharacter.Id;
        character.prefab = model;
        character.icon = LoadIcon() ?? character.icon;
        character.colliderHeight = SqueakerCharacter.ColliderHeight;
        character.colliderWidth = SqueakerCharacter.ColliderWidth;
        character.statModifiers = BuildModifiers();
        character.weapon = BuildCookieWeapon(calcium.weapon, cookie);
        character.passive = BuildTinyTarget(calcium.passive);
        character.achievementRequirement = null;
        character.numQuestsRequiredForVisibilityInCharacterSelection = 0;
        character.sortingPriority = calcium.sortingPriority;
        character.isEnabled = true;

        Texts[character.GetInstanceID()] = (SqueakerCharacter.DisplayName, SqueakerCharacter.PassiveDescription);
        characters.Add(character);
        data.unsortedSkins.Add(skin);
        RegisteredCharacter = character;
        Log?.Msg($"Squeaker: registered as character {SqueakerCharacter.Id} with weapon '{character.weapon.name}' (cookie icon rendered: {_cookieIcon != null}).");
    }

    private static Il2CppSystem.Collections.Generic.List<StatModifier> BuildModifiers()
    {
        var list = new Il2CppSystem.Collections.Generic.List<StatModifier>();
        foreach (var row in SqueakerCharacter.TinyTargetModifiers)
        {
            list.Add(new StatModifier { stat = (EStat)row.Stat, modifyType = (EStatModifyType)row.ModifyType, modification = row.Modification });
        }

        return list;
    }

    // Clones Calcium's Bone weapon for its text and icon; the game builds the live weapon from Bone's own data, so the projectile swap happens on the stock attack prefab in SwapProjectile.
    private static WeaponData BuildCookieWeapon(WeaponData bone, GameObject cookie)
    {
        var weapon = Pin(UnityEngine.Object.Instantiate(bone));
        weapon.name = "StaleCookie";
        _boneData = bone;
        _boneIcon = bone.icon;
        _cookieIcon = PrefabThumbnails.Render(cookie);
        if (_cookieIcon != null)
        {
            Pin(_cookieIcon);
            weapon.icon = _cookieIcon;
        }

        _boneAttack = bone.attack.GetComponent<WeaponAttack>();
        _boneProjectile = _boneAttack.prefabProjectile;
        _cookieProjectile = CookieProjectile(_boneProjectile, cookie);
        Texts[weapon.GetInstanceID()] = (SqueakerCharacter.WeaponName, SqueakerCharacter.WeaponDescription);
        return weapon;
    }

    private static WeaponData _boneData;
    private static Texture _boneIcon;
    private static Texture2D _cookieIcon;
    private static WeaponAttack _boneAttack;
    private static GameObject _boneProjectile;
    private static GameObject _cookieProjectile;

    // Bone's attack prefab and data are shared with every Bone owner, so a Squeaker run points them at the cookie and any other run points them back.
    [HarmonyPatch(typeof(MyPlayer), nameof(MyPlayer.StartPlayer))]
    private static class StartPlayerPrefix
    {
        private static void Prefix(ECharacter character) => SetCookieIdentity(SqueakerCharacter.UsesCookieProjectile((int)character));
    }

    [HarmonyPatch(typeof(MyPlayer), "OnDestroy")]
    private static class PlayerDestroyPostfix
    {
        private static void Postfix() => SetCookieIdentity(false);
    }

    private static void SetCookieIdentity(bool cookie)
    {
        if (_boneAttack == null || _cookieProjectile == null || _boneData == null)
        {
            return;
        }

        _boneAttack.prefabProjectile = cookie ? _cookieProjectile : _boneProjectile;
        _boneData.icon = cookie && _cookieIcon != null ? _cookieIcon : _boneIcon;
        if (cookie)
        {
            Texts[_boneData.GetInstanceID()] = (SqueakerCharacter.WeaponName, SqueakerCharacter.WeaponDescription);
        }
        else
        {
            Texts.Remove(_boneData.GetInstanceID());
        }
    }

    // The Bone projectile keeps its components and collider; its renderers are switched off and the cookie model rides along as a child.
    private static GameObject CookieProjectile(GameObject boneProjectile, GameObject cookie)
    {
        var projectile = HiddenClone(boneProjectile, "StaleCookieProjectile");
        foreach (var renderer in projectile.GetComponentsInChildren<Renderer>(true))
        {
            renderer.enabled = false;
        }

        var visual = UnityEngine.Object.Instantiate(cookie, projectile.transform);
        visual.name = "StaleCookieVisual";
        visual.transform.localPosition = Vector3.zero;
        visual.transform.localRotation = Quaternion.identity;
        return projectile;
    }

    // The passive carries no behaviour: EPassive.None, with the Tiny Target numbers living in the character's stat modifiers.
    private static PassiveData BuildTinyTarget(PassiveData template)
    {
        var passive = Pin(UnityEngine.Object.Instantiate(template));
        passive.name = SqueakerCharacter.PassiveName;
        passive.ePassive = EPassive.None;
        Texts[passive.GetInstanceID()] = (SqueakerCharacter.PassiveName, SqueakerCharacter.PassiveDescription);
        return passive;
    }

    private static SkinData BuildSkin(DataManager data, GameObject model)
    {
        SkinData template = null;
        foreach (var skin in data.unsortedSkins)
        {
            if ((int)skin.character == CharacterOverride.CalciumId)
            {
                template = skin;
                break;
            }
        }

        var renderer = model.GetComponentInChildren<SkinnedMeshRenderer>(true);
        if (template == null || renderer == null)
        {
            Log?.Warning("Squeaker: no skin template or no SkinnedMeshRenderer on the model, the character is not added.");
            return null;
        }

        var skinData = Pin(UnityEngine.Object.Instantiate(template));
        skinData.name = SqueakerCharacter.DisplayName;
        skinData.character = (ECharacter)SqueakerCharacter.Id;
        skinData.materials = renderer.sharedMaterials;
        return skinData;
    }

    private static Texture LoadIcon()
    {
        var path = Path.Combine(ModPaths.GameRootDirectory, "UserData", "LevelPacks", "squeaker", IconFileName);
        if (!File.Exists(path))
        {
            return null;
        }

        var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point };
        if (!NativeImageLoader.LoadImage(texture, File.ReadAllBytes(path)))
        {
            return null;
        }

        return Pin(texture);
    }

    private static GameObject HiddenClone(GameObject source, string name)
    {
        if (_hiddenRoot == null)
        {
            _hiddenRoot = new GameObject("MegabonkLevels.SqueakerAssets");
            _hiddenRoot.SetActive(false);
            UnityEngine.Object.DontDestroyOnLoad(_hiddenRoot);
        }

        var clone = UnityEngine.Object.Instantiate(source, _hiddenRoot.transform);
        clone.name = name;
        return clone;
    }

    // The game's unused-asset unload would otherwise free the runtime-built objects.
    private static T Pin<T>(T asset) where T : UnityEngine.Object
    {
        asset.hideFlags |= HideFlags.DontUnloadUnusedAsset;
        return asset;
    }
}
