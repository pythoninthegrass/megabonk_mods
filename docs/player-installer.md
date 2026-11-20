# Player installer

**Legacy reference:** the MelonLoader-only runtime and its vendored player
package are no longer built or shipped. The current BepInEx installer installs the
mod, levels and packs from the site and Thunderstore at run time, so its
distributable carries only the binary and a README. Use the
[player guide](player-guide.md) and [Thunderstore package](thunderstore.md) for
Megabonk Level Editor; `task package:linux`, `package:windows` and `package:macos`
now build that thin zip.

The player-facing download: a folder a player unzips and runs `./megabonk-installer` in, which installs the level editor mod, the levels and the packs they need from the site and Thunderstore at run time. This doc is the contract between the two halves — the **package** the build produces and the **installer** that consumes it — plus the Linux-specific behaviour that contract cannot express.

The installer is one static Go binary per platform, built from `go/` by `task installer:build` and shipped inside the package, so a player needs nothing else: no Python, no uv, no repo checkout, no .NET SDK, no Wine installation. The package builder and verifier (`scripts/installer_package.py`, `task package:check`) are Python and write a zip holding exactly the installer binary and a README.

## Linux player setup

Use the **Windows game under Proton/Wine**, not the native Linux build. In Steam,
open Megabonk's Properties → Compatibility and select Proton, then wait for the
Windows download to finish. Selecting Proton in the GUI triggered the depot
switch on Fedora; editing Steam's configuration alone did not. Launch vanilla
once to create the prefix, choose **DX11 - Recommended**, then quit the game
before installing. `-force-d3d11` in Steam's Launch Options pins that renderer.

Unzip the installer and run `./megabonk-installer`.
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
cd /path/to/unzipped-installer
G=/media/sdcard/SteamLibrary/steamapps/common/Megabonk
P="$HOME/.local/share/Steam/steamapps/compatdata/3405340/pfx"
./megabonk-installer --game-dir "$G" --prefix "$P" --wine-override registry
./megabonk-installer --game-dir "$G" --prefix "$P" --wine-override registry --check
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
`./megabonk-installer --game-dir "$G" --prefix "$P" --uninstall` removes recorded
installer-owned files, not unrelated mods or saves. Packs must contain Windows
bundles even though the host OS is Linux.

## Package layout

```text
megabonk-levels-<mod>-ml<melonloader>-linux/
├── megabonk-installer            the Go installer for this platform (install.exe on Windows)
├── manifest.json                 the contract, described below
├── vendor/                       vendor archives, named exactly as the manifest names them
├── content/levels/               bundled .mblevel.json files and their sidecar thumbnails
└── content/packs/<pack-id>/      bundle + manifest.json (+ attachments.json) per pack
```

`megabonk-installer` is the only entry point a player needs: a static binary, so there is no interpreter to choose and nothing to put on a path. It takes the levels to install as arguments and finds everything else itself — the mod and its loader from Thunderstore, the level files from `megabonkmod.party`. The builder copies the platform's binary from `.tools/installer/` and marks it executable; a zip build without `--installer-binary` fails, and a missing file is a missing input that points at `task installer:build`.

## What ships in the zip

`task package:linux`, `package:windows` and `package:macos` write a zip holding exactly two entries: the platform installer binary and a `README.txt` that says how to run it on that platform and what the installer fetches. There is no manifest, no `vendor/`, no bundled mod DLL, level or pack: the installer resolves all of that at run time, so the distributable is the same size and shape regardless of what content the site offers. `task package:check` reads a built zip and refuses anything but those two entries.

## What the installer fetches

The distributable ships no `manifest.json` and no `vendor/` archives. Under the retired MelonLoader-era package a `manifest.json` with `schema` `megabonk-player-package/1` listed the vendored MelonLoader and .NET archives and the mod files, each with a sha256, and the installer refused anything it could not use before copying. None of that ships now. The installer resolves everything at run time instead: the mod and its BepInEx loader pack from Thunderstore, and the levels and their packs from `megabonkmod.party`, verified against the digests and file lists the site and Thunderstore return for the exact version named. The download rules, the cache under `~/.cache/megabonk-levels`, and the pack validation are described under "Installing the mod from Thunderstore" and "Levels and packs from the command line" below.

### Where content lands

`go/internal/content` is the one place that knows the layout the mod's loaders read, and it is the only writer of those paths:

| Content | Destination | Loader that reads it |
| --- | --- | --- |
| Level | `UserData/Levels/<slug>.mblevel.json` | Map Selection lists every titled `.mblevel.json` in the folder. |
| Cover | `UserData/Levels/<slug>.png` | `LevelThumbnailSidecar` finds the image named after the level's base name. |
| Biome icon | `UserData/Levels/<slug>.biome.png` | The same lookup with its `.biome` stem suffix. |
| Pack | `UserData/LevelPacks/<id>/{<id>,manifest.json,attachments.json}` | `PackPrefabs` loads one folder per pack id; see [asset-bundles.md](asset-bundles.md). |

