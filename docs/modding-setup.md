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
2. For MSBuild-time overrides instead (or in addition), copy `src/MegabonkLevels.Mod/Directory.Build.props`'s properties into a `src/MegabonkLevels.Mod/Directory.Build.local.props` file (gitignored) and override `BottleFolder`/`GameFolder`/`ModInstanceFolder` there. MSBuild does not read `.env`, and `Directory.Build.props` defaults to the CrossOver Steam bottle, so a build against any other prefix needs this file. For the default plain-Wine prefix it is:

```xml
<Project>
  <PropertyGroup>
    <BottleFolder>$(HOME)/.local/share/megabonk/wine/drive_c</BottleFolder>
  </PropertyGroup>
</Project>
```

`BottleFolder` is the prefix's `drive_c`; `GameFolder`, the MelonLoader folders and `ModInstanceFolder` derive from it. To compile without copying the DLL into the game's `Mods` folder, pass `-p:ModInstanceFolder=<temp dir>/` to `dotnet build`.

Run `uv run scripts/game_paths.py` at any point to see the paths actually resolved.

## Running and verifying the mod

```sh
task mod:build   # builds the mod; the csproj's AfterTargets=Build step deploys the DLL+PDB into the game's Mods folder
task game:run     # launches Megabonk
task game:log     # tails MelonLoader's Latest.log
```

A successful load logs an `OnInitializeMelon` message from `MegabonkLevelsMod` in `Latest.log`.

To exercise a level without driving the game with key presses, see [development.md](development.md).
