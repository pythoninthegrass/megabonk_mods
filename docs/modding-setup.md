# Modding setup

**Megabonk Level Editor** targets **BepInEx 6 IL2CPP** (`BepInExPack_IL2CPP` 6.0.788). Install that pack and launch the game once to generate `BepInEx/interop/` before building. See [running BepInEx under Wine](development.md#running-bepinex-under-wine) for the required files, DLL override and reversible loader switch. Do not activate MelonLoader and BepInEx together.

For playing rather than developing, use the [package README](../pkg/README.md)
and [player guide](player-guide.md). The standalone MelonLoader installers belong
to the `melonloader-final` tag, not the current DLL.

## File naming convention

Inside `src/MegabonkLevels.Mod/`:

- Pure-logic files (no Unity/Harmony/loader dependency) use a plain snake_case name, e.g. `edit_stack.cs`. These are unit-testable and get compile-linked into `tests/MegabonkLevels.Tests/`.
- Harmony patches generally use a `_patch` suffix, e.g. `generation_patch.cs`. Unity and loader integration files cannot be unit-tested without the runtime and are not compile-linked into the test project.

## Install the loader first

Install [BepInExPack IL2CPP 6.0.788](https://thunderstore.io/c/megabonk/p/BepInEx/BepInExPack_IL2CPP/)
with a compatible manager, or follow the manual steps below. Use the Windows
game build on every platform: native Windows, Proton on Linux or Wine on macOS.
Native Linux mod support is not verified. On a new Mac setup, run
`task wine:install` first; see [launching under Wine](development.md#launching-under-wine-macos).

## Pointing a build at your own Megabonk install

Path resolution precedence (see `scripts/game_paths.py`): process environment variable > `.env` file > built-in default.

1. Copy `.env.example` to `.env` and set `MEGABONK_WINE_PREFIX` (the macOS Wine prefix that holds Steam, the directory containing `drive_c`) or `MEGABONK_GAME_DIR` (direct game directory override, any platform) if your install isn't at the default location. On macOS, `MEGABONK_MACOS_RUNTIME` (`wine` by default, or `crossover`) selects the runtime and `MEGABONK_WINE` overrides the plain Wine binary.
2. The mod build reads the same three settings with the same precedence from the environment (`Directory.Build.props`): `MEGABONK_GAME_DIR`, then `MEGABONK_WINE_PREFIX`, then the older `MEGABONK_BOTTLE` (the prefix's `drive_c`), then the default prefix. A leading `~` is expanded. `task mod:build` loads `.env` into the environment; a bare `dotnet build` or IDE build sees only the process environment. For local overrides use the gitignored `src/MegabonkLevels.Mod/Directory.Build.local.props`. `GameFolder` determines `BepInExCoreFolder` (`BepInEx/core`), `Il2CppAssembliesFolder` (`BepInEx/interop`) and `ModInstanceFolder` (`BepInEx/plugins/MegabonkLevels`). Remove obsolete MelonLoader interop overrides rather than mixing loaders' assemblies.

To compile without deploying into the game's plugins folder, pass `-p:ModInstanceFolder=<temp dir>/` to `dotnet build`. `dotnet msbuild src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj -getProperty:GameFolder` prints the game folder the build resolved.

Run `uv run scripts/game_paths.py` at any point to see the paths actually resolved.

## Build a player package

The supported distributable is the runtime-only Thunderstore ZIP:

```sh
task package:thunderstore
task package:thunderstore:check
```

Import the ZIP from `.tools/thunderstore/` through the manager's local/custom-mod
import. It does not include levels, packs or music. See
[Thunderstore packaging](thunderstore.md) for the package contract, clean-profile
checks, Wine caveats and publication gates. There is no public release download
yet; building or locally testing a ZIP does not publish it.

## Installing by hand (for players)

Prefer a compatible mod manager. For a manual BepInEx install, quit the game first:

1. Download BepInExPack IL2CPP **6.0.788** and extract the **contents** of its
   `BepInExPack/` folder beside `Megabonk.exe`, including `dotnet/`, `winhttp.dll`
   and `doorstop_config.ini`.
2. Park an existing MelonLoader `version.dll` as a backup, rather than activating
   both loaders. Keep its files for [rollback](thunderstore.md#rollback).
3. Copy the mod ZIP's `BepInEx/` contents into the game's `BepInEx/` folder.
   The plugin, NLayer and its license belong together under
   `BepInEx/plugins/MegabonkLevels/`. Never copy game interop or loader assemblies
   beside the plugin.
4. Under Wine or Proton, set `winhttp=native,builtin`. A Proton Steam launch can
   use `WINEDLLOVERRIDES="winhttp=n,b" %command%`. Native Windows needs no override.
   r2modmac's runtime omission and Wine launch limitations are documented in the
   [package README](../pkg/README.md#macos--wine-and-linux--proton).
5. Create `UserData/Levels/` in the game folder and add separately supplied
   `.mblevel.json` files. The package itself contains no levels.
6. Launch the game. The first BepInEx start needs internet and takes roughly half
   a minute to generate interop. Check `BepInEx/LogOutput.log` for the plugin's
   loading and initialization lines below.

To remove the mod, disable it in the manager and Apply, or park its plugin folder
while the game is stopped. Preserve user-authored content under `UserData/`.

## Running and verifying the mod

```sh
task mod:build   # deploys DLL, PDB and NLayer into BepInEx/plugins/MegabonkLevels
task game:run     # launches Megabonk
```

A successful load logs `Loading [Megabonk Level Editor 0.0.1]` and `MegabonkLevels mod initialized.` in `BepInEx/LogOutput.log`. Loader assemblies are never copied beside the plugin. F6 reads `megabonklevels-test-level.mblevel.json` beside the plugin DLL. Levels, packs, music and console history retain their existing game-root `UserData/` locations.

`task game:log`, `run.py relaunch` and MCP log helpers use the BepInEx layout.
Restart an already-connected MCP server after updating Python modules. For
nonstandard game locations, note the launcher's explicit-executable caveat in
[Thunderstore packaging](thunderstore.md#test-the-final-zip-not-the-build-folder).

To exercise a level without driving the game with key presses, see [development.md](development.md).

## Legacy MelonLoader tooling

The standalone installers and their [format reference](player-installer.md) are
retained for historical use with `melonloader-final`. The old platform package
tasks are internal: they are hidden from task listings and cannot be run directly.
Do not add a public wrapper that combines those installers with the BepInEx DLL.
Use a separate worktree at the legacy tag when rebuilding a MelonLoader package.