`InstallLevel` takes the slug, the level file, and optionally the cover and biome image, and creates any missing `UserData` folder on the way. The images are written under the slug-derived names whichever file names they arrived with, because the lookup is by the level's base name and nothing in the level file points at a picture. An existing level file of the same name is replaced and the replacement is reported. Images left from an earlier install of that level which this install does not carry are removed, so a re-install cannot serve a stale cover, and the removal is reported with it.

`InstallPackFromZip` unpacks a pack archive into `UserData/LevelPacks/<id>/`. Nothing is written until the archive as a whole is proven: every member name is vetted against the pack folder, so a name that climbs out of it, uses a drive letter or a backslash separator, or is absolute is refused outright; each member is then read through and checked against the size and checksum its header declares. The unpacked folder must pass `ValidatePackSource`, the same rules the game applies, before the install is accepted. A refusal leaves no pack folder behind, and an accepted install replaces the folder wholesale rather than merging into it. Members outside the `<id>/` folder, and inside it but not a manifest, attachments sidecar or bundle, are not installed. The check runs before the destination is touched, so a truncated or tampered download never replaces a pack folder the game is already showing.

Zip extraction lives in `go/internal/zipx`. Its `Extract` is what a fetched loader or pack archive is unpacked with, and `ExtractMember` is the shared member copy the pack install builds on, so zip-slip protection is written once rather than per caller. `Extract` walks every member name against the resolved destination before writing any of them, which is why a run that refuses leaves nothing behind, and `ExtractMember` caps the copy at a positive limit so a member whose declared size lies cannot fill the disk.

`task package:check` runs `scripts/installer_package.py`, which reads a built distributable zip and reports a message per problem — an entry other than the platform's installer binary and `README.txt`, or either one missing — and exits 1 on any of them.

## Install record

After a successful install the installer writes `MegabonkLevels.installer.json` into the game directory, schema `megabonk-levels-install/2`: package id, `installed_at`, the game directory, and what is installed — `mod_version` and `bepinex_version`, `levels` as a code-to-entry map naming the level file and the cover and biome image beside it, and `packs` as an id-to-version map holding each pack folder and the files in it. `game_buildid` is the build the package was verified against; `installed_game_buildid` is the build Steam's appmanifest reported when the installer ran, or `null` when it reported none. Both keys are optional, so records written before they existed still load under the same schema. The `files`, `runtime` and `dll_override` entries carry the loader-side state the plan still writes; the loader install owns them, not the content install.

That one file drives both `--check` and `--uninstall`. Uninstall is deliberately record-driven rather than a glob: it removes what it recorded placing and leaves anything it did not put there alone, so a player's own `Mods/` entries, saves, and `UserData` survive.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Done, nothing needed. |
| 1 | Error (archive checksum mismatch, I/O, a step that failed and rolled back). |
| 2 | Usage — no level was named, an invalid choice was given, or the platform needs `--prefix` and none was passed. |
| 3 | Nothing found to work on: no Steam install, no game directory. |
| 4 | The game directory is a build this installer will not touch, i.e. the native Linux build. |
| 10 | `--check` found content the game does not have yet. A script can treat 10 as "install it" and 0 as "already installed". |

## Installer contract

Every platform's installer — the same Go binary, built as `megabonk-installer` for Linux and macOS and `install.exe` for Windows — implements the steps below in this order, and a player's experience differs between platforms only in how the installer is launched. The sections after this one describe the platform specifics; this one is the single list they must agree with, and the Go tests under `go/internal` hold the installer to it.

