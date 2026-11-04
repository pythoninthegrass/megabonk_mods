# Player installer

The player-facing download: a folder a Linux player unzips and runs `./install.sh` in, which installs MelonLoader, the MegabonkLevels mod, the .NET 6 runtime it needs, and any levels or packs the package carries. This doc is the contract between the two halves — the **package** the build produces and the **installer** that consumes it — plus the Linux-specific behaviour that contract cannot express.

Everything here is Python standard library only, on both sides. The installer runs as `python3 -m player_installer` from a copy of `scripts/player_installer/` that travels inside the package, so a player needs Python 3.11 or newer and nothing else: no uv, no repo checkout, no .NET SDK, no Wine installation. The floor is set by the newest feature the bundled modules use and is enforced by `install.sh` rather than just advertised, so an older interpreter gets a package-manager hint instead of a traceback.

## Linux player setup

Use the **Windows game under Proton/Wine**, not the native Linux build. In Steam,
open Megabonk's Properties → Compatibility and select Proton, then wait for the
Windows download to finish. Selecting Proton in the GUI triggered the depot
switch on Fedora; editing Steam's configuration alone did not. Launch vanilla
once to create the prefix, choose **DX11 - Recommended**, then quit the game
before installing. `-force-d3d11` in Steam's Launch Options pins that renderer.

Unzip the player package and run `./install.sh` with Python 3.11 or newer.
Packages are currently built with `task package:linux`; a published player
download URL is not yet available. No separate Wine install is needed with
Steam Proton. For a game whose prefix is in a different Steam library, pass
`--prefix` explicitly on both install and check: automatic prefix discovery
currently assumes the game's library.

