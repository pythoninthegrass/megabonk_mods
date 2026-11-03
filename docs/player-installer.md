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

`scripts/player_installer/steam.py` looks for a Steam install under `$XDG_DATA_HOME/Steam`, `~/.local/share/Steam`, `~/.steam/root`, `~/.steam/steam`, the two Flatpak locations (`~/.var/app/com.valvesoftware.Steam/...`), and any Flatpak-granted path. A directory counts as a client when it has `steamapps/`. Library folders are read out of `config/libraryfolders.vdf` (`vdf.py`, a read-only parser — the installer never writes VDF) and scanned for `steamapps/common/Megabonk`.

Two things make this sturdier than it looks:

- **A library on a detached drive** shows up as a configured root whose `steamapps` is gone. Those roots are skipped rather than reported as a missing game, and only when even the parent directory is missing.
- **Flatpak Steam can only read paths granted to it**, so granted paths from `flatpak override --show` (or the persisted `local-overrides` file) are read on every run and added as extra search roots. They also count as the Flatpak client itself when one of them holds `steamapps/`: a maintainer machine exists where the entire Steam root — `config/`, `userdata/` and `steamapps/` — was moved to a data disk, so no client is left at any default location, and the grants are the only way back to it. Without this, a game on a second disk is simply invisible to a Flatpak install.

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
static binary per platform with no runtime dependency and no external module — the module
requires nothing but the standard library, and `task installer:verify-static` fails if that
stops being true. It is a companion to the Python reference, not a replacement: `install.sh`
still runs `scripts/player_installer`, the player package zip carries no Go binary, and the
binaries land in gitignored `.tools/installer/`.

```sh
task installer:build            # cross-compile into .tools/installer
task installer:test             # gofmt check, go vet, go test
task installer:verify-static    # CGO off, no dependencies, not dynamically linked
task installer:parity           # both installers over the same scenarios
```

Targets are `darwin/arm64`, `linux/amd64` and `windows/amd64`. `linux/arm64` is left out on
purpose: the game and its Proton prefixes are x86_64, so an arm64 Linux player would run the
installer and never the mod. The Windows binary is built to prove the port is portable and is
not executed by any test.

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

Dialogs are the exception: the Go `PickProgress` always returns plain numbered text. The
zenity/yad/kdialog backends stay Python-only until the GUI work is ported.

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

The fleet also includes Fedora 42 with GNOME Wayland, Intel Arc graphics and a
gamescope + Steam gamepadui launcher. Its verified setup includes switching to
Windows depot `3405342` through Steam's GUI and selecting DX11 (confirmed in the
active prefix's `Player.log`). This is not yet evidence of a wiped player-package
install with the mod loaded. Native Linux loader installation is out of scope;
the AlmaLinux host supplies Flatpak discovery and KDE progress evidence only.

Still pending:

- the Go binaries beyond the host the parity harness runs on: `linux/amd64` is exercised by
  `task installer:parity`, the `darwin/arm64` and `windows/amd64` builds are compiled and
  checked for being static but never executed, and no Go binary has yet installed the mod on
  a maintainer host;
- clean-install verification on both CachyOS and Fedora, with fresh mod-load logs;
- automatic removable-media game selection on CachyOS: library discovery finds the mounted SD-card library, but game discovery incorrectly selects an unrelated home-library game (`1000xRESIST`) because its `GameAssembly.dll` matches first; pass explicit `--game-dir` and the measured `--prefix` until this is fixed;
- the printed game-directory `DOTNET_ROOT` launch option working when Steam actually applies it (the live proof uses prefix mode);
- the persisted `local-overrides` file as the source of the Flatpak grants — the real host went through `flatpak override --show`, which is the other of the two paths in `flatpak_granted_paths`;
- the zenity and yad dialog paths — the verified host has neither installed, so those branches run only in tests (the kdialog-over-D-Bus path above is the one with desktop evidence);
- Steam's own behaviour around the download, including whether the Windows build needs the "Only download on my OS" untick on a given Steam version.