1. **Classify the build.** Only the Windows build is supported, on every platform. This happens before the network is used, so a native Linux game is refused without a download and a player is not kept waiting: exit 4 with the steps for switching to the Windows build.
2. **Read the inputs.** Each positional `LEVEL` is a share code, a `megabonkmod.party` level link, a level's stored file name, or a `.mblevel.json` path on disk, and each is resolved to its hosted record before anything else is judged — so a bad file or an unknown code reaches the player rather than a complaint about a folder. Two spellings of one level are one install, and a local file is preferred over the site's copy of the same name.
3. **Resolve the prefix and platform.** A `--prefix` with `drive_c/` is usable; one named but without it is a Steam install that has not been launched under Proton yet, which downgrades to the loader's own runtime with a warning rather than refusing. Nothing usable at all, where the platform needs a prefix, is a usage error naming the flag.
4. **Name the game build.** Read the installed build id from the library's `appmanifest_3405340.acf` and print it, so a player reporting a problem has it in front of them. Nothing is pinned to one build, so this is an observation rather than a verdict: an untested build still installs. The id goes into the install record.
5. **Plan it.** The levels, their sidecar images, the packs they need, and the optional mod become a list of steps. A pack several levels need appears once; a pack already installed at the version every level asks for is skipped; a pack the site does not host is a warning, not a failure, and the level still installs.
6. **Fetch into staging.** Every download and every content file is written into a staging folder the game cannot read. Nothing in the game directory changes while this happens, so a plan the player walks away from, cancels, or that fails halfway leaves the game exactly as it was: the run rolls back what it placed and reports what it could not restore.
7. **Commit the plan.** Staged files move into `UserData/Levels/` and `UserData/LevelPacks/` in the order the plan promised, replacing a pack folder whole so a pack that changed version keeps no stale bundle.
8. **Install the mod** from Thunderstore when asked for or when the game lacks one: the BepInEx loader pack, whose archive carries the .NET runtime under `dotnet/` beside the executable, and the plugin under `BepInEx/plugins/MegabonkLevels/`. Where a loader and plugin set are already in place but not this installer's, only the platform override is applied — a foreign install is never rewritten.
9. **Apply the `winhttp` override** where a Wine or Proton prefix needs it. Native Windows has none; a Proton run prints the Steam launch option instead of writing one.
10. **Write the install record**, which drives `--check` and `--uninstall`.
11. **Report** what was done and what was not, as numbered `N/M label` lines or a progress window. A failure exits nonzero with a message that says what to do.

### Re-running

A second run with nothing changed does nothing and says so, answering from the record alone. A run after something has gone missing or stale repairs only that: `--check` reports the content the game does not have and answers whether the mod is in place, exiting 10 when anything is missing and 0 when it is not. The level and pack archives are cached under `~/.cache/megabonk-levels`, so a repair reuses what was already fetched and verified rather than asking Thunderstore again; an install takes what the site offers now, into a folder of its own.

After a game update the answer is the same run again. The game build comparison in step 4 tells the player whether the package still matches the game and the repair covers any loader file that went missing; if the build differs and the mod stops loading, the fix is a newer package, which the warning says. Whether Steam's own update or file verification removes the loader files it did not install is not established here, and the game has not updated since February 2026, so no update has been observed; see [what is not verified](#what-is-verified-and-what-is-not).

### Uninstall

`--uninstall` is record-driven: it removes what the record says the installer placed, plus what the loader generates on first launch where the platform notes say so, and leaves a player's own plugins, preferences, levels and saves alone. With no record it removes nothing.

## Building a package

```sh
task package:linux
task package:linux MOD_VERSION=0.4.2
```

`task package:linux` builds the linux/amd64 Go installer through `installer:build` and writes `megabonk-installer-<version>-linux.zip` into `.tools/installer-dist/` (override with `OUTPUT`). The zip holds exactly the installer binary and a `README.txt`; the mod DLL, the levels, the packs and the loader are fetched by the installer at run time from the site and Thunderstore, so the build never touches Thunderstore, bundles no content, and needs no vendored MelonLoader or .NET archive. Set `SOURCE_DATE_EPOCH` for a byte-identical zip. `scripts/installer_package.py` writes the zip and `task package:check` verifies it: it fails on any entry other than the binary and the README, and each platform task runs it on what it just built.

Two choices are intentional:

- **The default is Bramblecrown Hill only.** The package tasks name `bramblecrown-hill.mblevel.json`, bringing its original selection illustration and biome icon, with no packs or music. See [Starter level](starter-level.md) for the content inventory, first-edit tutorial and packaged smoke test. `levels/` also holds development fixtures, so there is no directory-wide bundling. Explicit `LEVELS` and `PACKS` overrides still support local packages; the lower-level builder bundles only files named with `--level` and `--pack`. A `.local.mblevel.json` is skipped even when named. Matching thumbnail and `.biome` sidecars are ordinary hashed manifest files, installed beside the level, repaired by a rerun and removed with it on uninstall. Images that match no bundled level stay out.
- **Packs come from the site at run time**: each level's record names the packs it needs and their versions, and the installer fetches the pack zips laid out for `UserData/LevelPacks/`. Nothing about a pack is staged at build time; the download is what `ValidatePackSource` checks before an install is accepted.

The builder writes into a staging directory and swaps the finished zip in at the end, so a failure leaves the previous build untouched. The zip is deterministic — sorted entries, fixed timestamps, modes 0755 for the installer binary and 0644 for the README — so two builds of the same binary are byte-identical once `SOURCE_DATE_EPOCH` is pinned.

