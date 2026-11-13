# Characters

How the game defines, lists, spawns and persists playable characters, read from the Il2Cpp dump and Ghidra decompiles of `GameAssembly.dll` (see [Using Ghidra through REA](development.md#using-ghidra-through-rea)). RVAs are offsets from the image base; add `0x180000000` for the Ghidra address. Field offsets are the ones `dump.cs` prints beside each field. Everything here is read from static code unless it is listed under [Not verified](#not-verified).

The mod itself only restricts, reorders and selects the stock characters (see "Character selection" in [development](development.md)). Nothing in it adds a character, so this page is the groundwork for doing that.

## The character is data, keyed by an enum

`ECharacter` runs from `Fox = 0` to `Roberto = 20`, with `Calcium = 1` and `TonyMcZoom = 13`. A character is a `CharacterData` ScriptableObject (`UnlockableBase` subclass). The fields that matter:

| Field | Offset | Used for |
| --- | --- | --- |
| `isEnabled` (from `UnlockableBase`) | `0x18` | `DataManager.Load` skips entries where this is false |
| `sortingPriority` (from `UnlockableBase`) | `0x2C` | Ordering in the grid |
| `eCharacter` | `0x50` | The dictionary key everywhere else |
| `icon` | `0x58` | Character select tile |
| `statModifiers` | `0x60` | Base stats for the character (the fall-damage reduction Tony has lives here) |
| `prefab` | `0x68` | The model, instantiated for the run (see [Prefab requirements](#prefab-requirements)) |
| `weapon` | `0x80` | The `WeaponData` the run starts with |
| `passive` | `0x88` | The `PassiveData` the run starts with |
| `colliderHeight`, `colliderWidth` | `0x90`, `0x94` | The player capsule |
| `achievementRequirement` | `0xB0` | Unlock gate; null means no achievement gate |
| `numQuestsRequiredForVisibilityInCharacterSelection` | `0xB8` | Quest count needed before the tile shows |
| `meshDefault`, `meshLow`, `meshLowest` | `0xC0`, `0xC8`, `0xD0` | Mesh levels of detail |

## How the list is built

`DataManager.Load` (`0x4F96D0`, a unique RVA) fills the runtime tables once at startup from the serialized lists on `DataManager`.

- For each entry of `unsortedCharacterData` (`0x30`) with `isEnabled` set, it inserts the entry into `characterData` (`0x98`, a `Dictionary<ECharacter, CharacterData>`) keyed by `eCharacter`, then calls `CharacterData.Init` (`0x3817E0`).
- For each entry of `unsortedSkins` (`0x70`) it appends the `SkinData` to `skinData` (`0xC8`, a `Dictionary<ECharacter, List<SkinData>>`) under the `SkinData.character` key (`0x60`), creating the list the first time a key appears.
- It ends by invoking the static `DataManager.A_DataLoaded` action.

`CharacterData.Init` builds `categoryRatios` (`0xA0`) from `StatCategoryRatios` (`0xA8`) and, when `passive` is set and the passive's `dummyPassive` (`0x38`) is null, instantiates the passive ability and stores it there.

Lookups are bare dictionary reads that throw when the key is missing:

| Method | RVA | Behaviour |
| --- | --- | --- |
| `DataManager.GetCharacterData` | `0x4F9030` | `characterData[key]` |
| `DataManager.GetSkins` | `0x4F9580` | `skinData[key]`; throws for a character with no `SkinData` |
| `DataManager.GetSkin` | `0x4F9450` | The saved index into that list, or index 0 when out of range |
| `CharacterData.IsBlackedOutInCharacterSelectionScreen` | `0x3819E0` | Not blacked out when the achievement is complete; with a null requirement it falls to a comparison of a progress count against `numQuestsRequiredForVisibilityInCharacterSelection` |

A character therefore needs both a `CharacterData` and at least one `SkinData` naming it. `GetSkin` falls back to index 0, so one default skin is enough.

## Character select

`CharacterMenu.TryInit` (`0x54A8E0`) builds the grid from `unsortedCharacterData`, not from the enum. It instantiates one `MyButtonCharacter` per entry, calls `DataManager.GetCharacterData` for each and `MyButtonCharacter.SetCharacter` (`0x552190`), then fills the rest of the grid with empty buttons up to a static slot count. It marks the button whose `eCharacter` equals `Preferences.selectedCharacter` as selected.

`MyButtonCharacter.SetCharacter` reads the name, icon and unlock state from the `CharacterData` and calls `ProgressionSaveFile.GetCharacterProgression` (`0x40FCF0`). `OnSelectCharacter` is `0x54A290` and `OnConfirmCharacter` is `0x549C90`; confirming writes the character into `Preferences.selectedCharacter`.

## Starting a run

`MyPlayer.StartPlayer(ECharacter, Vector3)` (`0x4B6A90`) does the following:

1. `DataManager.GetCharacterData(character)`.
2. Creates the singleton `PlayerInventory` from the `CharacterData` (accessor `0x4217A0`, constructor `0x4E0800`). The constructor stores the `CharacterData` (`0x18`), builds the stat and weapon managers, instantiates the passive from `CharacterData.passive`, and calls `WeaponInventory.AddWeapon(CharacterData.weapon, null)` unless the inventory is being restored.
3. `PlayerRenderer.SetCharacter` (`0x3474F0`), which instantiates the model (below).
4. `MyPlayer.RefreshSize` (`0x4B62F0`), which sets the player capsule's height to `colliderHeight` and radius to `colliderWidth`, each multiplied by the size multiplier, and repositions the renderer and camera anchors from those values.

So the collider size is data (`colliderHeight` and `colliderWidth`), and the starting weapon and passive are whatever `CharacterData.weapon` and `CharacterData.passive` point at.

## Prefab requirements

`PlayerRenderer.SetCharacter` instantiates `CharacterData.prefab` as a child of the player renderer and returns without a model when the field is null. It then reads from the instance:

- An `Animator` (stored at renderer `0x28`) and a `SkinnedMeshRenderer` (`0x40`), both found with component lookups on the instance.
- Child transforms named exactly `hips` and `torso` (lowercase, found by name among the instance's transforms; the names come from the game's string literals), stored at renderer `0x60` and `0x68`. They drive the look rotation and movement tilt.
- Skin materials. `SetSkin` (`0x348790`) applies `SkinData.materials` (`0x58`) for the skin chosen in `Preferences.characterSkins`, so the prefab's own materials are replaced.

The renderer also expects an `Outline` component and the game's toon shaders on the materials. Bundle materials are remapped by the mod's pack loader (see [AssetBundle authoring](asset-bundles.md)). The `PlayerRenderer` fields at `0x28`, `0x40`, `0x60` and `0x68` are filled from the instance, so the prefab does not need to carry a `PlayerRenderer`.

## Weapon wiring

`WeaponData` (`dump.cs` 350325) holds the weapon's numbers (`damage`, `projectiles`, `projectileSpeed`, `eWeapon` and so on) and `attack` (`0xD0`), a prefab with a `WeaponAttack` component. `WeaponAttack.prefabProjectile` (`0x20`) is the object that flies, with `prefabMuzzle` (`0x28`) and `prefabHit` (`0x30`) for the effects. `EWeapon.Bone` is `1`. A weapon with Bone's behaviour and a different projectile is a `WeaponData` copy whose `attack` prefab is a copy with `prefabProjectile` replaced.

`WeaponInventory.weapons` and `DataManager`'s weapon table are keyed by `EWeapon`, so a copy that keeps `eWeapon = Bone` is not a new dictionary entry and shares Bone's upgrade offers.

Measured in the running game with `query_objects` on `CharacterData` (21 objects, ids 0 to 20, all `isEnabled`):

| Character | `eWeapon` | Attack prefab | `EPassive` |
| --- | --- | --- | --- |
| Calcium | `1` (Bone) | `BoneAttackPrefab` | `2` (SpeedDemon) |
| Monke | `12` | `BananaAttack` | `8` (WallClimb) |
| TonyMcZoom | `25` | `BluetoothBladeAttack` | `20` (Zap) |

## Stats and passives

Max HP and evasion are plain stats: `EStat.MaxHealth = 0` and `EStat.Evasion = 5`. A character gets them from `statModifiers`, so a trait made only of stat changes and a collider size needs no code.

`PlayerStatsNew` recomputes one stat at a time in the function at `0x446290`. Its first source is `PlayerInventory.characterData` (`0x18`), whose `statModifiers` (`0x60`) it walks for entries naming the stat; shop items, tomes, items and the passive are added after. Each `StatModifier` has a `stat` (`0x10`), a `modifyType` (`0x14`, `EStatModifyType`: `Addition = 0`, `Multiplication = 1`, `Flat = 2`) and a `modification` (`0x18`). The total is `(base + sum of Flat) * (1 + sum of Addition) * product of Multiplication`, stored in `stats` (`0x10`) with the raw total in `rawStats` (`0x18`). Two stats are then transformed: `MaxHealth` has a floor of 1, and `Armor` (`4`) and `Evasion` (`5`) are stored as `v / (v + 0.75) * 0.999` and `v / (v + 1) * 0.999`, so an evasion total of `0.25` gives 20% evasion.

Stock modifiers measured in the running game (stat ids from `EStat`, in order stat, type, value):

| Character | Modifiers |
| --- | --- |
| Calcium | `MoveSpeedMultiplier` (25) Addition 0.15, `JumpHeight` (26) Flat 1.5, `PickupRange` (29) Flat 3 |
| Monke | `MaxHealth` Flat 35, `JumpHeight` Flat 1 (twice), `FallDamageReduction` (27) Flat 0.25, `DamageMultiplier` (12) Flat 0.15 |
| TonyMcZoom | `MaxHealth` Flat -30, `Shield` (2) Flat 10, `MoveSpeedMultiplier` Addition 0.3, `JumpHeight` Flat 3, `FallDamageReduction` Flat 1, `PickupRange` Flat 3 |

Tony's `MaxHealth` Flat `-30` is the stock precedent for a character that trades HP for other stats. Stock collider sizes are `colliderHeight` 3.85 and `colliderWidth` 0.7 for most characters, ranging from 3.7 to 4.75 tall and 0.5 to 0.85 wide.

`PassiveData` (`dump.cs` 349894) carries a name and description (`LocalizedString`), an `ePassive` and a `dummyPassive` ability. `EPassive` runs from `Bullseye = 0` to `Hoarder = 21`, with `None = 9`, and each value has a `PassiveAbility` subclass. The `PlayerInventory` constructor instantiates the passive from `CharacterData.passive`, so the field should point at a real `PassiveData` (the `None` one for a character with no passive).

## Persistence

| State | Where | Unseen character id |
| --- | --- | --- |
| Selected character | `Preferences.selectedCharacter` (`0x20`) | Written when the character is confirmed |
| Skin per character | `Preferences.characterSkins` (`0x10`) | **Throws.** `Preferences.Init` (`0x40F220`) seeds an entry of 0 for each defined `ECharacter` value only (it loops over the enum), and `PlayerRenderer.SetCharacter` reads `characterSkins[eCharacter]` with the throwing getter |
| Hat per character | `Preferences.characterHats` (`0x18`) | `GetCharacterHat` (`0x40F180`) adds a default entry when the key is missing (safe) |
| Progression per character | `ProgressionSaveFile.characterProgression` | `GetCharacterProgression` creates a missing entry on demand |
| Kill statistics key | `StatTrackingUtility.GetKeyKillsCharacter` (`0x412000`) | Creates a missing cache entry on demand |
| Skin achievement names | `LocalizationUtility.GetSkinAchievementName` (`0x3D6DC0`) | Builds and caches a missing `(character, skin type)` key on demand |
| Hat screen | `HatSelection.OnSelectCharacter` (`0x5683A0`) | Takes `eCharacter` from the selected button and reads the hat through the guarded `GetCharacterHat`; its hat list comes from `DataManager.unsortedHats`, not per character |
| Run history by tier | `tierCompletionsWithCharacters` | A `HashSet<ECharacter>` per tier |

The saves are Newtonsoft JSON (`SaveManager.SaveTemp`), and the enum-keyed dictionaries serialize through that. An id with no defined name is written as its number.

The other readers of `ECharacter` pass the integer straight through: `SteamRichPresenceManager.GetEnumCharacter` (`0x3ED100`) returns the running player's character value, and `LeaderboardEntry.GetCharacter` (`0x3E0FA0`, and the static overload at `0x3E2200`) returns the character stored in an entry's details array. A leaderboard entry carrying an unknown id would be decoded by clients that do not have the new character.

## Registering a character at runtime

A new `ECharacter` value needs no change to the enum, because the tables are plain dictionaries keyed by the enum's integer. The registration path that fits the code:

1. Before `DataManager.Load` runs, append a `CharacterData` (`isEnabled` true, `eCharacter` set to the new value, a null `achievementRequirement`, and `numQuestsRequiredForVisibilityInCharacterSelection` of 0) to `unsortedCharacterData`, and at least one `SkinData` with `character` set to the same value to `unsortedSkins`. `Load` then builds the dictionaries and calls `Init` itself, and `CharacterMenu.TryInit` finds the character in the same list.
2. Give the `CharacterData` a `prefab`, `icon`, `weapon`, `passive`, `statModifiers` and collider size as described above.
3. Seed `Preferences.characterSkins[value] = 0` after `Preferences.Init` runs, because `PlayerRenderer.SetCharacter` reads that entry with a throwing getter. The hat table needs nothing.
4. Restore `Preferences.selectedCharacter` when the run ends, as the existing character-screen restriction already does, so the save never names a character the stock game cannot resolve. Remove the seeded skin entry at the same point if the key should not persist in the save.
5. Keep runs as the new character off the leaderboards.

The hooks are a prefix on `DataManager.Load` (`0x4F96D0`) and a postfix on `Preferences.Init` (`0x40F220`). Both RVAs are unique in the dump, which matters because a patch on a folded RVA shared by several methods crashes the game.

### Verdict

Registering a value outside `0..20` is supported by the code paths that were read, with one required fix. The character table, the grid and the spawn path are dictionary and list driven. The lookups that throw for a missing key (`GetCharacterData`, `GetSkins` and the `characterSkins` read) are satisfied by registering the `CharacterData` and one `SkinData` and seeding the skin preference. The one place that loops over the enum, `Preferences.Init`, only fails to seed the new value, which step 3 covers. The fallback, if the points under [Not verified](#not-verified) turn out badly, is to reuse a stock id by cloning that stock character's `CharacterData` instead of adding a new value; that keeps every table lookup valid at the cost of replacing that character while the mod is loaded.

## Stock animation and icon conventions

Measured in the running game with `query_objects`:

- The character-select icon is a 32x32 `Texture` (Calcium, Monke and Amog were read): a pixel-art bust portrait shown on a dark tile.
- Every character has its own `RuntimeAnimatorController` (`CalciumAController`, `AnimatorMonke`, `AnimatorBirdo` and so on). All of them carry an idle, a run (named Run, Running, Walk, Walking or Moving), a Jump, a Falling and a Grind clip, at 45 to 60 frames per second. Idle clips run 1 to 14 s, run cycles 0.6 to 1.5 s, grind cycles 0.5 to 1.3 s and jumps 0.5 to 1.2 s; all but a few jumps loop.
- Animator parameter names are not read from the controllers. The string table holds `grounded`, `moving`, `jump`, `grinding`, `idle` and `slide` as candidates; the exact names stay open until `PlayerRenderer.Update` (`0x3492F0`) is decompiled.

## Authoring the Squeaker model

Squeaker is the original four-legged mouse sketch (`tools/simple_mouse.blend`, left untouched as the source) joined into one skinned mesh and rigged. Four scripts in `scripts/blender/` build it, run in order with `exec(open(path).read())` through the Blender MCP or the Scripting workspace. They rebuild their output on every run; the built scene is `tools/squeaker.blend`.

| Script | Produces |
| --- | --- |
| `squeaker_model.py` | Appends the original parts from a copy of `tools/simple_mouse.blend` (Blender cannot append from the file it has open), bakes the whisker and tail curves to mesh, joins everything into the smooth-shaded mesh `Squeaker` (about 12.7k faces) and builds the armature `SqueakerRig` with vertex weights |
| `squeaker_anim.py` | The actions `Idle`, `Run`, `Jump`, `Falling` and `Grind` on the rig (60 fps, fake user set so they survive a save) |
| `squeaker_cookie.py` | The separate `StaleCookie` object, about 0.64 x 0.68 x 0.12 units (the mouse is about 2.4 units tall), origin at its centre, face along +Z |
| `squeaker_export.py` | `unity/pack-authoring/Assets/Squeaker/squeaker_icon.png` (32x32, transparent, rendered from the head and ears), `Squeaker.fbx` and `StaleCookie.fbx` |

Conventions the Unity import relies on:

- Z up in Blender, the mouse faces -Y. The exporter uses `axis_forward=-Z`, `axis_up=Y`, so the character faces +Z in Unity. `add_leaf_bones` is off, so the bone list is exactly the one below.
- Bones: `root`, `hips` (child of `root`, rear of the body), `torso` (child of `hips`, front of the body), `head`, `ear.L`, `ear.R` (left and right as the source names them), `leg.FL`, `leg.FR`, `leg.BL`, `leg.BR`, `tail.1` to `tail.3`. `hips` and `torso` are lowercase because `PlayerRenderer.SetCharacter` finds them by name. The body blends between them across its middle, so it bends along the spine.
- One mesh with five material slots in a fixed order: fur (`Mouse - warm gray`), skin (`Mouse - pink`), eyes (`Mouse - shiny eyes`), eye sparkle, whiskers. `SkinData.materials` replaces them at runtime, so the slot order is the contract, not the Blender colours. The cookie has two slots: dough, chip.
- Clips are named exactly `Idle`, `Run`, `Jump`, `Falling` and `Grind`, matching the stock set. They are a first pass for a scurrying quadruped; tune them against the game.
- The mesh keeps the sketch's smooth shading and density. The stock characters are low-poly and pixel-textured, so Squeaker does not match them in style; the model follows the sketch.
- Set a `REPO` global before running the scripts when the checkout is not at `~/git/megabonk_mods`.

## Not verified

- The imported FBX clip names and the Animator controller wiring in Unity (no Unity import has been run on these files yet).
- How the game's look rotation and movement tilt (driven through `hips` and `torso`) read on a horizontal body, and whether the model scale fills `colliderHeight`; both are chosen when the prefab is built.
- How the game reacts at startup when `Preferences.selectedCharacter` or an enum-keyed save dictionary holds a value the installed data does not define (the mod removed after a run as the new character). The restore in step 4 avoids the first case; the dictionaries are expected to round-trip an unnamed integer key through Newtonsoft but that has not been tried.
- Readers of `ECharacter` that the dump does not show as typed members. Every typed reference in the dump was read and the ones that matter were decompiled (`DataManager`, the character menu, spawn, stats, `Preferences`, progression, kill statistics, skin achievement names, the hat screen, presence, leaderboards); code that reaches the value through an untyped integer is not covered.
- Whether runs on custom levels or with a modded character submit leaderboard scores. Step 5 depends on where the submission is gated.
- How a character gets custom passive text. `PassiveData` names and descriptions are `LocalizedString` values, so text for a new passive depends on building one at runtime; an existing passive's text is the safe fallback.
- The literal match used for the `hips` and `torso` bones (exact or substring); the lowercase names match the strings the game stores.
- That the throwing getter used for `characterSkins` raises `KeyNotFoundException`; the lookup calls a throw helper that was not decompiled.
