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

The public release is available on
[Thunderstore](https://thunderstore.io/c/megabonk/p/pythoninthegrass/Megabonk_Level_Editor/).
Its package identifier is `Megabonk_Level_Editor`.

1. Select **Megabonk** in a compatible mod manager and create a clean profile.
2. Install **Megabonk Level Editor** from its Thunderstore page. The manager should also install
   **BepInExPack IL2CPP 6.0.788**. Apply the profile to the game.
3. Start the modded game. Check `BepInEx/LogOutput.log` for
   `Megabonk Level Editor` and `MegabonkLevels mod initialized.`.
4. Add a level as described below, then restart the game to see it on Map Selection.

For local testing, build the package from source with `task package:thunderstore`
and import the resulting ZIP through your manager's local/custom-mod option instead.

On macOS, the tested setup is r2modmac 1.1.0 for managing files and plain Wine
11.18 for launching. Apply omits the BepInEx pack's `dotnet/` runtime, and its
Play button did not launch the Wine-hosted game. Follow the
[package README's Wine instructions](../pkg/README.md#macos--wine-and-linux--proton)
for the runtime and `winhttp` override. For manual installation, see
[Installing by hand](modding-setup.md#installing-by-hand-for-players).

If you have a source checkout on the Mac, the optional
[r2modmac repair helper](development.md#repairing-an-r2modmac-apply) automates
copying the missing runtime files and safely disabling the old MelonLoader proxy.
It does not replace installing and applying the profile in r2modmac.

Disable the editor in the manager and Apply to remove it. Keep your levels,
packs and music under `UserData/`; disabling the mod does not remove them.

## Try Bramblecrown Hill

**Bramblecrown Hill** is an example level supplied separately from the editor.
Get `levels/bramblecrown-hill.mblevel.json` from the source repository or the
person who shared the mod, then copy it into `UserData/Levels/`. It needs no
extra packs or music. See [Bramblecrown Hill](starter-level.md) for a tour of its
five districts and a short move-rock, save-copy, replay tutorial.

The old standalone installer format is documented in
[player-installer.md](player-installer.md) as a legacy MelonLoader reference only;
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

## Controls and console commands

Press **backtick/tilde** to open the mod's console, then type a command and
press **Enter**. Use this console, not the game's F10 debug console.

These shortcuts work during a run. Close the console before using F7 or F8.

| Key | Action |
| --- | --- |
| **F7** | Show or hide coordinates on a custom level. Off by default; does not pause the run. |
| **F8** | Switch between playing and the editor's paused, free-fly view. Press again to return to play. |
| **Backtick/tilde** | Open or close the mod's console. Opening it pauses a running game; closing it restores the previous pause state. |
| **Enter** | Run the typed console command. |
| **Tab** | Complete a command or level title; press again to cycle matches. |
| **Up / Down** | Recall previous console commands. |
| **Ctrl-R** | Search command history. Enter selects a result; Enter again runs it. |
| **Esc** | Close history search, or close the console if search is not open. |

**Dev** commands require `MEGABONK_DEV=true` in the game's launch
environment before starting the game; ordinary player commands and F7/F8 do not.
Putting this setting in a repository `.env` only works when launching through
the repository's development tools, not when starting from a mod manager.

| Command | Action | Requires dev mode |
| --- | --- | --- |
| `help` / `help music` | List available commands, optionally filtered by name. | No |
| `state` | Show the current run/editor state. | No |
| `level.list` | List installed custom-level files. | No |
| `ui.coordinates on` / `ui.coordinates off` | Show or hide coordinates on a custom level, like F7. | No |
| `ui.hud on` / `ui.hud off` | Show or hide the game's HUD. | No |
| `music.list` / `music.now` | List music tracks or show the current track. | No |
| `music.pause` / `music.play` | Pause or resume the level's music. | No |
| `music.next` / `music.prev` | Skip to the next or previous music track. | No |
| `music.track 2` | Play a track by its number in `music.list`. | No |
| `history` / `clear` | List command history or clear console output. | No |
| `editor on` / `editor off` | Enter or leave the editor through the console. | Yes |
| `level.load "Bramblecrown Hill"` | Load an installed level by title; quote titles containing spaces. | Yes |
| `level.save "My Level"` | Save the editor's current level under a name. | Yes |
| `level.new "My Level"` | Create a blank level and open it in the editor. | Yes |

`help` lists only commands available in your current mode. For the full command
language and advanced debug commands, see the
[console reference](development.md#console-command-language).

## Sharing a level

Send the `.mblevel.json` file from your `UserData/Levels/` folder, as a Discord attachment, a forum upload or by any other way you would send a file. If it has a picture, send that too. If your level uses an asset pack, say which one, because the person receiving it needs it as well.

Levels from other people are data files the game reads, not programs, but the mod itself is code from a third party. Install the mod only from someone you trust.