When a download does happen it goes through `scripts/asset_download.py`, the only code in `scripts/` that touches the network (a test pins that). The rules: https only, TLS 1.2 floor with certificate verification; the status is checked before the body is read, so a 404, a login or captive-portal page, or an empty body reads as a missing asset rather than a checksum mismatch, and nothing poisoned ever lands in the cache; the body is capped, and an archive whose digest does not match the manifest pin is refused before it is cached. Redirects stay on the original host except for an explicit CDN allowance — GitHub release assets hand off to `release-assets.githubusercontent.com` and dotnetcli to azureedge/microsoft hosts — so an off-list redirect is refused as a missing asset. `install_melonloader.py` uses the same fetcher. The `url` in a manifest entry stays provenance for the player side: the installer itself never downloads.

The zip is deterministic — sorted entries, fixed timestamps, modes 0755 for the installer binary and 0644 elsewhere — so two builds of the same inputs are byte-identical once `SOURCE_DATE_EPOCH` is pinned.

## Windows package

```sh
task package:windows
task package:windows MOD_VERSION=0.4.2
```

`task package:windows` builds the `windows/amd64` Go installer through `installer:build` and writes `megabonk-installer-<version>-windows.zip` into `.tools/installer-dist/`. The zip holds exactly `megabonk-installer.exe` and a `README.txt`. Windows players unzip it and run the exe: the installer discovers Steam through the registry, takes its levels and packs from the command line, and fetches the mod, loader and content from the site and Thunderstore at run time. It has no prefix, no `version.dll` override and no launch option; every write is inside the game directory. The BepInEx doorstop and its bundled .NET runtime arrive with the loader pack the installer fetches, not with the download.

On native Windows the installer finds Steam through `HKCU\Software\Valve\Steam` (then `HKLM\...\WOW6432Node\Valve\Steam` and the Program Files default) and reads `libraryfolders.vdf` for libraries on other drives. It has no prefix, no `version.dll` override and no launch option; every write is inside the game directory. MelonLoader's bootstrap otherwise installs .NET 6 machine-wide under Program Files on first launch, so the installer pre-seeds the vendored runtime into `MelonLoader/Dependencies/dotnet`, the path the loader itself uses; it then logs `Using HostFXR Path: <game>\MelonLoader\Dependencies\dotnet\host\fxr\6.0.36\hostfxr.dll` and runs no runtime installer. `--uninstall` also removes the files the loader creates at first launch (`UserData/Loader.cfg`, and `Plugins/`, `UserData/Levels`, `UserData/LevelPacks`, `UserData` when empty), so the game returns to vanilla while a player's own plugins, preferences and levels stay.

The first launch downloads Cpp2IL from GitHub and takes about 35 seconds, so it needs network access. The Windows flow has been verified in a software-rendered Windows 11 guest, not on real hardware.

## macOS package

```sh
task package:macos
task package:macos MOD_VERSION=0.4.2
APPLE_SIGNING_IDENTITY="<Developer ID Application identity>" NOTARY_PROFILE=<notarytool keychain profile> task package:macos
```

`task package:macos` builds the `darwin/arm64` Go installer through `installer:build` and writes `megabonk-installer-<version>-macos.zip` into `.tools/installer-dist/`. The zip holds exactly the bare `megabonk-installer` binary (no extension, mode 0755) and a `README.txt`; the mod, loader and content are fetched at run time. Only Apple silicon is built: no Intel Mac was available to test an `amd64` binary.

Megabonk has no macOS build, so the player runs the **Windows build under Wine** and the installer works inside that prefix. It does not install Wine, create a prefix or log into Steam: Steam and Megabonk must already be installed in a Wine prefix, and the game started once. The player runs `./megabonk-installer LEVEL...` from the unzipped folder.

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

The installer classifies the game directory before touching it (`gamebuild.Classify` in `go/internal/gamebuild`). `Megabonk.exe` plus `Megabonk_Data/` is the Windows build and the only supported one. A directory with `Megabonk.x86_64` is the native Linux build and the installer stops with exit 4 and instructions for switching to the Windows build through Steam Play, because MelonLoader 0.7.3 segfaults the native binary during Il2Cpp assembly generation and the upstream fix is not in a release. That is a hard refusal, not a warning: installing onto it would leave a player with a crashed game and no log.

### Finding Steam and the game

`go/internal/steam` looks for a Steam install under `$XDG_DATA_HOME/Steam`, `~/.local/share/Steam`, `~/.steam/root`, `~/.steam/steam`, the two Flatpak locations (`~/.var/app/com.valvesoftware.Steam/...`), and any Flatpak-granted path. A directory counts as a client when it has `steamapps/`. Library folders are read out of `config/libraryfolders.vdf` (`go/internal/vdf`, a read-only parser — the installer never writes VDF).

