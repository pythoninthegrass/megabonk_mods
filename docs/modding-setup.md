# Modding setup

Megabonk mods in this repo are built on [MelonLoader](https://melonwiki.xyz/), since Megabonk is a Unity IL2CPP game with no bundled mod loader. This doc covers installing MelonLoader, pointing a local build at your own Megabonk install, and verifying the mod loaded.

## File naming convention

Inside `src/MegabonkLevels.Mod/`:

- Pure-logic files (no Unity/Harmony/MelonLoader dependency) use a plain snake_case name, e.g. `edit_stack.cs`. These are unit-testable and get compile-linked into `tests/MegabonkLevels.Tests/`.
- Unity/Harmony-dependent files (Harmony patches, `MelonMod` subclasses, anything touching IL2Cpp types) use a `_patch` suffix, e.g. `generation_patch.cs`. These cannot be unit-tested without Unity loaded and are never compile-linked into the test project.

## Installing MelonLoader

```sh
task game:melonloader:install
```

This downloads the pinned MelonLoader release, verifies its checksum, and extracts it into your resolved Megabonk game directory (see below). The task is idempotent: it's a no-op if the pinned version is already installed. On macOS it also applies the Wine DLL override (`version.dll` -> `native,builtin`) that IL2Cpp hooking needs under Wine, through plain Wine by default or CrossOver's Wine when `MEGABONK_MACOS_RUNTIME=crossover` (`task crossover:melonloader:install` sets that for you). Run `task wine:install` first on a new macOS setup; see [development.md](development.md#launching-under-wine-macos).

## Pointing a build at your own Megabonk install

Path resolution precedence (see `scripts/game_paths.py`): process environment variable > `.env` file > built-in default.

1. Copy `.env.example` to `.env` and set `MEGABONK_WINE_PREFIX` (the macOS Wine prefix that holds Steam, the directory containing `drive_c`) or `MEGABONK_GAME_DIR` (direct game directory override, any platform) if your install isn't at the default location. On macOS, `MEGABONK_MACOS_RUNTIME` (`wine` by default, or `crossover`) selects the runtime and `MEGABONK_WINE` overrides the plain Wine binary.
2. The mod build reads the same three settings with the same precedence from the environment (`Directory.Build.props`): `MEGABONK_GAME_DIR`, then `MEGABONK_WINE_PREFIX`, then the older `MEGABONK_BOTTLE` (the prefix's `drive_c`), then the default prefix. A leading `~` is expanded. `task mod:build` loads `.env` into the environment, so it follows your `.env`; a bare `dotnet build` or an IDE build sees only the process environment, so export the setting there. For anything the settings do not cover, copy the properties you need from `src/MegabonkLevels.Mod/Directory.Build.props` into a `src/MegabonkLevels.Mod/Directory.Build.local.props` file (gitignored) and override `BottleFolder`/`GameFolder`/`ModInstanceFolder` there; it wins over the environment. `BottleFolder` is the prefix's `drive_c`; `GameFolder`, the MelonLoader folders and `ModInstanceFolder` derive from it.

To compile without copying the DLL into the game's `Mods` folder, pass `-p:ModInstanceFolder=<temp dir>/` to `dotnet build`. `dotnet msbuild src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj -getProperty:GameFolder` prints the game folder the build resolved.

Run `uv run scripts/game_paths.py` at any point to see the paths actually resolved.

## Installing for players on Linux

MelonLoader's native Linux support does not work yet: 0.7.3 segfaults `Megabonk.x86_64` while generating the Il2Cpp assemblies, and the upstream fix is not in a release. The supported Linux route is the **Windows** build of Megabonk under Steam Play/Proton, with the Windows MelonLoader and a Windows .NET 6 runtime — which is what the player installer does for them.

```sh
task package:linux LEVELS="example-forest.mblevel.json thps.mblevel.json" PACKS=thps MOD_VERSION=0.4.2
```

That produces `.tools/player-package/` and a distributable zip beside it. A player unzips it and runs `./install.sh`; it needs Python 3.13 or newer and nothing else — no uv, no repo, no Wine install. It finds the Steam install (native or Flatpak) and the game directory, refuses a native-Linux game directory with instructions for switching to the Windows build, installs MelonLoader, the mod, and the .NET runtime, sets the `version.dll` override in the Proton prefix, and writes a record that makes `--check` and `--uninstall` exact. When the .NET runtime cannot go inside the prefix it prints a `DOTNET_ROOT=... %command%` launch option for the player to paste — it never edits Steam's `localconfig.vdf`, which Steam rewrites while it runs.

The package format, the manifest contract, and the Linux behaviour are documented in [player-installer.md](player-installer.md), including what has been verified offline and what still needs a real Linux desktop.

For developing on Linux rather than installing for a player, the mod and its harness work under Proton the same way; the caveats for the native build (no Proton prefix, `LD_PRELOAD` MelonLoader, the .NET 6 runtime Flatpak Steam can actually read) are in [development.md](development.md).

## Installing for players on Windows

```sh
task package:windows LEVELS="example-forest.mblevel.json" MOD_VERSION=0.4.2
```

A player unzips the result and runs `install.exe`. It finds the game through Steam's registry key and `libraryfolders.vdf` (including libraries on other drives), installs the pinned MelonLoader, the mod and a user-scope .NET 6 runtime inside the game directory, shows a progress window and needs no administrator rights. Run it again to repair or `install.exe --uninstall` to restore a vanilla game. Details, including why the runtime goes in `MelonLoader/Dependencies/dotnet`, are in [player-installer.md](player-installer.md#windows-package).

## Running and verifying the mod

```sh
task mod:build   # builds the mod; the csproj's AfterTargets=Build step deploys the DLL+PDB into the game's Mods folder
task game:run     # launches Megabonk
task game:log     # tails MelonLoader's Latest.log
```

A successful load logs an `OnInitializeMelon` message from `MegabonkLevelsMod` in `Latest.log`.

To exercise a level without driving the game with key presses, see [development.md](development.md).
