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

This downloads the pinned MelonLoader release, verifies its checksum, and extracts it into your resolved Megabonk game directory (see below). The task is idempotent: it's a no-op if the pinned version is already installed. On macOS (CrossOver) it also applies the Wine DLL override (`version.dll` -> `native,builtin`) that IL2Cpp hooking needs under Wine.

## Pointing a build at your own Megabonk install

Path resolution precedence (see `tools/game_paths.py`): process environment variable > `.env` file > built-in default.

1. Copy `.env.example` to `.env` and set `MEGABONK_BOTTLE` (macOS CrossOver bottle) or `MEGABONK_GAME_DIR` (direct game directory override, any platform) if your install isn't at the default location.
2. For MSBuild-time overrides instead (or in addition), copy `src/MegabonkLevels.Mod/Directory.Build.props`'s properties into a `src/MegabonkLevels.Mod/Directory.Build.local.props` file (gitignored) and override `BottleFolder`/`GameFolder`/`ModInstanceFolder` there.

Run `uv run tools/game_paths.py` at any point to see the paths actually resolved.

## Running and verifying the mod

```sh
task mod:build   # builds the mod; the csproj's AfterTargets=Build step deploys the DLL+PDB into the game's Mods folder
task game:run     # launches Megabonk
task game:log     # tails MelonLoader's Latest.log
```

A successful load logs an `OnInitializeMelon` message from `MegabonkLevelsMod` in `Latest.log`.