Game identity comes from `GameCandidates`, which offers every directory three searches thought might be Megabonk, in the order it should be trusted: the `installdir` in the library's own `appmanifest_3405340.acf`, then `steamapps/common/Megabonk` by name, then any other Il2Cpp install in `common`. The third tier exists because a copy moved out of its library keeps `GameAssembly.dll` and its data folder but loses the name. Acceptance never rests on that shape: a candidate is Megabonk only when it holds `Megabonk.exe`, `Megabonk.x86_64` or `Megabonk_Data/`, all three named by this game alone. `FindGameDir` takes the first accepted candidate; `--check` and the not-found report name what was rejected and why (`an Il2Cpp install (GameAssembly.dll) but no Megabonk.exe, Megabonk.x86_64 or Megabonk_Data/`), so a machine with another Unity/Il2Cpp title installed says so instead of installing into it.

Two more things make this sturdier than it looks:

- **A library on a detached drive** shows up as a configured root whose `steamapps` is gone. Those roots are skipped rather than reported as a missing game, and only when even the parent directory is missing.
- **Flatpak Steam can only read paths granted to it**, so granted paths from `flatpak override --show` (or the persisted `local-overrides` file) are read on every run and added as extra search roots. They also count as the Flatpak client itself when one of them holds `steamapps/`: a maintainer machine exists where the entire Steam root — `config/`, `userdata/` and `steamapps/` — was moved to a data disk, so no client is left at any default location, and the grants are the only way back to it. Without this, a game on a second disk is simply invisible to a Flatpak install.

### Which Proton prefix

Steam keeps the prefix at `<library>/steamapps/compatdata/<appid>/pfx` **in the library the game was installed to**, which is not always the one holding the game files after a move — the SD-card layout has the files on removable media and the live prefix in the home library. `FindPrefix` prefers the game's own library, and when that prefix has no `drive_c/` it takes the only other usable prefix among the libraries searched and prints `Proton prefix: <path> (Steam keeps it in that library, not beside the game)`. Two usable prefixes elsewhere is a guess, so nothing is chosen: both are printed with the `--prefix` hint, and the plan falls back to `gamedir` mode. A prefix passed with `--prefix` silences all of that reporting. `--check` names the prefixes it considered and why each was rejected (`no steamapps/compatdata prefix in this library`, `the prefix has no drive_c/: the game has never been launched under Proton in this library`).

### .NET placement and the launch option

The BepInEx loader pack carries its own .NET runtime under `dotnet/` beside the executable, so the installer ships and extracts no separate runtime and writes no `DOTNET_ROOT` launch option. Under plain Wine and CrossOver it applies the `winhttp` proxy override into the prefix; a Proton run prints the Steam launch option instead and the player pastes it.

### The winhttp override

BepInEx is reached under Proton and Wine by a `winhttp` = `native,builtin` DLL override, which makes the game load the loader's `winhttp.dll` proxy. `SetDllOverride` in `go/internal/proton` writes it through the Proton tool's own `wine` with `reg add` when that binary is findable (`via: wine`), and otherwise merges `Software\Wine\DllOverrides` into the prefix's `user.reg` (`via: registry`). `--wine-override off` skips it; `--wine-override wine` fails loudly when no wine binary exists instead of falling back.

The two routes are alternatives to the same end, so whichever one runs is recorded the same way and names the prefix it edited — that is what lets `--uninstall` clear a key the game folder itself says nothing about. A Proton run writes no prefix key at all: it prints the Steam launch option instead and the player pastes it.

A MelonLoader `version.dll` left by an older install is parked aside rather than deleted, and restoring it is part of uninstall.

### Levels and packs from the command line

Each positional `LEVEL` is a share code, a `megabonkmod.party` level link, or the path of a `.mblevel.json` file on disk, and a run installs exactly what it names — there is no bundled set to choose out of. The packs a level needs come with it: they are read off the level's record, fetched at the version that record names, and go through the member-name and content checks above, so a pack a player never mentions is still validated before anything is copied. Everything lands in the install record, which is what `--uninstall` works from.

### Progress reporting

The installer shows a native progress window when it has a display and falls back to numbered `N/M label` lines otherwise; the window is described under "Progress window" below. `--non-interactive`, `--no-gui` or `MEGABONK_NON_INTERACTIVE=1` force plain text for install and uninstall, even on a desktop. The environment setting also accepts `true`, `yes` and `on` (case-insensitive); empty, `0`, `false`, `no` and `off` leave automatic selection enabled. `--json` suppresses progress output and dialogs. No installer prompt reads stdin.

## The installer

`go/` holds the installer: `go/cmd/megabonk-installer` builds one cgo-free binary per platform. The one external module is MyGo (`github.com/egoist/mygo`), used only for the progress window below, and `task installer:verify-static` fails if any other direct dependency appears or if a Linux binary needs anything at load time beyond glibc. `task package:linux`, `package:windows` and `package:macos` each copy the matching binary into their package; the binaries themselves land in gitignored `.tools/installer/`.

