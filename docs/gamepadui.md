# Gamepadui and remote Steam hosts

Two things live here: standing up a gamescope + Steam gamepadui session on a
Linux desktop, and driving the Megabonk mod workflow on such a host over SSH.
The install workflow was verified on a CachyOS host in gamepadui mode with
Proton Experimental, Megabonk 1.0.69 and MelonLoader 0.7.3. The session setup
below was verified on a Fedora 42 GNOME Wayland host running the game under
gamescope. SteamOS is an intended use of the same workflow, not a separately
verified host; substitute its user, library paths and selected Proton tool.

Examples use `game-host` as a placeholder SSH alias. Keep the desktop or
gamepadui session logged in. The player package needs Python 3.11 or newer, but
no repository checkout, uv, .NET SDK or separate Wine installation on the target.

**Use the Windows build under Proton**, launched by the existing Steam session,
rather than the native Linux build or a directly invoked Wine executable. The
mod ships `version.dll` through MelonLoader's `LD_PRELOAD` bootstrap, which the
native build does not load, and the player installer refuses a native install
outright (see [Player installer](development.md#player-installer)).

## Setting up gamepadui on a Fedora GNOME Wayland host

Three packages, plus a launcher:

```sh
sudo dnf install gamescope steam-devices mangohud
sudo dnf copr enable pvermeer/gamescope-session-guide
sudo dnf install gamescope-sessionsteam
```

`gamescope` provides the compositor, `steam-devices` the controller udev rules,
and `mangohud` the `--mangoapp` frame-time overlay. The COPR package installs a
GDM session (`/usr/share/wayland-sessions/gamescope-session-steam.desktop`)
that logs into the existing account through the GDM greeter theme and runs a
script that starts gamescope with Steam inside it, the same shape as the
SteamOS session. The native Fedora Steam RPM coexists with it; `which steam`
resolves to `/usr/bin/steam`.

To launch the session from the desktop rather than from the GDM session
selection, add a launcher under `~/.local/share/applications/`:

```ini
[Desktop Entry]
Name=Steam Game Mode
Comment=SteamOS-style gamepadui under gamescope (same as the login session)
Exec=gamescope -e -f --mangoapp -- steam -steamdeck -steamos3
Icon=steam
Terminal=false
Type=Application
Categories=Game;
StartupNotify=true
```

`-f` is required because the session runs nested inside a running GNOME
session; without it gamescope tries to take the VT. `steam -steamdeck` on its
own gives desktop mode — the `-steamdeck -steamos3` pair after `--` is what
selects gamepadui. Validate with `desktop-file-validate`, then
`update-desktop-database ~/.local/share/applications`. Dropping the file in
`~/.local/share/applications/` exposes it in the overlay app grid and dash; the
GNOME desktop-icons extension has no per-item control, so a file in `~/Desktop`
is not required and can be left out.

## Establish the vanilla baseline and actual prefix

Force a Proton tool under Megabonk's Compatibility settings, launch the
unmodified game once, confirm it reaches the menu, and quit before installing.
Verify the game directory contains `Megabonk.exe` and `GameAssembly.dll`. A
native `Megabonk.x86_64` install uses a different loader path and is not this
workflow.

Selecting Proton in the GUI triggers Steam to replace the native depot with
the Windows depot; a separate uninstall is not necessary. Wait for the update
to finish. In `appmanifest_3405340.acf`, Windows is depot `3405342` and Linux is
`3405341`. Hand-writing `CompatToolMapping` alone did not trigger this switch
on the tested Fedora client.

The launch dialog offers **Play Megabonk (DX11 - Recommended)** and a DX12
fallback. Select DX11. Set `-force-d3d11` in Steam's launch options to pin the
renderer, then verify the running game rather than trusting the flag:
`Player.log` under the active prefix's
`drive_c/users/*/AppData/LocalLow/Ved/Megabonk/` must report
`Version: Direct3D 11.0`. The live game's `/proc/<pid>/maps` should show
`d3d11.dll` and `dxgi.dll`, not D3D12/vkd3d modules. The tested Proton prefix
uses the Windows user `steamuser`, not the Linux account name.

**Do not derive the prefix from the game's library.** A moved game can run from
an SD card while Steam keeps its prefix in the home library. Example paths for
that layout are:

| Purpose | Path |
| --- | --- |
| Game | `/media/sdcard/SteamLibrary/steamapps/common/Megabonk` |
| Active prefix | `$HOME/.local/share/Steam/steamapps/compatdata/3405340/pfx` |

While the vanilla game is running, inspect the process environment over SSH;
`STEAM_COMPAT_DATA_PATH` is the compatdata directory, so append `/pfx` for the
installer:

```sh
ssh game-host 'pid=$(pgrep -x Megabonk.exe | head -1)
  test -n "$pid" || exit 1
  tr "\0" "\n" < "/proc/$pid/environ" |
    grep -E "^(STEAM_COMPAT_DATA_PATH|STEAM_COMPAT_INSTALL_PATH)="'
```

An existing `drive_c` alone does not prove Steam uses that prefix: invoking Wine
with a wrong `WINEPREFIX` can create a convincing unused prefix. Automatic
installer discovery currently assumes the game's library, so pass the measured
`--prefix` on **every install and check**. Do not delete another prefix merely
because it is not active in this launch.

## Install, launch and verify

Quit through the game first. When that is unavailable, the following SSH
fallback sends SIGTERM only to the exact Windows game process name, leaving
Steam alone:

```sh
ssh game-host 'pkill -TERM -x Megabonk.exe || true'
ssh game-host 'pgrep -ia -x Megabonk.exe'
```

The second command must report no process before changing files or prefix state.
SIGTERM is process termination, not a guarantee of in-game saving. Never use
`pkill -f Megabonk`: it can match the SSH shell's own command line. Do not kill
Steam or all Wine processes to quit one game.

Build the package on the development machine, transfer it, and run its bundled
installer on the target. Use a fresh extraction directory; these commands assume
`~/mb-player` does not already contain another package:

```sh
task package:linux
scp .tools/megabonk-levels-dev-ml0.7.3-linux.zip game-host:~/
ssh game-host 'mkdir -p ~/mb-player && cd ~/mb-player &&
  unzip -q ~/megabonk-levels-dev-ml0.7.3-linux.zip'
ssh game-host 'cd ~/mb-player
  G=/media/sdcard/SteamLibrary/steamapps/common/Megabonk
  P="$HOME/.local/share/Steam/steamapps/compatdata/3405340/pfx"
  ./megabonk-installer --game-dir "$G" --prefix "$P" --dotnet-in prefix --wine-override registry &&
  ./megabonk-installer --game-dir "$G" --prefix "$P" --dotnet-in prefix --wine-override registry --check'
ssh game-host 'steam steam://rungameid/3405340'
```

The archive name above is the development build's name; substitute the package
produced by the current build. The installed runtime is Windows .NET 6 inside
the actual prefix. This configuration loaded the mod without a `DOTNET_ROOT`
Steam launch option. The observed install record reported the override as
`via: wine`, so inspect the recorded result rather than assuming the requested
registry mode describes the mechanism used. `--check` must say the install
matches the package and exit 0. Omitting `--prefix` can instead report
runtime/override drift against the wrong library.

The Steam URI successfully launched the tested gamepadui session over SSH
without exporting display variables. If Steam reports a display/session error on
another host, use its actual graphical-session environment or launch from the
gamepad UI; do not assume `DISPLAY=:0` works everywhere. A successful URI
command only means the request was sent, not that the game or mod is ready.

Read the **new launch's** `MelonLoader/Latest.log` in the game directory.
First-launch assembly generation took about 40 seconds on the tested host;
subsequent launches used the generated cache. The measured success markers were:

```text
Assembly Generation Successful!
1 Mod loaded.
[MegabonkLevels] MegabonkLevels mod initialized.
```

The assembly-generation success line need not recur on a cached launch. Check
timestamps, the MelonLoader version banner and the mod-initialized line, not
merely process existence or a stale log. If bootstrap never runs, inspect
`/proc/<pid>/maps` for `version.dll`: the failing wrong-prefix launch mapped
Proton's builtin DLL rather than the game's loader DLL. Steam's
`~/.local/share/Steam/logs/gameprocess_log.txt` records launch/process
tracking. Preserve these logs and report a failed mod load rather than trying
unverified runtime or launch-option workarounds.

Three launch traps measured on the gamescope host. A **Steam Cloud save-conflict
dialog blocks every `steam://rungameid` silently** — the URI is forwarded and does
nothing until the dialog is answered ("You must make a selection to launch the
application"); back up the game's `UserData/` first, pick whichever side is newer
(the dialog's buttons carry the real timestamps), and expect a follow-up "Unable to
Sync — Play anyway" prompt. **Direct-Proton launches of the Windows build do not
work on that host**: `proton run` and even the pressure-vessel
`waitforexitandrun` chain return exit 0 within ~10 seconds with a correct install,
so launch through the Steam client and use the client's own binary
(`~/.local/share/Steam/ubuntu12_32/steam steam://rungameid/3405340`) to forward the
request. And the gamepadui screen is **not capturable over X** — `x11grab` of the
gamescope display returns black frames — but the client answers Chrome DevTools
queries on its `--remote-debugging-port` (8080): `GET /json` lists the pages, and
`Runtime.evaluate` on the "Steam Big Picture Mode" page reads `document.body.innerText`
and clicks dialog buttons, which is how the blocking dialog is identified without a
screenshot.

## Transfer THPS content and test the player menus

The tested player package contains only `example-forest`; Warehouse requires both
`thps.mblevel.json` and the `thps` pack. Use the **Windows bundle even though the
host is Linux**, because the Unity player runs under Proton. Build it on the
authoring machine (see [Loading the THPS level](development.md#loading-the-thps-level)),
then stage the matching bundle, manifest and attachment metadata on the target:

```sh
ssh game-host 'mkdir -p ~/mb-player/thps-source/thps'
scp .tools/bundles/windows/thps \
  unity/pack-authoring/packs/thps/manifest.json \
  unity/pack-authoring/packs/thps/attachments.json \
  game-host:~/mb-player/thps-source/thps/
ssh game-host 'cd ~/mb-player &&
  ./megabonk-installer --game-dir "$G" --prefix "$P" --levels "$HOME/mb-player/content/levels" \
    --packs "$HOME/mb-player/content/packs" --thps-bundle thps-source/thps'
```

Restart the game and test Warehouse, Piece Editor and Map Editor. The mod logs
the resolved content roots under `[ContentPaths]`; inspect it before concluding
the content is missing.

In a clean run the Warehouse shows THPS assets as well as Forest assets, and the
Piece Editor can create and place at least one THPS piece. Record the result
under the standard result table format.

Do not install a development harness or editor-only tools unless they are
explicitly approved development exceptions. Keep:

- input driving limited to documented menu navigation;
- screenshots limited to visible menus and test states;
- process termination scoped to the game process;
- no changes to game assets or user content beyond the documented installer.

### Driving stock menus with run.py

Stock Rewired menus and the gamepadui Steam client need OS-level keyboard,
mouse, and controller events. The editor `key`/`mouse`/`type_text` harness
commands are for editor mode, not these menus. Use `run.py menu`, which creates
uinput devices on the Linux target and accepts a bounded batch. The maintained
batch driver supports keyboard, controller, mouse, read-only harness diagnostics,
and screenshot retrieval.

Start devices before launching the game when possible, keep the daemon running
across batches, and stop it afterward:

```sh
# Host dependencies as root:
# dnf install python3-devel gcc libX11-devel kernel-headers kernel-devel
# (Debian/Ubuntu: apt install python3-dev build-essential libx11-dev linux-headers-$(uname -r))
# uinput module:
#   modprobe uinput
#   echo uinput >/etc/modules-load.d/uinput.conf
# group membership (then re-login/restart the SSH session):
#   getent group input >/dev/null || groupadd --system input
#   usermod -aG input <user>
#   install -m 0644 /dev/null /etc/udev/rules.d/99-uinput.rules
#   printf '%s\n' 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
#     >>/etc/udev/rules.d/99-uinput.rules
#   udevadm control --reload-rules && udevadm trigger --sysname-match=uinput

uv run scripts/run.py menu start --host ssh-host --remote-repo ~/git/megabonk_mods
task game:run
uv run scripts/run.py menu drive '[["key","KEY_DOWN"],["pad","BTN_SOUTH"]]' \
  --host ssh-host --remote-repo ~/git/megabonk_mods --out ./menu.png
uv run scripts/run.py menu status --host ssh-host --remote-repo ~/git/megabonk_mods
uv run scripts/run.py menu stop --host ssh-host --remote-repo ~/git/megabonk_mods
```

`--out` asks the harness for a frame, so it needs the harness enabled and shows
the game, not the Steam client or any other window. To see Steam's own gamepad
UI, use the portal screenshot path described in
[What it took](#capturing-the-screen).

`menu` verbs are `start`, `serve`, `status`, `stop` and `drive`. `drive` takes
the batch as a **positional** JSON array of commands with `--settle` seconds
between actions (default 0.35, 0–10) and `--timeout` for the whole run
(default 10, 0–300); there is no `--batch` flag and no `[ms]` delay element.
Each command is a small array:

| Command | Effect |
| --- | --- |
| `["key","KEY_DOWN"]` | keyboard key from the whitelisted `KEY_*` set |
| `["pad","BTN_SOUTH"]` | controller button (`BTN_*`) on the virtual gamepad |
| `["axis","ABS_HAT0Y",-1]` | controller axis within its documented range |
| `["move",X,Y]` | absolute pointer move on `--display` |
| `["click"]` | left click at the current pointer position |

Keyboard names are the `KEY_*` constants only: `KEY_ENTER`, `KEY_ESC`, `KEY_UP`,
`KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`, `KEY_TAB`, `KEY_SPACE`. Buttons are the
`BTN_SOUTH`/`BTN_EAST`/`BTN_NORTH`/`BTN_WEST`/`BTN_START`/`BTN_SELECT`/`BTN_TL`/
`BTN_TR`/`BTN_THUMBL`/`BTN_THUMBR` set, and axes `ABS_X`/`ABS_Y`/`ABS_RX`/
`ABS_RY`/`ABS_HAT0X`/`ABS_HAT0Y`/`ABS_Z`/`ABS_RZ`. The virtual device appears to
Steam Input as a standard Xbox 360 pad, which is what makes it work for both
Steam's own gamepad UI and the game's Rewired menus.

`menu` has no `key`, `mouse` or `type` verb. Those are top-level `run.py`
commands that talk to the editor harness, and outside editor mode the game
ignores them while the command still reports success. Every OS-level event a
stock menu can see must go through a `drive` batch.

`--host` must be a trusted SSH target and `--remote-repo` a shell-quoted path
that resolves on that host. Set `MEGABONK_SSH_MAX_OUTPUT_BYTES` if a trusted
target legitimately needs more than the default output bound. Do not paste
untrusted batch JSON or let an untrusted path into these flags: validation is
defense in depth, not a sandbox.

Dependencies are `evdev>=1.6` and `python-decouple>=3.8` from
`pyproject.toml`, plus the host packages, `uinput` module and input-device
permissions above. A Debian/Ubuntu target has the `input` group by default;
Fedora and CachyOS usually do not and need it created before the daemon can
open `/dev/uinput`.

For an SSH target, run the local supervisor with `--host` and `--remote-repo`.
It starts the remote daemon over SSH, forwards a private Unix socket through the
same SSH tunnel, sends validated batches, optionally pulls a screenshot, and
stops the daemon when the supervised command exits. For a persistent daemon
(e.g. driving Steam's own UI across many separate invocations), start it with
`menu start` and stop it with `menu stop`. `--display` selects the X display for
pointer moves; omit it for keyboard/controller-only batches.

`uv` is not necessarily on a non-interactive SSH `PATH` — on a box where it comes
from mise, invoke through `mise exec -- uv run scripts/run.py …`, and give
`--remote-python` an **absolute** interpreter path
(`--remote-python /home/<user>/git/megabonk_mods/.venv/bin/python`). A literal
`~/…` is passed through unexpanded and fails with "No such file or directory".

`scripts/run.py` is a shim over the `megabonk_harness` package, so that venv must have the project installed: run `uv sync` in the remote checkout after pulling the packaging change, or the remote call fails with `No module named 'megabonk_harness'`.

Run `task scripts:test` to exercise device validation and batch validation
without opening physical devices, including controller and mouse paths.

### Verified menu regression under Proton

Under Proton Experimental, a long editor session can enter editor mode but be
unable to leave it: `E` and `Escape` stop reaching the game and the harness
rejects `editor off` with `not in editor mode`. Re-launching the game clears it.
When reproducing, also record whether the mouse was captured before keyboard
input stopped responding.

## What it took (worth recording)

Findings from bringing up the Fedora 42 gamepadui host and driving it over SSH,
each of which cost real time to discover.

### Driving input

- `run.py key down` looks like a menu command and is not one: top-level `key`,
  `mouse` and `type` post to the editor harness, which drops them outside editor
  mode while the command still exits 0. A batch of D-pad presses can therefore
  report success and move nothing on screen. Only `menu drive` reaches the
  compositor, and arrows need their `KEY_*` name in a `drive` command.
- Confirm the virtual pad is actually live before blaming navigation: Steam
  Input draws its A/MENU button bar when it has a gamepad, and the game's
  Photosensitivity Warning names the axis it is waiting for.

### Capturing the screen

- The compositor process is `gamescope-wl`, not `gamescope`, so `pkill -x
  gamescope` never matches it.
- gamescope's wlserver exposes no `zwlr_screencopy_manager_v1`. wlroots
  compositors advertise only `screencopy` and `dmabuf`, so `weston-screenshooter`
  and `grim` cannot capture it.
- GNOME Shell's screenshot D-Bus APIs (`org.gnome.Shell.Screenshot`, plus `Eval`
  and `GetWindows`) are refused for callers arriving over SSH, so there is no
  scriptable GNOME capture path from a remote shell.
- The working path is the freedesktop portal: `org.freedesktop.portal.Screenshot`
  → `SaveScreenshot` with `handle_result_path`, invoked inside the user's
  graphical session (a D-Bus call from an SSH session reaches the portal through
  the session bus). It writes a PNG under `~/Pictures`, which then has to be
  pulled back over SSH.
- The game itself runs on a **rootless** nested Xwayland (`:2`,
  `XAUTHORITY=/run/pressure-vessel/Xauthority`). Rootless means no root window,
  so `magick import -window root -display :2` fails with "no such window" and a
  named window id resolves to 0x0.
- A full-desktop capture taken while the game runs reads as near-black: the
  compositor composites the gamescope layer separately from the cursor and
  overlay layers. Crop the window region out of the portal screenshot
  (`magick in.png -crop WxH+X+Y out.png`) rather than trusting a full-frame grab
  of a running game.
- The panel is 3072×1920 and gamescope renders Steam at 1280×720 upscaled, so
  text in a full-frame screenshot is small; crop instead of downscaling.

### Steam under a gamescope session

- `steam steam://shutdownsteam` prints `Shutdown request sent to Steam, it may
  take a few seconds to complete.` and does nothing on this build. `pkill -TERM
  -x steam` does quit it.
- **Steam respawns.** Under the gamescope session, killing `steam` does not
  leave it dead — the session brings it back. `userdata/<id>/config/localconfig.vdf`
  is rewritten by the running client, so any edit made while it is alive is gone
  by the time Steam restarts. This is what makes a Compatibility edit look
  "ignored": stop the session, not just the `steam` process, then edit the file,
  then start the session again.
- With `Apps/3405340 → compat → {tool,other}` set to `proton-experimental` under
  `UserLocalConfigStore → Software → Valve → Steam`, and `CompatToolMapping`
  carrying the same tool at `priority 2`, `~/.local/share/Steam/logs/compat_log.txt`
  can still log `Recording non-user mapping for 3405340 at priority 85 to tool
  native` and launch `Megabonk.x86_64`. Only the depot layout tells you which
  OS actually got installed: `appmanifest_3405340.acf` listing depot `3405341`
  (Linux) and no `1391111` (Windows) means the native build is in place.
- `~/.config/unity3d/Ved/Megabonk/prefs` holds only `Screenmanager` keys on this
  host, so the Photosensitivity Warning is not accepted-and-remembered: it
  appears on every launch and needs a fresh Enter (`KEY_ENTER` in a `drive`
  batch) each time, which advanced it to the main menu and on to Character
  Selection. Steam Input confirms the virtual pad is live by drawing its A/MENU
  bar.
- MangoHud's `no_display` key is not known to `mangoapp`, which logs
  `Unknown option 'no_display'` from `~/.config/MangoHud/MangoHud.conf` at
  startup. It is cosmetic — the overlay and mangoapp read the same file but
  support different keys.
- On a headless dev box, disable GNOME's idle suspend or the machine sleeps
  mid-session and SSH times out:
  `gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'`.

### Dev harness on a plain Fedora Steam host (no gamescope)

These apply when using the development harness (not a packaged install) on a
Fedora host that runs vanilla Steam (not a gamescope session):

- **Offline direct-Proton launch** must export `SteamAppId=3405340 SteamGameId=3405340`.
  Without them the loader calls `SteamApps.GetAppBuildId()` before Steamworks
  has initialised and every `load-level` command fails with
  `System.InvalidOperationException: Steamworks is not initialized`.
- **Stale harness commands survive a restart.** The launcher script does not
  clear the harness queue; a queued `quit` written during a previous session
  executes at the next boot and kills the process immediately. Clear all five
  subdirectories before launching:
  `for d in commands processing results done rejected; do rm -f "$H/$d"/*.json; done`
  (where `$H` is `<game>/harness`). `run.py relaunch` handles this automatically.
- **Photosensitivity Warning per launch.** `~/.config/unity3d/Ved/Megabonk/prefs`
  does not persist the accepted state here, so the warning appears on every
  launch. Dismiss it with `run.py menu drive` and `KEY_ENTER` (start the menu
  daemon first). A `load-level` sent while the screen is up fails with
  `LevelLoader: load failed: no MapData found for map=Forest (1); available:`
  with an empty list — retry the load after Enter.
- `run.py interact` targets the **nearest** interactable, not a named one. In
  the Warehouse it opens a chest 31 m away instead of the boombox. Use
  `run.py interact --type Boombox --force` for boombox work.
- Invoke `~/.local/share/mise/shims/task` directly; `mise exec -- task`
  mis-resolves the lowercase `taskfile.yml` and reports "no tasks defined".
- Menu batch JSON does not survive two nested SSH quoting layers. Write the
  `menu drive` call to a helper script on the target, or use `run.py`'s
  `--host`/`--remote-repo` flags from the authoring box.
