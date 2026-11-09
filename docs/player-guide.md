# Player guide

How to install **Megabonk Level Editor** and play levels other people have made.
For building or changing the mod itself, read [modding-setup.md](modding-setup.md).

## What this is

Megabonk Level Editor is an unofficial, fan-made mod. It is not made, endorsed or
supported by the developer of Megabonk, and it is not part of Steam Workshop:
there is no Subscribe button in Steam. The mod loads through **BepInEx 6 IL2CPP**
and adds custom levels to Map Selection beside the built-in maps. Levels are
shared as plain files you copy into the game's folder.

The editor package contains no levels, third-party asset packs or music.

## Before you start

- Install Megabonk through Steam and start it once.
- Quit the game, and ideally Steam, before installing.
- You need an internet connection the first time you launch the modded game. It downloads some tools and takes about half a minute while the screen stays black.
- The mod supports the **Windows build** of Megabonk. On Linux and on a Mac,
  run that build through Steam Play (Proton) or Wine. Install those separately;
  the mod ZIP does not install Steam, Wine or the game.
- Do not activate MelonLoader and BepInEx together. Keep a backup of an older
  setup and follow the [loader rollback guide](thunderstore.md#rollback) when
  switching between them.

## Installing

The public Thunderstore release has not been published yet. For local testing,
the package is built from source with `task package:thunderstore`; get that ZIP
from its builder and import it through your manager's local/custom-mod option.
Its package identifier is `Megabonk_Level_Editor`.

1. Select **Megabonk** in a compatible mod manager and create a clean profile.
2. Install **BepInExPack IL2CPP 6.0.788** and import the editor ZIP. Apply the
   profile to the game.
3. Start the modded game. Check `BepInEx/LogOutput.log` for
   `Loading [Megabonk Level Editor 0.0.1]` and `MegabonkLevels mod initialized.`.
4. Add a level as described below, then restart the game to see it on Map Selection.

On macOS, the tested setup is r2modmac 1.1.0 for managing files and plain Wine
11.18 for launching. Apply omits the BepInEx pack's `dotnet/` runtime, and its
Play button did not launch the Wine-hosted game. Follow the
[package README's Wine instructions](../pkg/README.md#macos--wine-and-linux--proton)
for the runtime and `winhttp` override. For manual installation, see
[Installing by hand](modding-setup.md#installing-by-hand-for-players).

Disable the editor in the manager and Apply to remove it. Keep your levels,
packs and music under `UserData/`; disabling the mod does not remove them.

## Try Bramblecrown Hill

**Bramblecrown Hill** is an example level supplied separately from the editor.
Get `levels/bramblecrown-hill.mblevel.json` from the source repository or the
person who shared the mod, then copy it into `UserData/Levels/`. It needs no
extra packs or music. See [Bramblecrown Hill](starter-level.md) for a tour of its
five districts and a short move-rock, save-copy, replay tutorial.

The old standalone installer format is documented in
[player-installer.md](player-installer.md) for the `melonloader-final` tag only;
it is not compatible with the current BepInEx DLL.

## Finding your levels folder

Levels live in the game's own folder, in `UserData/Levels/`:

1. In Steam, right-click Megabonk, choose Manage, then Browse local files. That opens the game folder.
2. Open `UserData`, then `Levels`. If either folder is missing, create it with exactly that name.

A level is a single file ending in `.mblevel.json`.

## Playing a level someone shared

1. Save the `.mblevel.json` file they sent you.
2. Copy it into `UserData/Levels/`.
3. Start Megabonk. The level appears on the Map Selection screen beside the built-in maps, under the title the author gave it.

If a level shows up but looks empty or as a placeholder, it needs an asset pack you do not have. The mod logs the missing pack's name in `BepInEx/LogOutput.log` in the game folder as `pack '<name>' is not installed`. Ask the author for the pack, which is a folder to place in `UserData/LevelPacks/`.

A level can have a picture on the Map Selection screen: put an image with the same name as the level next to it, for example `thps.png` beside `thps.mblevel.json`.

## Sharing a level

Send the `.mblevel.json` file from your `UserData/Levels/` folder, as a Discord attachment, a forum upload or by any other way you would send a file. If it has a picture, send that too. If your level uses an asset pack, say which one, because the person receiving it needs it as well.

Levels from other people are data files the game reads, not programs, but the mod itself is code from a third party. Install the mod only from someone you trust.