```sh
task installer:build            # cross-compile into .tools/installer
task installer:test             # gofmt check, go vet, go test (part of task check)
task installer:verify-static    # CGO off, MyGo the only module, glibc-only load deps
```

Targets are `darwin/arm64`, `linux/amd64` and `windows/amd64`. `linux/arm64` is left out on purpose: the game and its Proton prefixes are x86_64, so an arm64 Linux player would run the installer and never the mod. The Windows binary is exercised in a Windows 11 Docker guest (see below).

### Gallery API client

`go/internal/site` is the installer's client for the gallery API, the package that turns what a player pastes into files it can install. It uses only the standard library, so MyGo stays the installer's one direct module dependency. The endpoints are the ones the site's own hooks serve, so `pocketbase/pb_hooks/levels.pb.js` and `packs.pb.js` are the authority on their behaviour and this section is the summary the installer side needs. Both download routes are served by those hooks rather than by PocketBase's own file serving, so a change to a hook is a change to the installer's contract.

The API location comes from `MEGABONK_API_URL`, defaulting to `https://api.megabonkmod.party`. A value with no scheme is taken as https, and a value carrying a path, query or fragment is refused rather than silently trimmed, so a mistyped override fails loudly instead of talking to the wrong place. Tests point the variable at an `httptest` server; nothing in the package names a host other than that default, which a test enforces by scanning the package's own sources, so `go test` can only ever reach a local server or a closed loopback port.

A player's input is normalised by `NormalizeCode`, which accepts a share code in any case and with or without its hyphens, a `megabonkmod.party/l/<code>` share link, and a `/levels/view/?code=<code>` link, with or without a scheme and with extra query parameters. All three land on the same canonical upper-cased code, which is how the server stores it. The host must be exactly `megabonkmod.party` (or `www.` with it), so a lookalike such as `megabonkmod.party.evil.example` is rejected, and anything that is not one of the three shapes is refused with a message naming all three. A code's alphabet excludes I, L, O and U, so a code a player reads back correctly is a valid code.

`LookupLevel` reads one record through `GET /api/collections/levels/records?filter=(code='<CODE>')` and returns the title, the record's stored level file name, the cover and biome image URLs under `/api/files/levels/<id>/<file>`, and the required packs as a pack id to version map. `Slug` reproduces the site's `slugify` (`pocketbase/pb_hooks/level_lib.js`), the rule that names the level file on disk; the record's own file name wins where the two disagree, because a title can be renamed after upload. An empty result page and a 404 or 403 answer mean the same thing to the player — `NotFoundError`, worded "level not found" — which is also what a hidden level looks like, so the installer never reveals that a hidden level exists. A share code's capitalisation never matters either, because codes are upper-cased server-side before they are stored.

A level file is fetched only through `GET /api/l/<code>/download`, never the raw file URL, because that route is what bumps the download count; it answers 302 and the client follows it within the API host and refuses a redirect off it. A pack is fetched through `GET /api/p/<id>/download?platform=windows&version=<v>`, which returns the zip laid out for `UserData/LevelPacks/`. Pack ids are validated against the site's own pattern before the request, so a malformed id never reaches the server.

Three failures stay distinct, because the player's next action differs for each. A 404 from the pack route is `PackNotHostedError`: the site does not offer that version, so asking its maker is the way forward and retrying is not. A connection failure is neither of those, so an offline player is never told a pack is unhosted. A 429 is `RateLimitedError`, which reads `Retry-After` and tells the player to wait that many seconds and retry; `/api/l/` is limited to 30 requests per 60 seconds. A response that is neither of those carries the server's own message when it sent one, since a PocketBase validation message is more useful than a bare status.

Windows path handling has one rule: `resolve` answers in slash-separated form on every OS.
`filepath.Abs` and `filepath.EvalSymlinks` return backslash paths there, and any comparison
that mixes them with the slash-separated install paths misclassifies safe zip members as
escaping the game directory. The `plan` and `steam` resolve seams take injectable
abs/toSlash/eval so tests pin this without a Windows host; a guest run first caught the leak.

### Installing the mod from Thunderstore

`go/internal/modinstall` is the Thunderstore path, separate from the offline package path in `plan`: it resolves the latest Megabonk Level Editor release, installs the BepInEx loader pack it depends on beside `Megabonk.exe`, puts the plugin set under `BepInEx/plugins/MegabonkLevels/`, and applies the `winhttp` proxy override where the platform needs one. `go/internal/content/bepinex.go` holds the file-level half (what a loader install writes and what the record has to account for), `go/internal/proton/bepinex.go` the `winhttp` override naming, and `go/internal/thunderstore` the download half.

Nothing is fetched before the run knows both versions it is installing, and nothing is written to the game directory before both archives are verified. The order is resolve, pin, fetch, unpack-and-check, then write.

