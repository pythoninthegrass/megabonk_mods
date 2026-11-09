# Modding setup

The runtime on this branch targets **BepInEx 6 IL2CPP** (`BepInExPack_IL2CPP` 6.0.0-be.788). Install that pack and launch the game once to generate `BepInEx/interop/` before building. See [running BepInEx under Wine](development.md#running-bepinex-under-wine) for the required files, DLL override and reversible loader switch. Do not activate MelonLoader and BepInEx together.

The existing player installers described below still package the older MelonLoader runtime; they are not an installation path for this branch's DLL. Keep using the matching released package until the BepInEx packaging cutover.

## File naming convention

Inside `src/MegabonkLevels.Mod/`:

- Pure-logic files (no Unity/Harmony/loader dependency) use a plain snake_case name, e.g. `edit_stack.cs`. These are unit-testable and get compile-linked into `tests/MegabonkLevels.Tests/`.
- Harmony patches generally use a `_patch` suffix, e.g. `generation_patch.cs`. Unity and loader integration files cannot be unit-tested without the runtime and are not compile-linked into the test project.

## Legacy MelonLoader installation

```sh
task game:melonloader:install
```

This downloads the pinned MelonLoader release, verifies its checksum, and extracts it into your resolved Megabonk game directory (see below). The task is idempotent: it's a no-op if the pinned version is already installed. On macOS it also applies the Wine DLL override (`version.dll` -> `native,builtin`) that IL2Cpp hooking needs under Wine, through plain Wine by default or CrossOver's Wine when `MEGABONK_MACOS_RUNTIME=crossover` (`task crossover:melonloader:install` sets that for you). Run `task wine:install` first on a new macOS setup; see [development.md](development.md#launching-under-wine-macos).

## Pointing a build at your own Megabonk install

Path resolution precedence (see `scripts/game_paths.py`): process environment variable > `.env` file > built-in default.

1. Copy `.env.example` to `.env` and set `MEGABONK_WINE_PREFIX` (the macOS Wine prefix that holds Steam, the directory containing `drive_c`) or `MEGABONK_GAME_DIR` (direct game directory override, any platform) if your install isn't at the default location. On macOS, `MEGABONK_MACOS_RUNTIME` (`wine` by default, or `crossover`) selects the runtime and `MEGABONK_WINE` overrides the plain Wine binary.
2. The mod build reads the same three settings with the same precedence from the environment (`Directory.Build.props`): `MEGABONK_GAME_DIR`, then `MEGABONK_WINE_PREFIX`, then the older `MEGABONK_BOTTLE` (the prefix's `drive_c`), then the default prefix. A leading `~` is expanded. `task mod:build` loads `.env` into the environment; a bare `dotnet build` or IDE build sees only the process environment. For local overrides use the gitignored `src/MegabonkLevels.Mod/Directory.Build.local.props`. `GameFolder` determines `BepInExCoreFolder` (`BepInEx/core`), `Il2CppAssembliesFolder` (`BepInEx/interop`) and `ModInstanceFolder` (`BepInEx/plugins/MegabonkLevels`). Remove obsolete MelonLoader interop overrides rather than mixing loaders' assemblies.

To compile without deploying into the game's plugins folder, pass `-p:ModInstanceFolder=<temp dir>/` to `dotnet build`. `dotnet msbuild src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj -getProperty:GameFolder` prints the game folder the build resolved.

Run `uv run scripts/game_paths.py` at any point to see the paths actually resolved.

## Installing for players on Linux

MelonLoader's native Linux support does not work yet: 0.7.3 segfaults `Megabonk.x86_64` while generating the Il2Cpp assemblies, and the upstream fix is not in a release. The supported Linux route is the **Windows** build of Megabonk under Steam Play/Proton, with the Windows MelonLoader and a Windows .NET 6 runtime — which is what the player installer does for them.

```sh
task package:linux LEVELS="example-forest.mblevel.json thps.mblevel.json" PACKS=thps MOD_VERSION=0.4.2
```

That produces `.tools/player-package/` and a distributable zip beside it. A player unzips it and runs `./megabonk-installer`, a static Go binary that needs nothing else — no Python, no uv, no repo, no Wine install. It finds the Steam install (native or Flatpak) and the game directory, refuses a native-Linux game directory with instructions for switching to the Windows build, installs MelonLoader, the mod, and the .NET runtime, sets the `version.dll` override in the Proton prefix, and writes a record that makes `--check` and `--uninstall` exact. When the .NET runtime cannot go inside the prefix it prints a `DOTNET_ROOT=... %command%` launch option for the player to paste — it never edits Steam's `localconfig.vdf`, which Steam rewrites while it runs.

The package format, the manifest contract, and the Linux behaviour are documented in [player-installer.md](player-installer.md), including what has been verified offline and what still needs a real Linux desktop.

For developing on Linux rather than installing for a player, the mod and its harness work under Proton the same way; the caveats for the native build (no Proton prefix, `LD_PRELOAD` MelonLoader, the .NET 6 runtime Flatpak Steam can actually read) are in [development.md](development.md).

## Installing for players on Windows

```sh
task package:windows LEVELS="example-forest.mblevel.json" MOD_VERSION=0.4.2
```

A player unzips the result and runs `install.exe`. It finds the game through Steam's registry key and `libraryfolders.vdf` (including libraries on other drives), installs the pinned MelonLoader, the mod and a user-scope .NET 6 runtime inside the game directory, shows a progress window and needs no administrator rights. Run it again to repair or `install.exe --uninstall` to restore a vanilla game. Details, including why the runtime goes in `MelonLoader/Dependencies/dotnet`, are in [player-installer.md](player-installer.md#windows-package).

## Installing for players on macOS

```sh
task package:macos LEVELS="example-forest.mblevel.json" MOD_VERSION=0.4.2
```

Megabonk has no macOS build, so a Mac player runs the Windows build under Wine with Steam installed in the same prefix. A player unzips the result and runs `./megabonk-installer` from that folder; it needs no repo, no uv and no .NET SDK. It finds the game in a plain-Wine prefix first (`~/.local/share/megabonk/wine`, `~/.wine`) and in a CrossOver bottle only when no plain-Wine prefix holds it, and `--prefix <folder holding drive_c>` points it anywhere else. It installs the pinned MelonLoader, the mod, a .NET 6 runtime under `MelonLoader/Dependencies/dotnet` and the `version.dll` override in the prefix, shows a progress window, and `--uninstall` restores a vanilla game. The first launch downloads the Il2Cpp assembly generator's tools and takes a while under Wine; see [player-installer.md](player-installer.md#macos-package).

## Installing by hand (for players)

This is the fallback for when the player installer cannot run; the installers in the sections above do exactly these steps and are the recommended route. Use the Windows build of the game on every platform.

1. Download the MelonLoader archive at the version the package names, from the [MelonLoader releases](https://github.com/LavaGang/MelonLoader/releases) (`MelonLoader.x64.zip`, currently 0.7.3), and extract it into the game folder, the one holding `Megabonk.exe`. A package carries the exact archive in its `vendor/` folder with its checksum in `manifest.json`.
2. Copy the mod files from the package into the game folder: `MegabonkLevels.Mod.dll` into `Mods/` and `NLayer.dll` into `UserLibs/`.
3. Create `UserData/Levels/` in the game folder, and copy any `.mblevel.json` files into it.
4. On Linux (Proton) or macOS (Wine), the game folder's `version.dll` must be loaded in preference to the system one: set the DLL override `version` = `native,builtin` in the Wine or Proton prefix, for example with `winecfg` (Libraries tab). Native Windows needs no override.
5. Start the game from Steam. On native Windows MelonLoader installs the .NET 6 runtime itself on first launch, machine-wide under Program Files; on Linux and macOS install a Windows .NET 6 runtime into the prefix first. The first launch downloads tools and takes about half a minute.
6. Open `MelonLoader/Latest.log` in the game folder and look for `1 Mod loaded.` and `MegabonkLevels mod initialized.`.

To undo it, delete `MelonLoader/`, `Mods/MegabonkLevels.Mod.dll` and `UserLibs/NLayer.dll` from the game folder, plus `version.dll` (MelonLoader's loader stub).

## Running and verifying the mod

```sh
task mod:build   # deploys DLL, PDB and NLayer into BepInEx/plugins/MegabonkLevels
task game:run     # launches Megabonk
```

A successful load logs `Loading [MegabonkLevels 0.0.1]` and `MegabonkLevels mod initialized.` in `BepInEx/LogOutput.log`. Loader assemblies are never copied beside the plugin. F6 reads `megabonklevels-test-level.mblevel.json` beside the plugin DLL. Levels, packs, music and console history retain their existing game-root `UserData/` locations.

The script log helpers still select the legacy log until their migration; inspect `BepInEx/LogOutput.log` directly rather than trusting `task game:log` or `run.py relaunch` on this branch.

To exercise a level without driving the game with key presses, see [development.md](development.md).
