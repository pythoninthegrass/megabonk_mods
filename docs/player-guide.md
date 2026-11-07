# Player guide

How to install the Megabonk Levels mod and play levels other people have made. If you want to build or change the mod itself, read [modding-setup.md](modding-setup.md) instead.

## What this is

Megabonk Levels is an unofficial, fan-made mod. It is not made, endorsed or supported by the developer of Megabonk, and it is not part of Steam Workshop: there is no Subscribe button in Steam, and levels are shared as plain files you copy into the game's folder. The mod loads through [MelonLoader](https://melonwiki.xyz/), a third-party mod loader, and adds custom levels to the game's Map Selection screen beside the built-in maps.

You can remove it any time with the installer's uninstall option below.

## Before you start

- Install Megabonk through Steam and start it once.
- Quit the game, and ideally Steam, before installing.
- You need an internet connection the first time you launch the modded game. It downloads some tools and takes about half a minute while the screen stays black.
- The mod supports the **Windows build** of Megabonk. On Linux and on a Mac that means running the Windows build through Steam Play (Proton) or Wine; the installer sets this up for you but will not install Steam or Wine.

## Installing

Downloads will be published on GitHub Releases: `<GitHub Releases link: to be added>`. That link does not exist yet because the project is still a development setup. Until it does, packages are built from the project's source with `task package:windows`, `task package:linux` or `task package:macos`, so you get yours from whoever shared this mod or a level with you.

Unzip the package, then:

- **Windows:** double-click `install.exe`. It finds the game through Steam, shows a progress window, and does not ask for administrator rights.
- **Linux:** open a terminal in the unzipped folder and run `./install.sh`. It needs Python 3.11 or newer and nothing else.
- **macOS:** open Terminal in the unzipped folder and run `./megabonk-installer`.

The Windows and macOS installers open a window that lists what they will do and waits for you to press Install; on Linux the installer prints its steps as it goes. When it finishes, start Megabonk from Steam. If the game shows a Map Selection screen with extra levels, it worked. If the installer says it found a different game build than the one the package was verified against, it still installs, but the mod may not load until a matching package is released.

To check that an install is intact, run the installer again with `--check` (on Windows, from a command prompt in the unzipped folder). To put the game back exactly as it was, run it with `--uninstall`. Re-running the installer after something goes missing repairs only what is missing.

Details of what each installer does, and what has and has not been tested, are in [player-installer.md](player-installer.md). The Windows installer has so far been tested in a virtual machine, not on a physical PC.

### If the installer does not work

The installer is the recommended route. If it cannot run on your machine you can install by hand; the steps are in [Installing by hand](modding-setup.md#installing-by-hand-for-players).

## Try the included starter

Default player packages include **Bramblecrown Hill**, a composite level with
forest, graveyard, dungeon, desert and hell districts around a tall hill you can climb by a spiral path. Choose it on Map Selection; it needs no
extra packs or music. See [Bramblecrown Hill](starter-level.md) for what to expect
and a short move-rock, save-copy, replay tutorial.

## Finding your levels folder

Levels live in the game's own folder, in `UserData/Levels/`:

1. In Steam, right-click Megabonk, choose Manage, then Browse local files. That opens the game folder.
2. Open `UserData`, then `Levels`. If either folder is missing, create it with exactly that name.

A level is a single file ending in `.mblevel.json`.

## Playing a level someone shared

1. Save the `.mblevel.json` file they sent you.
2. Copy it into `UserData/Levels/`.
3. Start Megabonk. The level appears on the Map Selection screen beside the built-in maps, under the title the author gave it.

If a level shows up but looks empty or as a placeholder, it needs an asset pack you do not have. The mod logs the missing pack's name in `MelonLoader/Latest.log` in the game folder as `pack '<name>' is not installed`. Ask the author for the pack, which is a folder to place in `UserData/LevelPacks/`, or use an installer package that includes it.

A level can have a picture on the Map Selection screen: put an image with the same name as the level next to it, for example `thps.png` beside `thps.mblevel.json`.

## Sharing a level

Send the `.mblevel.json` file from your `UserData/Levels/` folder, as a Discord attachment, a forum upload or by any other way you would send a file. If it has a picture, send that too. If your level uses an asset pack, say which one, because the person receiving it needs it as well.

Levels from other people are data files the game reads, not programs, but the mod itself is code from a third party. Install the mod only from someone you trust.