**Verification.** The loader pack archive is always checked against a SHA-256: a `--bepinex-sha256` the caller passes wins, otherwise the built-in table in `thunderstore.bepinexPins` has to know the version Thunderstore named, and an unknown version is refused before a byte is downloaded. There is no path that installs an unverifiable loader pack. The mod's own archive is the hard case, because Thunderstore publishes no checksum for any package: it is checked against a `--mod-sha256` when the caller holds one, or against the digest the install record kept for that exact version when the run is repairing its own install, and otherwise fetched fresh and proven by its contents — the archive has to unpack to the complete plugin set (`MegabonkLevels.Mod.dll`, `NLayer.dll`, `NLayer.LICENSE.txt` under `BepInEx/plugins/MegabonkLevels/`) inside a temporary folder before any of it reaches the game directory, and the digest it turned out to carry is recorded so the next repair can check the cache against it. An archive in the cache with nothing to check it against is never reused: cache names come from the version alone, so a release republished under the same version would otherwise answer from its old bytes forever.

**The whole run is one transaction.** Everything the run places is removed again if it is cancelled or fails partway, and every file it overwrote is restored from a backup taken before the write, including `doorstop_config.ini` a player edited. Files it replaces are restored rather than deleted, folders are collapsed only once nothing the installer did not place is left in them, and a `winhttp` override it set is cleared from the prefix even when the run is walking away with nothing installed. What a rollback could not put back is named in the error rather than swallowed, because a game directory left half-changed is the player's problem to know about.

**Foreign installs are left alone.** The install record is the only thing that can tell this installer's files from a mod manager's, since the files themselves look identical. Without a recorded loader install, uninstall removes nothing: an unrecorded `BepInEx/` belongs to a mod manager or to the player. A `version.dll` is parked as `version.dll.bak` (and restored on uninstall) only when a `MelonLoader/` folder sits behind it, so a proxy nobody can account for is refused by name rather than moved aside.

**Per platform.** Wine and CrossOver get `winhttp=native,builtin` written into the prefix — through `wine reg add` when a wine binary is supplied, falling back to the registry writer in `go/internal/proton` when it is not, with the run reporting which one it used. Proton gets the Steam launch option through the existing `ShowLaunchOption` Copy UI, because Proton's prefix is not something to edit. Native Windows needs neither, and no prefix at all. Detection (`Detect`, and `DetectAgainst` when a client is available to name the current release) reports the installed mod and loader versions from the record and whether the files are actually present, which is what the GUI checkbox defaults from.

### Test seams

Go tests are hermetic by construction. `MEGABONK_MOUNT_ROOTS` replaces the removable-media scan list (empty scans nothing) so a maintainer's mounted library cannot turn a "not found" scenario into an install, and a `local-overrides` file with no grants is the source `flatpak_granted_paths` prefers, so the host's `flatpak` CLI is never asked. Go unit tests cover what is awkward to reach through a subprocess — path arithmetic, the VDF and registry parsers, the flag seam above.

### Progress window

The Go binary reports progress in a MyGo native-UI window — a checklist of the plan's steps (pending circle, spinner on the running step, green check when done, red cross on the step that failed), a collapsible Details log and Cancel and Install buttons — drawn with GTK 3 on Linux, Metal on macOS and Direct3D 11 on Windows. It never uses MyGo's webview mode, so WebKitGTK is never loaded. The selection order is the window, then plain numbered text; kdialog, zenity and yad are not used.

On Linux the window needs a display (`DISPLAY` or `WAYLAND_DISPLAY`) and GTK 3, which the desktops players run already carry; GTK is `dlopen`ed at run time, so the binary itself loads only glibc and nothing depends on GTK being installed. `--no-gui`, `--non-interactive`, `MEGABONK_NON_INTERACTIVE=1`, `--json`, no display, or an app that cannot start (missing GTK) all give the text reporter, with `N/M label` lines, a closing message that starts with a capital letter, and the same exit codes.

The window opens on a prompt — "Install Megabonk Levels" or "Uninstall Megabonk Levels" — listing every step the plan will take, with Cancel and Install buttons, and nothing is touched until Install is pressed. Cancel or closing the window at the prompt exits 1 with "nothing was changed". There is no terminal check: a double-click launch gets the window, and scripted runs opt out with the variable or flags above.

After a run the window stays open with the result and a Done button, so a double-click launch does not lose the outcome. A failure marks the failing step with a red cross, shows the error and opens Details. The Details log holds the step lines and everything the installer would print on stdout. After a successful install that needs a Steam launch option, the window shows it with a Copy button. Cancel closes the window once the executor has stopped.