The following prefix-mode sequence loaded the mod on the CachyOS Proton host.
Replace both paths with your actual game and active prefix paths; while vanilla
is running, its `STEAM_COMPAT_DATA_PATH` environment variable names the compatdata
directory (append `/pfx`). See [the gamepadui guide](gamepadui.md#install-launch-and-verify)
for measurement, package transfer, and remote launch commands.

```sh
cd /path/to/unzipped-player-package
G=/media/sdcard/SteamLibrary/steamapps/common/Megabonk
P="$HOME/.local/share/Steam/steamapps/compatdata/3405340/pfx"
./install.sh --game-dir "$G" --prefix "$P" --dotnet-in prefix --wine-override registry
./install.sh --game-dir "$G" --prefix "$P" --dotnet-in prefix --wine-override registry --check
```

`--check` must exit 0 and report that the install matches the package. Start
Megabonk from Steam and check the **new launch's** `MelonLoader/Latest.log` for
the pinned version banner, `1 Mod loaded.` and
`[MegabonkLevels] MegabonkLevels mod initialized.`. First-launch assembly
generation took about 40 seconds on the tested host; a cached launch need not
repeat `Assembly Generation Successful!`. Prefix-mode .NET needed no
`DOTNET_ROOT` launch option. Inspect the install record for the actual DLL
override method: the observed run reported `via: wine` despite requesting
registry mode. Do not infer success from the Steam launch command or an old log.

Re-run the same install command to repair drift. With the game stopped,
`./install.sh --game-dir "$G" --prefix "$P" --uninstall` removes recorded
installer-owned files, not unrelated mods or saves. Packs must contain Windows
bundles even though the host OS is Linux.

## Package layout

```text
megabonk-levels-<mod>-ml<melonloader>-linux/
├── install.sh                    sh wrapper: picks a new enough interpreter, execs the bundled installer
├── manifest.json                 the contract, described below
├── installer/player_installer/   the installer's own modules, copied in
├── vendor/                       vendor archives, named exactly as the manifest names them
├── content/levels/               bundled .mblevel.json files
└── content/packs/<pack-id>/      bundle + manifest.json (+ attachments.json) per pack
```

`install.sh` is the only entry point a player needs. It picks an interpreter — `--python PATH`, else `MEGABONK_PYTHON`, else `python3` on PATH — checks that it is new enough, and in both failure cases names the package manager command that installs a version that is, then hands the rest to `"$PYTHON" -m player_installer --package <its own directory>`. The interpreter choice is resolved in the wrapper, not by the module: a PATH `python3` too old to parse the bundled code cannot reach an argparse flag, so `--python` has to be read by `sh`; `player_installer` merely declares the flag so it survives the hand-off. A bad explicit path exits 2, an explicit or default interpreter below the floor exits 1, and a missing default `python3` exits 1. Because `-m` resolves modules from the working directory rather than the script's own, the wrapper also puts the bundled `installer/` directory on `PYTHONPATH` — running the module by name without that fails with `No module named player_installer` no matter where the player stands. The floor lives in one place, `MIN_PYTHON` in `scripts/build_player_package.py`, which the wrapper text is built from; the tests parse every bundled module with `ast` at that `feature_version`, and `ruff.toml` exempts `scripts/player_installer/` from pyupgrade so a repo-wide autofix on the 3.13-targeted config cannot raise the bundled code's floor behind the tests' back.

## The manifest

`manifest.json` is a JSON object with `schema` `megabonk-player-package/1`. `load_manifest` in `scripts/player_installer/manifest.py` refuses anything it cannot use, naming the missing or bad key rather than failing later during the install.

| Key | Meaning |
| --- | --- |
| `schema` | `megabonk-player-package/1`. An unknown schema is an error, not a warning: an old installer must not half-install a package from a newer build. |
| `platform` | The OS this package targets: `linux` or `windows`. Both installers accept either value; the manifest differs only in this key. |
| `package_id` | Name in the install record and in `--check` output. |
| `mod_version`, `melonloader_version`, `game_buildid` | Recorded at install time and echoed back by `--check` and `--uninstall`. `game_buildid` is the depot build id the shipped levels were authored against (`GAME_BUILD_ID` in `scripts/build_thps_level.py`), so a package and a level file agree about which game they expect. |
| `generated` | UTC timestamp of the build. Set `SOURCE_DATE_EPOCH` for a byte-identical rebuild. |
| `verified_on` | Distro/version pairs this package was actually tested on. Empty means untested, and it is not a claim of support. |
| `vendors` | The archives under `vendor/`. |
| `files` | Every file to place, and where. |

### vendors

Each entry needs `name`, `url`, `sha256`, `kind`, `version`.

`name` is the **filename under `vendor/`**, not a display name — the installer resolves an archive as `vendor/<name>`. `kind` is the lookup key: the installer asks for `manifest.vendor("melonloader")` and `manifest.vendor("dotnet")`, so a package that omits either kind is rejected before anything is copied. Only those two kinds exist today: MelonLoader's Windows release archive, and a base Windows x64 .NET 6 runtime.

Both archives are the **Windows** ones on purpose, even though the target is Linux: MelonLoader's native Linux build cannot load the native Linux game build, so the whole stack is the Windows stack running under Proton.

`url` is provenance, not a download instruction: the installer never goes to the network. It verifies the copy under `vendor/` against `sha256` and stops if it does not match.

### files

Each entry needs `path` (relative to the package root), `sha256`, and `dest` (relative to the game directory). Destinations follow what the game and the mod actually read:

| Content | `dest` | Why there |
| --- | --- | --- |
| Mod DLL | `Mods/MegabonkLevels.Mod.dll` | Where MelonLoader loads mods from. |
| Managed dependencies (NLayer) | `UserLibs/NLayer.dll` | MelonLoader's probe path for third-party assemblies. |
| Levels | `UserData/Levels/<name>.mblevel.json` | `LiveEditPatch.LevelsDirectoryPath()` lists titled levels from here, and Map Selection shows them beside the native maps. A level anywhere else is invisible to the player. |
| Packs | `UserData/LevelPacks/<id>/{<bundle>,manifest.json,attachments.json}` | `PackPrefabs` loads packs from this layout; see [asset-bundles.md](asset-bundles.md). |

Bundled content is ordinary `files[]` entries, so nothing in the schema is special about it: the same digest check covers it, and `--uninstall` removes it by the same record that removes the mod.

`verify_package` checks every `vendor/<name>` and `files[].path` against its digest and returns a message per problem — missing file or checksum mismatch — which is what `task package:check` runs.

## Install record

After a successful install the installer writes `MegabonkLevels.installer.json` into the game directory, schema `megabonk-levels-install/1`: package id and versions, `installed_at`, the relative paths of every mod file, level and pack it placed, where the .NET runtime went and with what launch option, and how the `version.dll` override was applied. `game_buildid` is the build the package was verified against; `installed_game_buildid` is the build Steam's appmanifest reported when the installer ran, or `null` when it reported none. The second key is optional, so records written before it existed still load under the same schema.

That one file drives both `--check` and `--uninstall`. Uninstall is deliberately record-driven rather than a glob: it removes what it recorded placing and leaves anything it did not put there alone, so a player's own `Mods/` entries, saves, and `UserData` survive.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Done, nothing needed. |
| 1 | Error (bad package, checksum mismatch, I/O). |
| 2 | Usage — e.g. no `--package`. |
| 3 | Nothing found to work on: no Steam install, no game directory, no package. |
| 4 | The game directory is a build this installer will not touch, i.e. the native Linux build. |
| 10 | `--check` found drift between the record and the package. A script can treat 10 as "reinstall" and 0 as "already installed". |

## Installer contract

Every installer — the Python reference behind `install.sh` and the Go binary behind `install.exe` and `megabonk-installer` — implements the steps below in this order, and a player's experience differs between platforms only in how the installer is launched. The sections after this one describe the platform specifics; this one is the single list they must agree with, and `tests/test_installer_parity.py` holds the two implementations to it.

1. **Check the package.** Load `manifest.json` and verify every `vendor/` archive and `files[]` entry against its digest before touching the game. A bad or tampered package exits 1 with the list of mismatches and changes nothing.
2. **Find the game directory.** Use `--game-dir` when given. Otherwise read Steam's recorded libraries and accept a directory only when it holds `Megabonk.exe`, `Megabonk.x86_64` or `Megabonk_Data/`. A game that cannot be found exits 3 and names every Steam client and library considered, each with why it was rejected, plus the flag to retry with.
3. **Classify the build.** Only the Windows build is supported, on every platform. The native Linux build is refused with exit 4 and the steps for switching to the Windows build.
4. **Compare the game build.** Read the installed build id from the library's `appmanifest_3405340.acf` and print whether it matches the build the package was verified against. A difference prints a warning and the run continues, because a game update must not lock a player out; an absent appmanifest prints that the installed build is unknown. The installed id goes into the install record.
5. **Install MelonLoader at the pinned version** from `vendor/`, verified against the manifest checksum. The installer never goes to the network.
6. **Provide the .NET 6 runtime** from `vendor/` at user scope, inside the game directory or the Wine prefix, never machine-wide. Where it goes depends on the platform: [Windows package](#windows-package), [macOS package](#macos-package) and [.NET placement](#net-placement-and-the-launch-option) on Linux.
7. **Apply the `version.dll` override** where a Wine or Proton prefix needs it. Native Windows has none.
8. **Place the mod files** from `files[]`: the mod DLL and its managed dependencies.
9. **Create `UserData/Levels/`**, then **import levels** and **install packs** the package carries or that `--level` and `--pack` name. Inputs are validated first, so a bad level or pack is listed and nothing is half-installed.
10. **Write the install record**, which drives `--check` and `--uninstall`.
11. **Report** what was done and what was not, as numbered `N/M label` lines or a progress window. A failure exits nonzero with a message that says what to do.

### Re-running

A second run with nothing changed does nothing and says so. A run after something has gone missing or stale repairs only that: `--check` compares the install against the package by file digest and loader version marker, exits 10 when anything differs, and the next install run fixes just those entries. A wiped runtime is reinstalled together with its `version.dll` override, because losing one without the other leaves a game that starts and never loads a mod.

After a game update the answer is the same run again. The game build comparison in step 4 tells the player whether the package still matches the game and the repair covers any loader file that went missing; if the build differs and the mod stops loading, the fix is a newer package, which the warning says. Whether Steam's own update or file verification removes the loader files it did not install is not established here; see [what is not verified](#what-is-verified-and-what-is-not).

### Uninstall

`--uninstall` is record-driven: it removes what the record says the installer placed, plus what the loader generates on first launch where the platform notes say so, and leaves a player's own plugins, preferences, levels and saves alone. With no record it removes nothing.

## Building a package

```sh
task package:linux
task package:linux LEVELS="example-forest.mblevel.json thps.mblevel.json" PACKS=thps MOD_VERSION=0.4.2
```

`scripts/build_player_package.py` builds the mod, assembles everything into `.tools/player-package/`, and writes a distributable zip beside it.

Two choices are intentional:

- **Nothing is bundled unless asked.** `levels/` is a working directory full of dev regression maps, so levels are named individually with `--level` and packs with `--pack`. A `.local.mblevel.json` file is skipped even when named: it is a scratch file.
- **Packs come from two places, the way `task pack:install` assembles them**: the built AssetBundle from `.tools/bundles/<platform>/<pack>` and the manifest (plus optional attachments) from `unity/pack-authoring/packs/<pack>/`. `--pack-platform` picks the bundle; `windows` is right on Linux because the game runs the Windows build. Staged packs are validated with `validate_pack_source`, which reproduces the game's own rules — required `id`/`name`/`author`/`version`/`assets` fields, `id` matching the folder name, a bundle file present, and a `pack-attachments/1` sidecar when there is one — so a broken pack fails the build instead of landing in the Warehouse as a placeholder.

Vendor archives are taken from `.tools/vendor-cache/` and only verified there, never downloaded unless you pass `--allow-download` (`ALLOW_DOWNLOAD=true` to the task, which forwards it). The build writes into a staging directory and swaps it in at the end, so a failure leaves the previous package untouched.

When a download does happen it goes through `scripts/asset_download.py`, the only code in `scripts/` that touches the network (a test pins that). The rules: https only, TLS 1.2 floor with certificate verification; the status is checked before the body is read, so a 404, a login or captive-portal page, or an empty body reads as a missing asset rather than a checksum mismatch, and nothing poisoned ever lands in the cache; the body is capped, and an archive whose digest does not match the manifest pin is refused before it is cached. Redirects stay on the original host except for an explicit CDN allowance — GitHub release assets hand off to `release-assets.githubusercontent.com` and dotnetcli to azureedge/microsoft hosts — so an off-list redirect is refused as a missing asset. `install_melonloader.py` uses the same fetcher. The `url` in a manifest entry stays provenance for the player side: the installer itself never downloads.

The zip is deterministic — sorted entries, fixed timestamps, modes 0755 for `install.sh` and 0644 elsewhere — so two builds of the same inputs are byte-identical once `SOURCE_DATE_EPOCH` is pinned.

## Windows package

```sh
task package:windows
task package:windows LEVELS="example-forest.mblevel.json" PACKS=thps MOD_VERSION=0.4.2
```

`task package:windows` builds the mod and the `windows/amd64` Go installer, then runs `scripts/build_player_package.py --platform windows --installer-binary <exe>`. The package has the same `vendor/`, `content/` and `manifest.json` layout as the Linux one with `"platform": "windows"`, but `install.exe` replaces `install.sh` and the bundled Python installer. It lands in `.tools/player-package-windows/` (override with `OUTPUT_WINDOWS`), with `megabonk-levels-<mod>-ml<loader>-windows.zip` beside it. Windows players unzip it and double-click `install.exe`: with no `--package`, the Go installer takes the folder it runs from.

On native Windows the installer finds Steam through `HKCU\Software\Valve\Steam` (then `HKLM\...\WOW6432Node\Valve\Steam` and the Program Files default) and reads `libraryfolders.vdf` for libraries on other drives. It has no prefix, no `version.dll` override and no launch option; every write is inside the game directory. MelonLoader's bootstrap otherwise installs .NET 6 machine-wide under Program Files on first launch, so the installer pre-seeds the vendored runtime into `MelonLoader/Dependencies/dotnet`, the path the loader itself uses; it then logs `Using HostFXR Path: <game>\MelonLoader\Dependencies\dotnet\host\fxr\6.0.36\hostfxr.dll` and runs no runtime installer. `--uninstall` also removes the files the loader creates at first launch (`UserData/Loader.cfg`, and `Plugins/`, `UserData/Levels`, `UserData/LevelPacks`, `UserData` when empty), so the game returns to vanilla while a player's own plugins, preferences and levels stay.

The first launch downloads Cpp2IL from GitHub and takes about 35 seconds, so it needs network access. The Windows flow has been verified in a software-rendered Windows 11 guest, not on real hardware.

## macOS package

```sh
task package:macos
task package:macos LEVELS="example-forest.mblevel.json" PACKS=thps MOD_VERSION=0.4.2
APPLE_SIGNING_IDENTITY="<Developer ID Application identity>" NOTARY_PROFILE=<notarytool keychain profile> task package:macos
```

`task package:macos` builds the mod in Release and the `darwin/arm64` Go installer, then runs `scripts/build_player_package.py --platform macos --installer-binary <binary>`. The package has the same `vendor/`, `content/` and `manifest.json` layout as the others with `"platform": "macos"`, and carries a bare `megabonk-installer` binary with no extension and no wrapper script, mode 0755 in the zip. It lands in `.tools/player-package-macos/` (override with `OUTPUT_MACOS`), with `megabonk-levels-<mod>-ml<loader>-macos.zip` beside it. Only Apple silicon is built: no Intel Mac was available to test an `amd64` binary.

Megabonk has no macOS build, so the player runs the **Windows build under Wine** and the installer works inside that prefix. It does not install Wine, create a prefix or log into Steam: Steam and Megabonk must already be installed in a Wine prefix, and the game started once. The player runs `./megabonk-installer` from the unzipped folder, which is the default `--package`.

### Finding the game and the prefix

Prefixes are searched in this order, and the first Steam library that holds Megabonk wins:

1. `--prefix <folder holding drive_c>`, which limits the search to that prefix.
2. Plain Wine: `~/.local/share/megabonk/wine`, then `~/.wine`.
3. CrossOver bottles under `~/Library/Application Support/CrossOver/Bottles/`, in name order. CrossOver is commercial and is never required, so a bottle is only used when no plain-Wine prefix holds the game.

In each prefix the installer reads Steam's `libraryfolders.vdf` from `drive_c/Program Files (x86)/Steam` and maps the Windows paths in it back to the Mac filesystem: `C:` is the prefix's `drive_c`, `Z:` is the filesystem root, and any other letter follows the prefix's `dosdevices/<letter>:` link. `--game-dir` skips discovery, and the prefix is then the folder above the `drive_c` in that path; a game directory outside any prefix needs `--prefix` as well, and the installer says so rather than guessing.

### What it writes

- MelonLoader and the mod files inside the game directory, as on every platform.
- The vendored .NET 6 runtime in `MelonLoader/Dependencies/dotnet`, the path the loader itself uses, the same placement as native Windows. The launch then logs `Using HostFXR Path: C:\Program Files (x86)\Steam\steamapps\common\Megabonk\MelonLoader\Dependencies\dotnet\host\fxr\6.0.36\hostfxr.dll` and runs no runtime installer. No launch option and no `DOTNET_ROOT` are needed.
- The `version.dll` = `native,builtin` override in the prefix. It goes in through a `wine` binary when one is found (`MEGABONK_WINE`, then `wine64` or `wine` on `PATH`, then a `Wine*.app` under `~/Applications` or `/Applications`), and otherwise by merging into the prefix's `user.reg`, which is also how CrossOver bottles are handled. The method used is recorded as `via` in the install record, and `--wine-override off` skips it.

Re-running is a no-op at the expected version, a wiped runtime is repaired together with its override, and `--uninstall` removes the loader, the mod, the runtime, the override and what the loader generated at first launch, leaving a player's own plugins, preferences and levels.

### First launch

The first launch downloads Cpp2IL and the Unity dependencies and generates the Il2Cpp assemblies, so it needs network access and takes noticeably longer under Wine than elsewhere: about half a minute after the loader starts, during which the window stays black. The mod logs `MegabonkLevels mod initialized.` when it is done. The repo's own `scripts/launch_game.py` passes `--melonloader.agfoffline`, which forbids those downloads, so a fresh install launched that way fails with `UnityDependencies_<version>.zip does not Exist!` and a black screen for ever; start the first launch from Steam, or without the flag.

### Signing

`APPLE_SIGNING_IDENTITY` names a Developer ID Application identity (`security find-identity -v -p codesigning`); the task then signs the installer with the hardened runtime before it is packed, and `codesign --verify --strict` checks it. The finished zip is submitted through `scripts/notarize_macos.py`, which waits for the verdict, when `NOTARY_PROFILE` names a `notarytool` keychain profile or when `APPLE_API_KEY` (key id), `APPLE_API_ISSUER` and `APPLE_API_KEY_B64` (the base64 `.p8`) hold an App Store Connect API key; a profile wins over a key. The key is decoded to a mode 0600 temporary file that is deleted when the submission ends, so the same three variables serve a local run and a CI job. All of them come from the environment, never from the repo. A download through curl carries no quarantine attribute, so Gatekeeper does not assess it; a browser download does, and an unnotarized binary then needs a right-click Open. A notarization ticket cannot be stapled to a bare binary or a zip, so Gatekeeper checks Apple's service when it assesses one.

### What is verified

On an Apple silicon Mac with plain Wine 11 (Wine Devel), against a copy of a working prefix with MelonLoader, the mod, the override and every loader-generated folder removed: the signed package installed 7 steps (exit 0) with `--prefix`, a re-run and `--check` reported nothing to do, the game launched without `--melonloader.agfoffline` and logged `Using HostFXR Path:` under `MelonLoader/Dependencies/dotnet`, `Assembly Generation Successful!`, `1 Mod loaded.` and `MegabonkLevels mod initialized.`, and `--uninstall` returned the game directory to its vanilla contents and removed the override. Default discovery of the plain-Wine prefix was checked with `--dry-run`. CrossOver is covered by unit tests and a `--dry-run` against a real bottle only, since the licence on the test machines has expired. The same install started from Terminal in the desktop session, with no `--no-gui`, opened the progress window, waited for its Install confirmation, and completed with exit 0.

## Linux behaviour

### The Windows build only

The installer classifies the game directory before touching it (`scripts/player_installer/gamebuild.py`). `Megabonk.exe` plus `Megabonk_Data/` is the Windows build and the only supported one. A directory with `Megabonk.x86_64` is the native Linux build and the installer stops with exit 4 and instructions for switching to the Windows build through Steam Play, because MelonLoader 0.7.3 segfaults the native binary during Il2Cpp assembly generation and the upstream fix is not in a release. That is a hard refusal, not a warning: installing onto it would leave a player with a crashed game and no log.

### Finding Steam and the game

`scripts/player_installer/steam.py` looks for a Steam install under `$XDG_DATA_HOME/Steam`, `~/.local/share/Steam`, `~/.steam/root`, `~/.steam/steam`, the two Flatpak locations (`~/.var/app/com.valvesoftware.Steam/...`), and any Flatpak-granted path. A directory counts as a client when it has `steamapps/`. Library folders are read out of `config/libraryfolders.vdf` (`vdf.py`, a read-only parser — the installer never writes VDF).

Game identity comes from `game_candidates`, which offers every directory three searches thought might be Megabonk, in the order it should be trusted: the `installdir` in the library's own `appmanifest_3405340.acf`, then `steamapps/common/Megabonk` by name, then any other Il2Cpp install in `common`. The third tier exists because a copy moved out of its library keeps `GameAssembly.dll` and its data folder but loses the name. Acceptance never rests on that shape: a candidate is Megabonk only when it holds `Megabonk.exe`, `Megabonk.x86_64` or `Megabonk_Data/`, all three named by this game alone. `find_game_dir` takes the first accepted candidate; `--check` and the not-found report name what was rejected and why (`an Il2Cpp install (GameAssembly.dll) but no Megabonk.exe, Megabonk.x86_64 or Megabonk_Data/`), so a machine with another Unity/Il2Cpp title installed says so instead of installing into it.

Two more things make this sturdier than it looks:

- **A library on a detached drive** shows up as a configured root whose `steamapps` is gone. Those roots are skipped rather than reported as a missing game, and only when even the parent directory is missing.
- **Flatpak Steam can only read paths granted to it**, so granted paths from `flatpak override --show` (or the persisted `local-overrides` file) are read on every run and added as extra search roots. They also count as the Flatpak client itself when one of them holds `steamapps/`: a maintainer machine exists where the entire Steam root — `config/`, `userdata/` and `steamapps/` — was moved to a data disk, so no client is left at any default location, and the grants are the only way back to it. Without this, a game on a second disk is simply invisible to a Flatpak install.

### Which Proton prefix

Steam keeps the prefix at `<library>/steamapps/compatdata/<appid>/pfx` **in the library the game was installed to**, which is not always the one holding the game files after a move — the SD-card layout has the files on removable media and the live prefix in the home library. `find_prefix` prefers the game's own library, and when that prefix has no `drive_c/` it takes the only other usable prefix among the libraries searched and prints `Proton prefix: <path> (Steam keeps it in that library, not beside the game)`. Two usable prefixes elsewhere is a guess, so nothing is chosen: both are printed with the `--prefix` hint, and the plan falls back to `gamedir` mode. A prefix passed with `--prefix` silences all of that reporting. `--check` names the prefixes it considered and why each was rejected (`no steamapps/compatdata prefix in this library`, `the prefix has no drive_c/: the game has never been launched under Proton in this library`).

### .NET placement and the launch option

MelonLoader's Il2Cpp support needs a .NET 6 runtime, and the vendored one is the Windows build. It goes in one of two places:

- `--dotnet-in prefix` (the default) extracts it to `<prefix>/drive_c/Program Files/dotnet`, inside the Proton prefix, where Windows .NET finds it on its own and the player changes nothing.
- `--dotnet-in gamedir` extracts it to a `dotnet6-win` directory beside the game executable, for when the prefix is not writable or not usable. The installer then prints the Steam launch option to paste:

```sh
DOTNET_ROOT=Z:\path\to\game\dotnet6-win %command%
```

`Z:` is Proton's drive letter for the filesystem root, so the path after it is the ordinary Unix path. The installer **never edits `localconfig.vdf`**: Steam rewrites that file while it runs and a concurrent write loses. It prints the exact line and leaves the paste to the player.

`usable_prefix` checks for `drive_c`, which Steam creates on the first Proton launch — so the fallback to `gamedir` mode fires when the player has not launched the game yet under Proton, and the warning tells them the launch option is coming.

### version.dll override

IL2Cpp hooking under Proton needs the `version.dll` = `native,builtin` DLL override in the prefix, and the game directory ships a `version.dll` stub for it to pick up. `proton.set_dll_override` writes it through the Proton tool's own `wine` with `reg add` when that binary is findable (`via: wine`), and otherwise merges `Software\Wine\DllOverrides` into the prefix's `user.reg` (`via: registry`). `--wine-override off` skips it; `--wine-override wine` fails loudly when no wine binary exists instead of falling back.

The override is written when the entry is **missing or** when the runtime is being (re)installed. The second condition matters: a wiped prefix loses the override along with the runtime, and reinstalling only one of the two leaves a game that starts and never loads a mod.

The method actually used is recorded and echoed back, so a player reporting a problem can say whether it went in through wine or the registry.

### Levels and packs from the command line

`--level <file>` and `--pack <dir>` install extra content the package does not carry, through the same record so `--uninstall` removes it too. Both are validated before anything is copied — a bad pack is reported as a list of problems and nothing is half-installed.

### Progress reporting

`pick_progress` in `scripts/player_installer/ui.py` requires both a controlling
terminal (`/dev/tty` opens and passes `isatty`) and a desktop session (`DISPLAY`
or `WAYLAND_DISPLAY`, plus a session bus for kdialog) for a GUI progress dialog.
Without either it uses numbered lines on stdout. The terminal probe never reads
stdin, so piped input is left untouched; a pipe alone does not imply headless
when the caller still has a controlling terminal. A tty alone cannot supply a
missing display/session environment, and an SSH session with display variables
but no controlling tty stays headless.

`--non-interactive`, `--no-gui` or `MEGABONK_NON_INTERACTIVE=1` forces plain text
for install and uninstall, even on a desktop with a tty. The environment setting
also accepts `true`, `yes` and `on` (case-insensitive); empty, `0`, `false`, `no`
and `off` leave automatic selection enabled. `--json` suppresses progress output
and dialogs. No installer prompt reads stdin.

Three backends, tried in order: zenity and yad are driven by writing `NN` and `# label` lines to their stdin; KDE's kdialog takes `--progressbar <label> 100` and prints its D-Bus reference (`org.kde.kdialog-<pid> /ProgressDialog`) on stdout, so `GuiProgress` drives it with `qdbus-qt6` (or `qdbus`) instead — `<service> <path> org.kde.kdialog.ProgressDialog.value N` sets progress (the dotted property assignment; `org.freedesktop.DBus.Properties.Set` fails with `InternalError` on this object), `setLabelText` retitles, and `close()` dismisses. kdialog aborts with rc 134 without a display or session bus, so it is only chosen when both are present and a qdbus tool exists; if the dialog never answers or a D-Bus call fails, that step and all later ones fall back to text rather than losing the message.

## The Go port

`go/` holds a port of the same installer in Go: `go/cmd/megabonk-installer` builds one
cgo-free binary per platform. The one external module is MyGo (`github.com/egoist/mygo`),
used only for the progress window below, and `task installer:verify-static` fails if any
other direct dependency appears or if a Linux binary needs anything at load time beyond glibc. It is a companion to the Python reference, not a replacement: `install.sh`
still runs `scripts/player_installer`, the player package zip carries no Go binary, and the
binaries land in gitignored `.tools/installer/`.

```sh
task installer:build            # cross-compile into .tools/installer
task installer:test             # gofmt check, go vet, go test
task installer:verify-static    # CGO off, MyGo the only module, glibc-only load deps
task installer:parity           # both installers over the same scenarios
```

Targets are `darwin/arm64`, `linux/amd64` and `windows/amd64`. `linux/arm64` is left out on
purpose: the game and its Proton prefixes are x86_64, so an arm64 Linux player would run the
installer and never the mod. The Windows binary is executed in a Windows 11 Docker guest
against the Python reference on the same guest (see below).

Windows path handling has one rule: `resolve` answers in slash-separated form on every OS.
`filepath.Abs` and `filepath.EvalSymlinks` return backslash paths there, and any comparison
that mixes them with the slash-separated install paths misclassifies safe zip members as
escaping the game directory. The `plan` and `steam` resolve seams take injectable
abs/toSlash/eval so tests pin this without a Windows host; a guest run first caught the leak.

### The parity contract

The two implementations agree **semantically**, not byte for byte:

- **Exact**: exit codes; the installed, repaired and removed file trees (every path and
  content digest under the game directory and the prefix); the install record compared as
  parsed JSON, so key order and the `null` spelling of an absent launch option are free.
- **Anchored**: refusal, discovery and help lines must name the same path, registry key or
  flag and the same stable verb phrase — `no usable Proton prefix at <path>`, `pass --prefix
  <path to the pfx directory>`, `no wine binary found in the Proton tools under <lib>`, the
  `Steam clients considered:` / `Libraries searched:` / `Libraries skipped:` blocks with
  their `— retry with --library <path>` hints, and the numbered `N/M label` progress lines.
  Quoting style is free: Go may print `"%q"` or a codec error where Python prints `!r`.
- **Not compared**: `--help` and any other argparse-rendered text. Go's flag package cannot
  reproduce argparse's wrapping and it is not worth a formatter for it.

`tests/test_installer_parity.py` is the Go test suite of record. It builds a fixture tree
twice, under `python/` and `go/`, drives the same argv list through `python -m
player_installer` and the host-native Go binary, and compares exit codes, both streams, both
trees, and both records; scenario anchors then pin the phrases that must survive in either
run. Fixture paths, timestamps and the program name are normalised away (`<ROOT>`, `<TIME>`,
`<PROG>`) — the one thing two installers named differently cannot share is their own name.

Runs are hermetic by construction. `MEGABONK_MOUNT_ROOTS` replaces the removable-media scan
list (empty scans nothing) so a maintainer's mounted library cannot turn a "not found"
scenario into an install, and each fixture home carries a `local-overrides` file with no
grants, which is the source `flatpak_granted_paths` prefers, so the host's `flatpak` CLI is
never asked. Go unit tests cover only what is awkward to reach through a subprocess — path
arithmetic, the VDF and registry parsers, the flag seam above — rather than mirroring
`tests/test_player_installer_*.py` one for one.

### Progress window

The Go binary reports progress in a MyGo native-UI window — a checklist of the plan's steps (pending circle, spinner on the running step, green check when done, red cross on the step that failed), a collapsible Details log and Cancel and Install buttons — drawn with GTK 3 on Linux, Metal on macOS and Direct3D 11 on Windows. It never uses MyGo's webview mode, so WebKitGTK is never loaded. The selection order is the window, then plain numbered text; kdialog, zenity and yad are not used by the Go binary (the Python reference keeps its dialog backends).

On Linux the window needs a display (`DISPLAY` or `WAYLAND_DISPLAY`) and GTK 3, which the desktops players run already carry; GTK is `dlopen`ed at run time, so the binary itself loads only glibc and nothing depends on GTK being installed. `--no-gui`, `--non-interactive`, `MEGABONK_NON_INTERACTIVE=1`, `--json`, no display, or an app that cannot start (missing GTK) all give the text reporter, with `N/M label` lines, a closing message that starts with a capital letter, and the same exit codes.

The window opens on a prompt — "Install Megabonk Levels" or "Uninstall Megabonk Levels" — listing every step the plan will take, with Cancel and Install buttons, and nothing is touched until Install is pressed. Cancel or closing the window at the prompt exits 1 with "nothing was changed". There is no terminal check: a double-click launch gets the window, and scripted runs opt out with the variable or flags above.

After a run the window stays open with the result and a Done button, so a double-click launch does not lose the outcome. A failure marks the failing step with a red cross, shows the error and opens Details. The Details log holds the step lines and everything the installer would print on stdout. After a successful install that needs a Steam launch option, the window shows it with a Copy button. Cancel closes the window once the executor has stopped.

Cancel, or closing the window, once the run has started is only a request: the executor checks it between actions, never mid-copy. A cancelled install writes a partial install record for the actions already done and runs the normal record-driven uninstall, so the game directory returns to its prior state. A cancelled uninstall stops between steps and does not roll back. `MEGABONK_UI_STEP_DELAY` (a Go duration such as `2s`) pauses after each step so a person or a script can press Cancel mid-run; it is unset in normal use. On Windows MyGo logs `drawing without the GPU` lines to stderr when Direct3D 11 cannot create a swap chain (a VM or a service session), so stderr is not empty there even though stdout matches the text reporter. Packaging through `mygo build -platform` and its `.deb`/desktop-entry output was evaluated and not adopted; the binaries still come from plain `go build`.

## What is verified, and what is not

Verified offline, on macOS, against a synthetic Windows-layout game directory and a synthetic `steamapps/compatdata/<appid>/pfx` prefix:

- package assembly, manifest round-trip through `load_manifest`, and `verify_package` clean on a real package built from the real vendored archives;
- the full install → `--check` (no drift) → `--uninstall` lifecycle in both `gamedir` and `prefix` modes, leaving the game's own files and an untouched `UserData` behind;
- `version.dll` recorded as `via: registry` with `user.reg` actually carrying the key, and cleared on uninstall;
- refusal of a native-Linux game directory with exit 4;
- every plan, prefix-selection, VDF-parsing, Steam-discovery and manifest rule under `tests/test_player_installer_*.py` and `tests/test_build_player_package.py`.

The `install.sh` wrapper is checked apart from the game-directory fixtures: `sh -n` parses it, and the version gate was exercised against stub interpreters reporting versions above and below the floor — the floor run reaches the bundled module and `--help` prints, an older one is refused with exit 1, the found version, and the `--python` hint, and a `--python`/`MEGABONK_PYTHON` path that cannot run is refused with exit 2 naming it. The built wrapper also runs end to end under a mise interpreter at exactly the floor version where one is installed locally.

Verified on the AlmaLinux 10.2 maintainer host, against its real Flatpak Steam with the whole root relocated to a data disk: the distributed zip's sha256 survived the transfer and `install.sh` runs the bundled module from any directory on the host's system `python3` 3.12.15 with a bare `PATH=/usr/bin:/bin` — no mise, nothing installed — where an earlier 3.13 floor had refused that interpreter; `--python` and `MEGABONK_PYTHON` honour an explicit interpreter and refuse a dead path with exit 2; discovery finds the relocated root through its Flatpak grant, reports the granted path, skips the unmounted library that `libraryfolders.vdf` still lists, and stops with exit 4 and the Windows-build steps on the native install; `--uninstall` with no record leaves the game's `Mods` alone; and on that host's KDE session the progress dialog is a real kdialog driven over D-Bus — value read back from the live dialog as 40 at 2/5 and 100 at 5/5, closed cleanly — while the same call with no session bus picks plain text.

Verified on the CachyOS Proton host: the player-package install and `--check`,
Windows .NET 6 resolving inside the active home-library prefix while the game
lives on SD-card storage, the DLL override recorded as `via: wine`, and a fresh
launch logging the mod-initialized marker. The live prefix also exposed Wine's
timestamped registry section headers, now covered by regression tests. See
[gamepadui.md](gamepadui.md) for the measured workflow.

That host now also carries the clean-install proof itself: uninstalling a previous
install to a vanilla tree, installing the distributed 0.4.2 package with the
documented pinned flags, `--check` reporting a match, and a Steam launch whose fresh
`MelonLoader/Latest.log` shows `Assembly Generation Successful!`, `1 Mod loaded.`
and `[MegabonkLevels] MegabonkLevels mod initialized.` with Bootstrap resolving
`hostfxr.dll` under the vendored prefix runtime — prefix mode proven end to end
without any development leftovers beside the game. The launch initially did nothing
because a Steam Cloud save-conflict dialog was pending; see
[gamepadui.md](gamepadui.md) for the three launch traps that cost time there.

The Fedora player box carries the matching proof for auto-discovery: uninstalling
its development install to a vanilla tree, then running the distributed package's
`install.sh` with **no flags at all** against a real single library that holds an
unrelated Il2Cpp title sorting before Megabonk — discovery picked Megabonk through
the appmanifest and the library's own prefix. `--check` matched, and with Steam
stopped the game launched directly under Proton through the offline Steamworks
stub (the pressure-vessel `_v2-entry-point --verb=waitforexitandrun` chain, Proton
Experimental, `XAUTHORITY` pointed at the desktop's Xwayland cookie) to the same
three markers, stable over three minutes of mod telemetry, then a clean TERM
shutdown.

The four library layouts the discovery code has to survive are run through both
implementations in containers as well as fixtures: a single library holding Megabonk
beside an unrelated Il2Cpp title that sorts first, the same library with no Megabonk
at all, the game on removable media with the live prefix in the home library, and two
other libraries each with a usable prefix. Each case runs the full
install → `--check` → drift → repair sequence as a non-root user in `fedora:42` and
`ubuntu:24.04` (no network, `HOME` and the Steam root inside the mounted tree), and is
compared to the Python reference on the host for exit codes, stdout, stderr and the
installed tree. The decoy keeps its own digest through every install, the report names
the Il2Cpp install it refused with its reason, the SD-card install writes the .NET
runtime into the home library's prefix and says so, and the two-prefix case prints both
candidates with the `--prefix` hint and falls back to `gamedir` mode until `--prefix`
picks one.

The download path is exercised against the real vendors, not just fakes: both pinned
archives — the GitHub MelonLoader release and the dotnetcli .NET 6 runtime — download
through their cross-host redirects with digests matching the pins, a real GitHub 404
reads as a missing asset, plain http and an off-list redirect host are refused, and a
404 leaves nothing in the cache; a cold-cache `--allow-download` rebuilds the whole
package from scratch.

The fleet also includes Fedora 42 with GNOME Wayland, Intel Arc graphics and a
gamescope + Steam gamepadui launcher. Its verified setup includes switching to
Windows depot `3405342` through Steam's GUI and selecting DX11 (confirmed in the
active prefix's `Player.log`). This is not yet evidence of a wiped player-package
install with the mod loaded. Native Linux loader installation is out of scope;
the AlmaLinux host supplies Flatpak discovery and KDE progress evidence only.

The Go binaries are exercised beyond the parity host. `linux/amd64` runs the full
lifecycle — install, `--check` no-drift, drift repair with exit 10, uninstall — on
`ubuntu:24.04`, `fedora:42` and the SteamOS-based `thevakhovske/holoiso` image with
identical exit codes, streams, installed and final trees, and install record; none of
those images ships `python3`, `python`, `go`, `pip` or `pip3`, and a `FROM scratch`
image holding nothing but the binary and the fixture tree — 46 filesystem entries, no
shell, no interpreter — runs the same lifecycle with the same exits, so the
no-interpreter claim is measured, not inferred. `windows/amd64` runs the same lifecycle
in the dockurr/windows Windows 11 guest and matches a `python -m player_installer`
reference run through the same steps on the same guest — the reference is compared
per platform, since `windows_path` keeps an existing drive letter and only prefixes
`Z:` for drive-less paths, so the `DOTNET_ROOT` launch option legitimately differs
between a Linux host run and a native Windows run. On the AlmaLinux maintainer host's
real layout (Flatpak Steam with the root relocated to `/media/steam`, the stale
unmounted `/mnt/games/GameLibrary/Steam` entry still in `libraryfolders.vdf`, and the
native install present) the Go binary prints byte-identical output to the Python
reference, including `Flatpak Steam may only read: /media/steam` and the exit-4
Windows-build refusal.

Still pending:

- what a Steam update or "verify integrity of game files" does to the loader files in the game directory, which decides whether re-running after an update is ever needed beyond the build warning;
- the printed game-directory `DOTNET_ROOT` launch option working when Steam actually applies it (both live proofs use prefix mode);
- the persisted `local-overrides` file as the source of the Flatpak grants — the real host went through `flatpak override --show`, which is the other of the two paths in `flatpak_granted_paths`;
- the zenity and yad dialog paths — the verified host has neither installed, so those branches run only in tests (the kdialog-over-D-Bus path above is the one with desktop evidence);
- Steam's own behaviour around the download, including whether the Windows build needs the "Only download on my OS" untick on a given Steam version.
