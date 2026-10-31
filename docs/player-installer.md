# Player installer

The player-facing download: a folder a Linux player unzips and runs `./install.sh` in, which installs MelonLoader, the MegabonkLevels mod, the .NET 6 runtime it needs, and any levels or packs the package carries. This doc is the contract between the two halves — the **package** the build produces and the **installer** that consumes it — plus the Linux-specific behaviour that contract cannot express.

Everything here is Python standard library only, on both sides. The installer runs as `python3 -m player_installer` from a copy of `scripts/player_installer/` that travels inside the package, so a player needs Python 3.13 or newer and nothing else: no uv, no repo checkout, no .NET SDK, no Wine installation. That floor is the repo's own pin, and `install.sh` enforces it rather than just advertising it — the modules import `datetime.UTC`, which arrived in 3.11, so an older interpreter dies at import rather than at a useful message.

## Package layout

```text
megabonk-levels-<mod>-ml<melonloader>-linux/
├── install.sh                    sh wrapper: finds a new enough python3, execs the bundled installer
├── manifest.json                 the contract, described below
├── installer/player_installer/   the installer's own modules, copied in
├── vendor/                       vendor archives, named exactly as the manifest names them
├── content/levels/               bundled .mblevel.json files
└── content/packs/<pack-id>/      bundle + manifest.json (+ attachments.json) per pack
```

`install.sh` is the only entry point a player needs. It checks for `python3`, checks that it is new enough, and in both cases names the package manager command that installs a version that is, then hands the rest to `python3 -m player_installer --package <its own directory>`. Because `-m` resolves modules from the working directory rather than the script's own, the wrapper also puts the bundled `installer/` directory on `PYTHONPATH` — running the module by name without that fails with `No module named player_installer` no matter where the player stands. The floor lives in one place, `MIN_PYTHON` in `scripts/build_player_package.py`, which the wrapper text is built from.

## The manifest

`manifest.json` is a JSON object with `schema` `megabonk-player-package/1`. `load_manifest` in `scripts/player_installer/manifest.py` refuses anything it cannot use, naming the missing or bad key rather than failing later during the install.

| Key | Meaning |
| --- | --- |
| `schema` | `megabonk-player-package/1`. An unknown schema is an error, not a warning: an old installer must not half-install a package from a newer build. |
| `platform` | The OS this package targets. The Linux installer accepts only `linux`. |
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

After a successful install the installer writes `MegabonkLevels.installer.json` into the game directory, schema `megabonk-levels-install/1`: package id and versions, `installed_at`, the relative paths of every mod file, level and pack it placed, where the .NET runtime went and with what launch option, and how the `version.dll` override was applied.

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

## Building a package

```sh
task package:linux
task package:linux LEVELS="example-forest.mblevel.json thps.mblevel.json" PACKS=thps MOD_VERSION=0.4.2
```

`scripts/build_player_package.py` builds the mod, assembles everything into `.tools/player-package/`, and writes a distributable zip beside it.

Two choices are intentional:

- **Nothing is bundled unless asked.** `levels/` is a working directory full of dev regression maps, so levels are named individually with `--level` and packs with `--pack`. A `.local.mblevel.json` file is skipped even when named: it is a scratch file.
- **Packs come from two places, the way `task pack:install` assembles them**: the built AssetBundle from `.tools/bundles/<platform>/<pack>` and the manifest (plus optional attachments) from `unity/pack-authoring/packs/<pack>/`. `--pack-platform` picks the bundle; `windows` is right on Linux because the game runs the Windows build. Staged packs are validated with `validate_pack_source`, which reproduces the game's own rules — required `id`/`name`/`author`/`version`/`assets` fields, `id` matching the folder name, a bundle file present, and a `pack-attachments/1` sidecar when there is one — so a broken pack fails the build instead of landing in the Warehouse as a placeholder.

Vendor archives are taken from `.tools/vendor-cache/` and only verified there, never downloaded unless you pass `--allow-download`. The build writes into a staging directory and swaps it in at the end, so a failure leaves the previous package untouched.

The zip is deterministic — sorted entries, fixed timestamps, modes 0755 for `install.sh` and 0644 elsewhere — so two builds of the same inputs are byte-identical once `SOURCE_DATE_EPOCH` is pinned.

## Linux behaviour

### The Windows build only

The installer classifies the game directory before touching it (`scripts/player_installer/gamebuild.py`). `Megabonk.exe` plus `Megabonk_Data/` is the Windows build and the only supported one. A directory with `Megabonk.x86_64` is the native Linux build and the installer stops with exit 4 and instructions for switching to the Windows build through Steam Play, because MelonLoader 0.7.3 segfaults the native binary during Il2Cpp assembly generation and the upstream fix is not in a release. That is a hard refusal, not a warning: installing onto it would leave a player with a crashed game and no log.

### Finding Steam and the game

`scripts/player_installer/steam.py` looks for a Steam install under `$XDG_DATA_HOME/Steam`, `~/.local/share/Steam`, `~/.steam/root`, `~/.steam/steam`, and the two Flatpak locations (`~/.var/app/com.valvesoftware.Steam/...`). A directory counts as a client when it has `steamapps/`. Library folders are read out of `config/libraryfolders.vdf` (`vdf.py`, a read-only parser — the installer never writes VDF) and scanned for `steamapps/common/Megabonk`.

Two things make this sturdier than it looks:

- **A library on a detached drive** shows up as a configured root whose `steamapps` is gone. Those roots are skipped rather than reported as a missing game, and only when the even the parent directory is missing.
- **Flatpak Steam can only read paths granted to it**, so granted paths from `flatpak override --show` (or the persisted `local-overrides` file) are added as extra search roots. Without this, a game on a second disk is simply invisible to a Flatpak install.

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

## What is verified, and what is not

Verified offline, on macOS, against a synthetic Windows-layout game directory and a synthetic `steamapps/compatdata/<appid>/pfx` prefix:

- package assembly, manifest round-trip through `load_manifest`, and `verify_package` clean on a real package built from the real vendored archives;
- the full install → `--check` (no drift) → `--uninstall` lifecycle in both `gamedir` and `prefix` modes, leaving the game's own files and an untouched `UserData` behind;
- `version.dll` recorded as `via: registry` with `user.reg` actually carrying the key, and cleared on uninstall;
- refusal of a native-Linux game directory with exit 4;
- every plan, prefix-selection, VDF-parsing, Steam-discovery and manifest rule under `tests/test_player_installer_*.py` and `tests/test_build_player_package.py`.

The `install.sh` wrapper is checked apart from the game-directory fixtures: `sh -n` parses it, and the version gate was exercised against a real 3.9 interpreter and a stand-in reporting 3.11, each refused with exit 1 and the install hint, while a 3.13 run reaches the bundled module and `--help` prints.

Not yet verified, because it needs a real Linux desktop with Steam and Proton:

- **that the mod loads at all under Proton** — no run has ever proven it. The Windows-build path is the plan, not a measured result. If a live run shows the mod not loading, that is a finding to report, not something to route around.
- `reg add` through a real Proton `wine` binary (`via: wine`);
- the .NET runtime resolving from inside a real prefix, and the printed launch option working when Steam actually applies it;
- Flatpak-granted-path discovery against a real `flatpak override --show`;
- the zenity/yad progress dialog on a real desktop session;
- Steam's own behaviour around the download, including whether the Windows build needs the "Only download on my OS" untick on a given Steam version.