Cancel, or closing the window, once the run has started is only a request: the executor checks it between actions, never mid-copy. A cancelled install writes a partial install record for the actions already done and runs the normal record-driven uninstall, so the game directory returns to its prior state. A cancelled uninstall stops between steps and does not roll back. `MEGABONK_UI_STEP_DELAY` (a Go duration such as `2s`) pauses after each step so a person or a script can press Cancel mid-run; it is unset in normal use. On Windows MyGo logs `drawing without the GPU` lines to stderr when Direct3D 11 cannot create a swap chain (a VM or a service session), so stderr is not empty there even though stdout matches the text reporter. Packaging through `mygo build -platform` and its `.deb`/desktop-entry output was evaluated and not adopted; the binaries still come from plain `go build`.

## What is verified, and what is not

Automated, in `task check`:

- Go: `task installer:test` runs gofmt, `go vet` and the unit tests under `go/internal`: plan, prefix selection, VDF and Steam discovery, manifest rules, level and pack installs, the shared zip extraction, the install record's round trip, record-driven uninstall, cancellation and the text reporter. Every test works in a temporary directory and none reaches the network.
- Python: `tests/test_installer_package.py` covers the thin zip builder and its check for all three platforms: the entries and their modes, the README text, deterministic output under `SOURCE_DATE_EPOCH`, and `package:check` refusing any entry other than the binary and the README.

Run against the real binaries when the installer was ported, using the Python installer it replaced as the oracle (it is no longer in the repository):

- `linux/amd64` runs the full lifecycle — install, `--check` no-drift, drift repair with exit 10, uninstall — on `ubuntu:24.04`, `fedora:42` and the SteamOS-based `thevakhovske/holoiso` image, and in a `FROM scratch` image holding nothing but the binary and the fixture tree (no shell, no interpreter), so the no-interpreter claim is measured rather than inferred.
- The four library layouts discovery has to survive ran as a non-root user in `fedora:42` and `ubuntu:24.04` with no network: a single library holding Megabonk beside an unrelated Il2Cpp title that sorts first, the same library with no Megabonk at all, the game on removable media with the live prefix in the home library, and two other libraries each with a usable prefix. The decoy keeps its own digest through every install, the report names the Il2Cpp install it refused with its reason, the SD-card install writes the .NET runtime into the home library's prefix and says so, and the two-prefix case prints both candidates with the `--prefix` hint and falls back to `gamedir` mode until `--prefix` picks one.
- `windows/amd64` runs the same lifecycle in the dockurr/windows Windows 11 guest. `windows_path` keeps an existing drive letter and only prefixes `Z:` for drive-less paths, so the `DOTNET_ROOT` launch option legitimately differs between a Linux host run and a native Windows run.
- On the AlmaLinux 10.2 maintainer host's real layout (Flatpak Steam with the root relocated to `/media/steam`, the stale unmounted library still in `libraryfolders.vdf`, and the native install present) the installer reports `Flatpak Steam may only read: /media/steam`, finds the relocated root through its Flatpak grant, skips the unmounted library, and refuses the native build with exit 4 and the Windows-build steps.
- The download path runs against the real vendors: the BepInEx loader pack and the level and pack archives download through their cross-host redirects with digests matching their pins, a real 404 reads as a missing asset, plain http and an off-list redirect host are refused, and a 404 leaves nothing in the cache.

Live-game evidence below was gathered with the Python installer that this one replaced, and has not been repeated with the Go binary:

- On the CachyOS Proton host, the player-package install and `--check`, Windows .NET 6 resolving inside the active home-library prefix while the game lives on SD-card storage, the DLL override recorded as `via: wine`, and a fresh launch logging the mod-initialized marker. See [gamepadui.md](gamepadui.md) for the measured workflow and the three launch traps that cost time there.
- On the Fedora player box, auto-discovery with no flags against a real single library holding an unrelated Il2Cpp title that sorts before Megabonk: discovery picked Megabonk through the appmanifest and the library's own prefix, `--check` matched, and with Steam stopped the game launched under Proton through the offline Steamworks stub to the same three markers (`Assembly Generation Successful!`, `1 Mod loaded.`, `[MegabonkLevels] MegabonkLevels mod initialized.`), stable over three minutes of mod telemetry.
- On an Apple silicon Mac with plain Wine, see "macOS package" above.

Still pending:

- A live Steam launch from a Go-installed Linux package, now that the Go binary is the only installer.
- What a Steam update or "verify integrity of game files" does to the loader files in the game directory, which decides whether re-running after an update is ever needed beyond the build warning.
- The printed game-directory `DOTNET_ROOT` launch option working when Steam actually applies it (both live proofs use prefix mode).
- The persisted `local-overrides` file as the source of the Flatpak grants; the real host went through `flatpak override --show`, which is the other of the two paths.
- Steam's own behaviour around the download, including whether the Windows build needs the "Only download on my OS" untick on a given Steam version.
