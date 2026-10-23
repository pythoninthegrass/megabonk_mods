# Development harness

The mod ships a development-only command channel so a shell script can run a load-and-check cycle against the running game without simulating keyboard or mouse input: load a level, capture the game's own rendered frame, and quit. It is driven by `scripts/run.py`.

## Enabling

The harness is off by default. It runs only if the marker file `<game dir>/harness/enabled` exists when the game starts, so a normal install exposes no command channel.

```sh
uv run scripts/run.py enable    # creates harness/enabled and harness/commands
uv run scripts/run.py disable   # removes the marker
```

Enabling takes effect on the next game launch. When active, the mod logs `DevHarness: enabled, watching '<dir>'` to `MelonLoader/Latest.log`.

The game directory is resolved the same way as in `scripts/game_paths.py`: process environment, then the nearest `.env` found walking up from the current directory or the script, then the built-in default: `<prefix>/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk` inside the Wine prefix on macOS, `C:\Program Files (x86)\Steam\steamapps\common\Megabonk` on Windows. The keys are `MEGABONK_GAME_DIR` (the game directory itself, any platform), `MEGABONK_WINE_PREFIX` (the Wine prefix, the directory that contains `drive_c`) and `MEGABONK_BOTTLE` (the older spelling: the prefix's `drive_c`; `MEGABONK_WINE_PREFIX` wins when both are set). The default prefix is `~/.local/share/megabonk/wine` for plain Wine and the CrossOver Steam bottle (`~/Library/Application Support/CrossOver/Bottles/Steam`) for the CrossOver runtime. `MEGABONK_WINE_PREFIX` also applies when `MEGABONK_GAME_DIR` points outside the prefix, which is how the launch scripts and `wine:dxvk` find the prefix in that case; without either setting the prefix is the `drive_c` ancestor of the game directory. `uv run scripts/game_paths.py` prints the resolved `game_dir` and `wine_prefix`. On macOS, `MEGABONK_MACOS_RUNTIME` (`wine`, the default, or `crossover`) picks the runtime and `MEGABONK_WINE` points at the plain Wine binary.

## Commands

`run.py` writes one JSON file per command into `<game dir>/harness/commands/`. The mod polls that folder twice a second, runs the files in name order, first moves each to `harness/processing/` so it cannot replay after a crash or quit, then moves it to `harness/done/` on success or `harness/rejected/` when parsing or execution fails.

| Command | Wire format | `run.py` |
| --- | --- | --- |
| Load a level and start the run | `{"command":"load-level","path":"<file>"}` | `run.py load <level>` |
| Save the rendered frame as a PNG | `{"command":"screenshot","path":"<file>"}` | `run.py screenshot <out.png>` |
| Freeze gameplay | `{"command":"freeze"}` | `run.py freeze` |
| Resume gameplay | `{"command":"resume"}` | `run.py resume` |
| Make the player survive enemy damage | `{"command":"invulnerable"}` | `run.py invulnerable` |
| Restore normal player damage | `{"command":"vulnerable"}` | `run.py vulnerable` |
| Check in-game Steamworks readiness | `{"command":"steam-ready"}` | `run.py steam-ready` |
| Read the game's current state | `{"command":"state"}` | `run.py state` |
| Start or stop the kill-floor heartbeat | `{"command":"heartbeat","enabled":true}` | `run.py heartbeat <on\|off>` |
| Start or stop the cell-change log | `{"command":"cells","enabled":true}` | `run.py cells <on\|off>` |
| Enter or leave editor mode | `{"command":"editor","enabled":true}` | `run.py editor <on\|off>` |
| Hold the camera at a pose | `{"command":"camera","position":[x,y,z],"rotation":[rx,ry,rz]}` | `run.py camera X Y Z --rot RX RY RZ` |
| Return the camera to the game | `{"command":"camera-clear"}` | `run.py camera --clear` |
| Tap, press or release a key | `{"command":"key","action":"tap","key":"R","modifiers":["LeftShift"]}` | `run.py key R --mod LeftShift`, `run.py key --down W`, `run.py key --up W` |
| Move, click, press or release the mouse | `{"command":"mouse","action":"click","button":0,"x":960,"y":540}` | `run.py mouse move X Y`, `run.py mouse click [--button N] [X Y]`, `run.py mouse down\|up`, `run.py mouse clear` |
| Type text | `{"command":"type","text":"chest"}` | `run.py type chest` |
| Move the player | `{"command":"teleport","position":[x,y,z]}` or `{"command":"teleport","cell":[cx,cz]}` | `run.py teleport X Y Z`, `run.py teleport --cell CX CY` |
| Pick an upgrade in the open level-up dialog | `{"command":"dismiss-levelup","choice":0}` | `run.py dismiss-levelup [--choice N]` |
| Quit the game | `{"command":"quit"}` | `run.py quit` |
| Relaunch the test level in editor mode | Multiple commands | `run.py relaunch [level]` |

`run.py cycle <level> <out.png>` runs load, waits `--settle` seconds (default 5), takes the screenshot, then quits. `--invulnerable` makes the player invulnerable right after the load, before the settle wait. `--freeze` freezes gameplay and `--camera X Y Z RX RY RZ` poses the camera after the settle wait and before the screenshot. `--timeout` (before the subcommand, default 15 seconds) sets how long to wait for each command and for the PNG to appear. The exit code is 0 only if every step succeeded, 1 if a step failed or timed out, and 2 if the harness is not enabled (`run.py` prints `harness not enabled at <dir>; run 'run.py enable' and relaunch the game`).

`run.py relaunch` quits the running game, starts a fresh process through `task game:run` (`task crossover:run` when `MEGABONK_MACOS_RUNTIME=crossover`), waits for a new `DevHarness: enabled` log entry, then polls the in-game Steamworks client before loading `levels/example-forest.mblevel.json`. It retries the load until `KillFloor: armed` appears, then enables invulnerability and editor mode. It allows at least 60 seconds for readiness checks, even when `--timeout` is lower. Pass an optional level path to use a different level file. Use this command between interactive editor sessions; do not send another `load` to an existing run. A second `load` while in editor mode is survivable: `LiveEditPatch` hides its session while the old tile generator is destroyed, so the editor tools find no grid until the reloaded level finishes generating, and the editor re-enters on the new run.

An unknown command, malformed JSON, a missing or empty `path`, or a command that fails while running logs an error and moves the file to `rejected/` without replaying it.

The paths in `load-level` and `screenshot` are interpreted by the game process, so `run.py` converts them (see below).

### Results

Before moving a command file to `done/` or `rejected/`, the mod writes `harness/results/<command file name>`: UTF-8 JSON, one object, written to `<name>.tmp` and renamed so a reader never sees a partial file. A command that succeeds writes `{"command":"<wire name>","ok":true,"result":<object or null>}`. A command that fails while running writes `{"command":"<wire name>","ok":false,"error":"<message>"}`. A file that does not parse writes the same failure shape with `"command":null`. Every command other than `state`, `teleport` and `dismiss-levelup` has `"result":null`. The result file is written before the command file moves, so a caller that sees the file in `done/` or `rejected/` can read the result at once. Result files are never deleted by the mod.

`run.py` reads them with `read_result(harness, name)`, which returns `None` when the file is absent or not valid JSON. Every subcommand that sends a command exits 1 and prints the `error` text on stderr when the result has `ok:false`, even if the command file landed in `done/`. A missing result file does not fail a command, so `run.py` still works against a mod built before results existed.

### State

`run.py state` prints the `result` object of the `state` command as one line of JSON. A field the mod cannot source is `null`.

| Field | Type | Source and when it is `null` |
| --- | --- | --- |
| `levelLoaded` | bool | `CustomLevelState.IsActive`: the run was started through the mod's level loader |
| `killFloorArmed` | bool | The kill-floor watcher armed for the current level |
| `editor` | bool | Editor mode is active |
| `frozen` | bool | `MyTime.paused` |
| `invulnerable` | bool | The harness's invulnerability is active on the current player's inventory |
| `player` | object or null | `{"position":[x,y,z],"cell":[column,row]}`. `null` when there is no player in the scene (menu, loading). `cell` is `null` when the position label's grid is not armed (no kill floor), and can lie outside the grid |
| `editorTool` | string or null | The active tool name (`Raise`, `Lower`, `Slope`, `Remove`, `Place`, `Select`). `null` outside editor mode, where the tool is not read |
| `selected` | string or null | The selected object as `gen:<genId>` or `placement:<id>`. `null` outside editor mode or when nothing is selected |
| `paletteEntries` | int or null | The number of entries in the catalog palette. `null` outside editor mode, where the palette is not read |
| `screen` | `[width, height]` | `Screen.width` and `Screen.height` in pixels; screen coordinates for input use this space |

## MCP server

`scripts/mcp_server.py` exposes the harness as an MCP server named `megabonk`, so an agent can call typed tools instead of shelling out to `run.py`, and gets screenshots back as inline `image/png` content. It is a PEP 723 script (`uv run --script scripts/mcp_server.py`) that reuses `run.py`'s helpers rather than duplicating them, and resolves the game directory the same way `run.py` does.

stdout is the MCP protocol channel, so the server writes nothing to stdout; everything reaches the client as tool results. Blocking waits (sending a command, waiting for the game to exit, the whole relaunch sequence) run off the event loop so one tool call never stalls the server.

Tools: `relaunch(level?)` (reports progress through the MCP context and returns the final `state`), `load(level)`, `quit()`, `screenshot()` (returns the PNG inline), `state()`, `editor(on)`, `freeze()`, `resume()`, `invulnerable(on)`, `camera(position?, rotation?, clear?)` `log_tail(pattern?, since_launch?, max_lines?)`, and the input and gameplay tools `key(key, modifiers?, action?)`, `mouse(action, x?, y?, button?)`, `type_text(text)`, `teleport(position?, cell?)` and `dismiss_levelup(choice?)`. A command the mod rejects, a timeout, or a result with `ok:false` surfaces as a tool error carrying the result file's `error` text (or `<command> <outcome>` when there is no result file). `log_tail` reads `MelonLoader/Latest.log`: `since_launch` (default true) trims to the last `DevHarness: enabled` line, `pattern` keeps lines matching a regex, and `max_lines` (default 50) caps the result to the last N lines. The input tools validate their arguments before sending anything and raise a tool error for a bad combination: `teleport` needs exactly one of `position` (three numbers) or `cell` (two integers), `mouse` `move` needs both `x` and `y` and the other actions take both or neither, and `key` accepts `modifiers` only with `action` `tap`. Each returns the result file's object (`teleport` and `dismiss_levelup` carry data; the others return `null`). Coordinates are screenshot pixels with the origin at the top left, as in "Key, mouse and type commands", which also lists the valid key names. Input is queued over the next frames, so a `screenshot` straight after may predate its effect.

### End-to-end check

A walkthrough that exercises the whole chain (agent, MCP, harness files, mod, game) using only the `megabonk` tools, in editor mode on the example forest level:

1. `relaunch()` quits any running game, starts a fresh one, loads `levels/example-forest.mblevel.json`, goes invulnerable and enters editor mode. The returned state has `editor: true`.
2. `screenshot()` and look for the catalog palette on the left.
3. `mouse(action="click", x, y)` on a palette row, using pixel coordinates read from the screenshot. A later `screenshot()` shows the title of the palette panel with that entry selected.
4. `key(key="Alpha5")` switches to the Place tool and a `mouse` click on a tile places the selected entry; `key(key="Alpha6")` and a click on the object select it, and `key(key="R")` rotates it. `type_text("e2e")` after a click on the level-name field types into it.
5. `teleport(cell=[cx, cz])` to a distant cell, wait about a second, then `state()` to confirm `player` and `cell` moved and `editor` is still true, and `screenshot()`. In editor mode the free-fly camera does not follow the player, so the check is the `state` position and the on-screen `me: pos(...)` label, not the view. The example forest grid is 15x15, so cells run 0 to 14; a cell outside it comes back as a tool error.
6. `quit()`.

If a step fails, `log_tail(pattern="Harness|Error")` shows whether the mod saw the command. A rejected command carries the mod's error text in the tool error, which says which layer refused it.

Register it by adding the `megabonk` entry under `mcpServers` in `.mcp.json` (command `uv`, args `["run", "--script", "scripts/mcp_server.py"]`); the repo ships it already. Confirm it with `/mcp`, which lists `megabonk` as connected.

## Launching under Wine (macOS)

Plain Wine is the default macOS runtime. It runs against the Wine prefix named by `MEGABONK_WINE_PREFIX` (default `~/.local/share/megabonk/wine`), which has to hold a Windows Steam install with Megabonk; the repo does not create or populate a prefix. To reuse the bottle CrossOver created, set `MEGABONK_WINE_PREFIX=~/Library/Application Support/CrossOver/Bottles/Steam` in `.env`, and its saves, Steam login and installed game carry over. The setup was verified with Wine 11.18 and DXVK-macOS on Apple silicon with Rosetta, using that bottle as the prefix.

```sh
task wine:install       # pinned Wine build and DXVK DLLs; skips what is already installed
task game:steam         # Steam client, detached; wait about 30 seconds for logon
task game:melonloader:install
task game:run           # Megabonk.exe, detached
```

`task wine:install` runs `wine:app` and `wine:dxvk` from `taskfiles/wine.yml`. The pins (version, URL, sha256 for each) are defined once in that file's `vars` and can be overridden by exporting `WINE_VERSION`, `WINE_URL`, `WINE_SHA256`, `DXVK_VERSION`, `DXVK_URL` or `DXVK_SHA256`, or by setting them in `.env`, which the root `taskfile.yml` loads with `dotenv` for every task. Each step downloads its archive to a temporary directory and checks the sha256 before extracting or copying anything, so a mismatch stops the task with nothing changed. An unset or empty override falls back to the pin. `wine:dxvk` installs into the prefix named by `MEGABONK_WINE_PREFIX` and needs it to exist (the `drive_c/windows/system32` directory); on a machine without one it prints `wine:dxvk skipped: no Wine prefix at <path>` and exits 0, leaving the Wine build installed, so run `task wine:dxvk` again once the prefix exists. The repo does not create a prefix. The skip is Task's command-level `if:`, which needs Task 3.47 or newer (pinned in `.tool-versions`); an older Task ignores `if:` without a warning and the step then fails on the missing prefix.

- **Wine build.** The Gcenx `wine-devel` 11.18 build is extracted to `~/Applications/wine11/Wine Devel.app`, then the quarantine attribute is removed and the app is ad-hoc signed so Gatekeeper lets it run. Set `MEGABONK_WINE` to use a different binary. Wine 7.7 (the Game Porting Toolkit cask) crashes Steam with an unhandled page fault, and Homebrew's `wine-stable` is disabled.
- **DXVK.** Wine's own Direct3D path reports no supported feature level on macOS, and Unity fails with `Failed to initialize player`. The task copies the x64 `d3d11.dll` and `d3d10core.dll` from DXVK-macOS (async build, `v1.10.3-20230507-repack`) into the prefix's `drive_c/windows/system32`. The first run saves the DLLs it replaces in `drive_c/windows/dxvk-orig/` and never overwrites that backup. `drive_c/windows/dxvk.installed` records the installed pin. MoltenVK ships inside the Wine build. The DXVK release publishes no checksum for its archive, so the pinned sha256 was computed locally from the downloaded file and is not independently verified.
- **`USER=crossover`.** Wine takes the Windows profile name from the macOS user. Without the override Wine creates `C:\users\<macOS user>` with no saves, and the game starts from an empty profile. CrossOver ran as `crossover`, so the saves live in `drive_c/users/crossover`. `scripts/launch_game.py` sets `USER` and `LOGNAME` to `crossover` for every Wine call it makes.
- **`-silent`.** The Steam UI renders as a black window under Wine because its embedded browser does not draw. `-silent` keeps the main window closed while the client still logs on and serves Steamworks. The client must be logged on before the game starts, or Steamworks fails to initialize. It cannot show a login prompt, so sign in through the macOS Steam client or CrossOver if the session expires.
- **`version.dll`.** MelonLoader needs `version=native,builtin`. `scripts/install_melonloader.py` sets it with `reg add` through the selected runtime's Wine; the game launch also passes it in `WINEDLLOVERRIDES`, along with the native DXVK DLLs.
- **Detaching.** `scripts/launch_game.py` starts Wine with `subprocess.Popen(..., start_new_session=True)`, so the game and Steam survive the task runner and a closed terminal. A trailing `&` does not work: Task's shell kills its background children when the task ends.

Shut Steam down with `wine 'C:\Program Files (x86)\Steam\steam.exe' -shutdown` (same `WINEPREFIX` and `USER`), never while the game is running, because that can break the Steamworks session and Cloud sync.

### Setting up a second machine

The repo does not create a prefix, and Steam cannot show a login prompt under Wine, so a second Mac gets its prefix by copying one that already works. Copy the prefix directory (the one that contains `drive_c`) to `~/.local/share/megabonk/wine` on the other machine, skipping what is volatile or not needed:

```sh
rsync -ah --stats \
  --exclude='/drive_c/Program Files (x86)/Steam/steamapps/common/<other game>/' \
  --exclude='/drive_c/Program Files (x86)/Steam/steamapps/appmanifest_<other app id>.acf' \
  --exclude='/drive_c/Program Files (x86)/Steam/logs/' --exclude='/drive_c/Program Files (x86)/Steam/dumps/' \
  --exclude='/drive_c/users/crossover/AppData/Local/Steam/htmlcache/' \
  "<source prefix>/" <host>:.local/share/megabonk/wine/
```

With only Megabonk kept, a prefix of about 12 GB copies as about 4.5 GB. The copy carries the Steam login, the saves, MelonLoader, the `version.dll` override and the DXVK DLLs, so `task wine:install` finds both steps up to date and `task game:steam` followed by `uv run scripts/run.py relaunch` works without a Steam login prompt. Steam allows one session per account: starting Steam from the copy signs the account out everywhere else, including the other machine's Steam and a native macOS Steam client. Copy while Steam is stopped when possible; a copy taken while it runs still booted, but the registry files can change underneath the copy. Check the result with `uv run scripts/game_paths.py` (it should print the new prefix) and `Latest.log` (`DevHarness: enabled`, then `Steamworks ready`, then `EditorMode: entered`).

This was verified on a second Apple silicon Mac (Wine 11.18, DXVK-macOS async, Rosetta): the game launched with MelonLoader, `relaunch` loaded the example Forest level into editor mode, and `screenshot` returned the editor overlay. The mod builds there with no extra setup, because the build reads the same prefix setting and default; see [modding-setup.md](modding-setup.md).

## Launching under CrossOver

Set `MEGABONK_MACOS_RUNTIME=crossover` to use CrossOver instead of plain Wine; `run.py relaunch` then starts the game through `task crossover:run`, and `task crossover:melonloader:install` installs MelonLoader with CrossOver's Wine. `task crossover:run` starts `Megabonk.exe` directly in the CrossOver Steam bottle with `cxstart`, with `SteamAppId` and `SteamGameId` set to 3405340. The Steam client must already be running in the bottle; start it from CrossOver first. Launching through the `steam://rungameid` URI is avoided because it can open only the CrossOver window without starting the game, especially from a script. The equivalent command:

```sh
game='C:\Program Files (x86)\Steam\steamapps\common\Megabonk'
SteamAppId=3405340 SteamGameId=3405340 \
  /Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/cxstart --bottle Steam --workdir "$game" "$game\Megabonk.exe" >/dev/null 2>&1 &
```

`cxstart` stays in the foreground until the game exits, so the task starts it detached and returns at once, before MelonLoader has loaded the mod. The detach is a `python3` `subprocess.Popen(..., start_new_session=True)`. A plain `&` in a Taskfile command does not work: Task's built-in shell kills its background children when the task ends, so the game would die right after launching. Python's own session also keeps the game alive if the terminal that ran the task is closed.

The two environment variables are required. A game started without them is not attached to Steam: Steam's `gameprocess_log.txt` shows no new tracking line, and `load-level` fails every time with `Steamworks is not initialized`, because the loader reads the app build id from Steamworks. With them set, a `load-level` sent right after launch can still fail once with the same error because Steamworks is not up yet; sending it again a few seconds later succeeds.

### Relaunching

Quit the previous launch before starting a new one. A second instance fights the first over the log file and the harness command folder, and a rebuilt mod DLL is only picked up on a fresh launch.

```sh
uv run scripts/run.py quit
```

For the usual test Forest editor session, use the single command below instead of manually sequencing quit, launch, load and editor commands:

```sh
uv run scripts/run.py relaunch
```

`quit` sends the quit command and then blocks until the game process has exited, so the next launch can follow immediately. It prints `quit: game exited` and exits 0. It exits 1 if the command is not accepted or the process is still alive after `--timeout` seconds (default 15), and it prints the remaining pids. If no game process is running it prints `quit: game not running` and exits 0, so it is safe to run before every launch. `run.py cycle` ends with the same quit-and-wait step.

Process detection uses the standard library only: `ps -axo pid=,command=` on macOS and Linux, `tasklist` on Windows (not exercised on a Windows host). A process counts as the game only when its command line starts with the game executable, `...\Megabonk.exe` under Wine or `Megabonk.x86_64` natively. Helpers that mention the executable, such as `winewrapper.exe`, `UnityCrashHandler64.exe`, `winemenubuilder.exe` and a shell running the launch command, are ignored. If `quit` times out because the game is hung, end it by the pid it printed.

### Launching from an automated session

To know when the mod is ready for commands, poll `MelonLoader/Latest.log` for the line `DevHarness: enabled` rather than for the process existing: MelonLoader takes several seconds to load after the process starts, and `Latest.log` is not truncated until that point, so an early read can see a stale line from the previous run. Run that poll as a background job (`run_in_background`, or `Monitor` as a self-ending loop) and wait for its own completion notice instead of a foreground `sleep`, which this harness blocks.

Caveats:

- `load-level` needs Steamworks, because the loader reads the app build id; see the launch section above for the environment variables that provide it.
- The game sees the host filesystem as the `Z:` drive. `run.py` rewrites host paths to `Z:\...` on macOS, so pass ordinary host paths.
- `ScreenCapture.CaptureScreenshot(path)` and `ImageConversion.EncodeToPNG` both fail inside Il2CppInterop in this game build, and `ScreenCapture.CaptureScreenshotAsTexture` is unusable for the same reason. The harness reads the finished frame with `Texture2D.ReadPixels` at the end of the frame and encodes the PNG itself (`png_encoder.cs`).
- The screenshot is the game's own frame at the game's render resolution, not a capture of the host screen.
- Localhost networking was not tested; the file-drop channel needs only `System.IO`.

## Freezing gameplay

`freeze` calls `MyTime.Pause()` and `resume` calls `MyTime.Unpause()`, the game's own time path, and each logs `MyTime.paused`. This is not `PauseUi.Pause()`, so no pause window appears in the frame. While frozen the run timer, enemies and the player stop, so an idle player cannot die. The harness still polls (MelonLoader's `OnUpdate` does not use the game's clock) and the screen still renders: clouds, grass and particles keep moving between two frozen screenshots, while the HUD timer, enemies and player do not.

Caveats:

- Freezing stops enemies as well, so it suits screenshots only and cannot stand in for a playthrough.
- Freeze after the settle wait, not before it: a level-up dialog that is already open stays open.
- Resuming continues the run from where it stopped.

## Camera pose

`camera` holds the camera at a world-space position and euler rotation in degrees (Unity convention: `rotation` `[90,0,0]` looks straight down). The game recomputes the camera each frame, so the mod stores the pose and re-applies it to `PlayerCamera.Instance.camera.transform` from `OnLateUpdate`, after the game's own update. Verified in the running game: the pose held for more than 6 seconds of live gameplay and while frozen.

On Forest, cell (x, z) is at world `(-280 + 40x, 20 * height, -280 + 40z)`, from `MapParameters.scaledTileWidth` and `scaledTileHeight`.

`camera-clear` restores the camera's local position and rotation saved when the override first applied. The game never rewrites that transform itself, so without the restore the camera would stay at the posed view.

Caveats:

- Fog hides the map from far above: at y=400 the frame is a flat blue field, at y=150 the map is washed out, and at y=60 it is clear. Pose within roughly 150 units of the ground.
- The player keeps playing under the override, so combine it with `freeze` for a still scene.
- The camera pose changes the picture only; use `invulnerable` to keep the player alive for an enemy playthrough.

## Player invulnerability

`invulnerable` gives the player 20 stacks of the game's own Mirror item (`EItem.Mirror`) and sets the item's `cooldown` and `minCooldown` to 0. Mirror stops a hit through `PlayerHealth.A_CheckStopDamage` and normally waits out a cooldown before it can stop the next one; with no cooldown it stops every hit. `vulnerable` removes the item and restores the Mirror amount the player had before. Each command logs `DevHarness: player invulnerable, Mirror amount=20.` or the `vulnerable` equivalent. Issuing the same command twice logs `already invulnerable` or `already vulnerable` and changes nothing. A new run builds a new inventory, so send `invulnerable` again after each `load`.

Verified in the running game on a mod-loaded Forest level: an idle player kept full HP and shield for 47 seconds of game time while kills went from 6 to 51. Setting only the stacks, with the default cooldown, was not enough: HP fell to 36/72 within 40 seconds.

Caveats:

- It is not a god mode. Damage that does not go through `A_CheckStopDamage` is still applied, and stronger enemies such as mini bosses can still kill the player. Which damage sources bypass Mirror was not enumerated.
- Mirror reflects damage back at the attacker, so enemies take damage from hitting the player.
- A surviving, idle player can still reach the level-up dialog, which pauses play and puts a window in the frame. `freeze` after the settle wait does not close it, so keep the settle time short or take the screenshot before the first level-up.
- The kill floor still wins. `KillFloorWatcher` ends a fall through `PlayerHealth.KillPlayer()`, which does not pass through the damage check. Verified with a level that removes every tile but one: the invulnerable player logged `KillFloor: player fell to y=-49.8, killing` and the run ended on the death screen.

## Kill-floor heartbeat

The kill floor (see "Kill floor" in [runtime-map-structure.md](runtime-map-structure.md)) logs a line for every actor it kills. The heartbeat adds a second line every 5 seconds that says what the watcher can see, which is what to read when something that should have died did not:

```text
KillFloor: watch enemies=26 stageBosses=1 lowestEnemyY=-69.03 lowestBossY=-66.47 bosses=['Enemy1(Clone)' id=18 y=-66.2 lowest=-66.4 inEnemies=True]
```

`enemies` is the size of `EnemyManager.enemies` and `stageBosses` the size of the manager's stage boss list. `lowestEnemyY` and `lowestBossY` are the lowest point (pivot or collider bottom, whichever is lower) any enemy or boss reached since the previous heartbeat, and each boss entry gives its id, pivot `y`, current `lowest` point, and whether it is also in `enemies`. A boss is only identified by id, because it has the same `Enemy1(Clone)` name as every other enemy.

It is off by default, because it adds a line every 5 seconds. Turn it on with `run.py heartbeat on` and off with `run.py heartbeat off`; both log `KillFloor: heartbeat on` or `off` and apply at once, including to a level that is already running. To start with it on, set `MEGABONK_KILL_FLOOR_HEARTBEAT` to `1` or `true` in the environment of the game process, for example in the `.env` that the taskfile reads or in front of the launch command. The variable is read once when the mod loads, and a later command overrides it. Verified in the game that the variable reaches the process under CrossOver.

The kill line itself always carries the actor's id, world position and `lowest` point, with `(still present, attempt N)` appended when an actor stays in the game after a kill.

## Position readout

With the harness enabled, a mod-loaded level draws monospace (`RobotoMono`) yellow text anchored under the game's minimap, left-aligned within a box whose right edge sits under the minimap's right edge (the minimap itself is flush with the screen's own top-right corner, so anchoring under its left edge instead would run new lines straight off-screen). The player's own line is labelled `me:`:

```text
me:        pos(120, 2, 3) floor -72
enemy: 4   pos(125, 2, -10)
```

Every line shares the same columns (label, id, then `pos(x, y, z)`), but the column widths are computed each refresh from what is actually on screen that refresh (`PositionReadout.Render`), not a fixed guess: the label column is as wide as the longest label shown (at least `me:`), the id column at least 3 digits (wider only if an id needs more, so ids don't jitter the column within a normal run), and each of x/y/z is as wide as that coordinate's widest current value. A value wider than its column still prints in full, only pushing what comes after it on that line; lines share these widths so the `pos` column lines up between them. `pos` itself is the world position rounded to whole units. `floor` on the player's line is the kill-floor height, and `BELOW FLOOR` is appended when an actor's position is below it (the kill floor uses the lower of the position and the collider bottom, so an actor can be killed a moment before its line is flagged). Boss-tier lines also carry the enemy's type name, directly after the position or the `BELOW FLOOR` flag with a single space — it is not column-aligned across lines, since reserving width for it on every line left large dead space when only one boss-tier actor was shown. The player's line is refreshed ten times a second, the actor lines four times a second.

It is drawn only when the harness is enabled and the level is mod-loaded, which is when the kill floor arms; a vanilla level or a disabled harness draws nothing. The label is a copy of one of the minimap's own direction letters, parented to the minimap root; its box is resized every refresh to the actual rendered text (`GetPreferredValues`), so it hugs the minimap instead of carrying a fixed width. If the minimap does not exist yet it logs `PositionLabel: no minimap found, readout not drawn` once and retries on the next tick; the log line `PositionLabel: created under the minimap` marks the first draw. The conversion and the text format are pure logic in `position_readout.cs`.

### Enemy kinds

Actors are classified by the game's own `EEnemyFlag` bits (`Elite=1, Boss=2, StageBoss=4, Challenge=8, SummonerMiniboss=16, FinalBoss=32`), read through `Enemy`'s public `IsElite()`/`IsBoss()`/`IsStageBoss()`/`IsFinalBoss()` methods (the raw field is private) and reduced by `ActorKinds.Of` in `actor_kind.cs`, most severe first: a final boss is never also shown as a stage boss, a stage boss or miniboss never as a plain elite. A stone golem and the other miniboss types (`MinibossGolemSand`, `MinibossScorpion`, `MinibossPig`, …) are spawned through `EnemyManager.SpawnBoss` with the `Boss` bit, the same bit a one-off boss carries, so `IsBoss()` alone is enough to classify them as `miniboss`; `EEnemyFlag.SummonerMiniboss` has no public getter and was not observed set on a spawned miniboss.

| Kind | Label | Always listed | Shows the enemy type |
| --- | --- | --- | --- |
| Final boss | `final boss:` | yes | yes |
| Stage boss | `boss:` | yes | yes |
| Miniboss | `miniboss:` | yes | yes |
| Elite | `elite:` | up to 3, nearest/below-floor first | no |
| Ordinary enemy | `enemy:` | up to 3, nearest/below-floor first | no |

Final bosses, stage bosses and minibosses are always listed (read from `EnemyManager.stageBosses` first, then any other boss-tier actor found walking `EnemyManager.enemies`, deduplicated by id); boss-tier lines append the enemy's `EnemyData.enemyName` (e.g. `MinibossGolem`) after the position. Elites and ordinary enemies each go through their own `NearbyEnemySelector` (`nearby_enemy_selector.cs`): below the kill floor first, then the rest ordered by horizontal distance (x and z) to the player, ties by lower id, capped at 3 each. With hundreds of enemies alive the readout stays bounded (boss tier plus at most 6 more lines).

The selectors reuse fixed buffers, so a refresh allocates only the few strings it shows. With about 400 enemies a refresh took 0.6 to 1.4 ms and allocated 3 to 5 KB, four times a second; nothing runs on every frame.

Verified in the running game: the player's `pos` tracked the player through a level with tiles removed, and a miniboss spawned by a scratch probe calling the game's own `SummonerController.EventMiniboss` showed `miniboss … MinibossGolem` with `IsBoss()` true. A boss spawned by the boss portal, a final boss, and elites were not exercised.

### Cell-change log

The grid cell, height level and `outside` text are not drawn on screen; a harness-gated toggle logs them instead, mirroring the kill-floor heartbeat. Off by default, turned on with `run.py cells on` and off with `run.py cells off` (both log `PositionLabel: cell log on` or `off` and apply at once), or started on with `MEGABONK_CELL_LOG` set to `1` or `true` in the game process's environment (read once at mod load; a later command overrides it).

When on, it logs one line per actor whenever that actor's cell or height level changes (not every tick): the player under the name `me`, and every boss-tier actor under its label, id and type name:

```text
PositionLabel: me cell (10,7) h0 pos (120, 2, 3)
PositionLabel: miniboss 41 MinibossGolem cell (11,7) h1 pos (157, 16, 3)
```

`outside` follows the cell when the position is outside the tile grid, as before. The grid size and spacing are read from the live tile grid and `MapParameters` when the level is armed, so it is not tied to the 15x15 Forest map. Change tracking is pure logic in `cell_change_tracker.cs`.

Caveats:

- The kill floor kills the player within a quarter of a second of crossing the floor, so `BELOW FLOOR` is on screen only for those few frames and was not captured in the running game.
- Cell and height level come from an actor's transform, not from the tile under it, so on a slope or while falling they are an approximation.

## Not covered

The harness does not press menu buttons or open the level-up dialog. Only `state`, `teleport` and `dismiss-levelup` return data; the other commands report success or failure and nothing else, and `state` does not report health, inventory, enemies, the level-up dialog or the edit stack. Use `freeze` to stop an idle player dying during a screenshot, or `invulnerable` when enemies must keep moving.

## Character selection

A level started through the mod (`LevelLoaderPatch.LoadAndStart`, used by F6 and `load-level`) spawns Tony McZoom. The loader assigns the static `CharacterMenu.selectedCharacter` (ECharacter 13) just before `MapController.StartNewMap`; the player spawn reads that static, so no `RunConfig` field is involved. `Preferences.selectedCharacter` is the saved setting and is never written: after a mod-loaded run `Saves/LocalDir/config.json` still holds the player's own choice.

If the assignment throws, `CharacterOverride.TryApply` returns a warning that the loader logs, and the run starts with the character the menu last selected. The id lives in `character_override.cs` and mirrors `ECharacter.TonyMcZoom` in the il2cpp dump.

To confirm which character spawned, run `run.py cycle` and read the screenshot; the saved character in `config.json` differs from the one on screen when the override works.

## Python tests

The tooling scripts under `scripts/` are covered by pytest tests in `tests/` (the C# tests live in `tests/MegabonkLevels.Tests`). `task scripts:test` runs them, and `task test` runs them after the C# tests. `pytest.ini` at the repo root sets `testpaths = tests` and puts `scripts/` on the import path, so a test does `import game_paths` directly and no `pyproject.toml` is needed.

`tests/conftest.py` has an autouse fixture that removes every `MEGABONK_*` environment variable and points `game_paths.ENV_FILE` at a nonexistent file for each test, so a developer's shell or `.env` (for example `MEGABONK_WINE_PREFIX`) cannot change a result. A test that needs a setting sets it with `monkeypatch.setenv` or passes `env_file_values` to the function under test. Async tests use `@pytest.mark.anyio`; the conftest pins `anyio_backend` to `asyncio`, so no trio dependency is needed.

`pytest`, `python-decouple` and `mcp` are not in a lockfile. The `--exclude-newer` date on the `uv run` line in `taskfile.yml` fixes what `uv` resolves, the same way the PEP 723 headers of the scripts do, so move that date forward deliberately when updating the dependencies.

## Reading the game's code

Megabonk is an Il2Cpp build, so there is no managed IL to decompile anywhere in the install. Both sets of assemblies that look decompilable are stubs:

- `MelonLoader/Il2CppAssemblies/*.dll` are Il2CppInterop proxies. Every field is a `NativeFieldInfoPtr_*` and every method a `NativeMethodInfoPtr_*` thunk that calls into native code.
- Il2CppDumper's `.tools/il2cpp_dump/DummyDll/*.dll` are metadata shells: real signatures and `[Address(RVA = ...)]` attributes, but every method body is empty.

Running a decompiler on either returns that scaffolding and never game logic. The check takes seconds, and is worth doing before planning any work around "reading the implementation":

```sh
ilspycmd -t MyTime "<game dir>/MelonLoader/Il2CppAssemblies/Assembly-CSharp.dll" | head -20
```

A wall of `NativeFieldInfoPtr_`/`NativeMethodInfoPtr_` declarations, or a body of `{ }`, means there is nothing further to extract from that file.

What to read instead:

| Question | Where to look |
| --- | --- |
| A type's fields, method signatures, enum values, attributes | `.tools/il2cpp_dump/dump.cs`, regenerate with `task re:dump` |
| A string constant | `.tools/il2cpp_dump/stringliteral.json` |
| What a method actually does | Native code in `GameAssembly`, in Ghidra (see "Ghidra" below) or Binary Ninja, at the RVA listed above the method in `dump.cs` (also on `DummyDll`'s `[Address]` attribute) |
| A value set in the Unity editor rather than in code | Nowhere in the dump — confirm it in the running game |

`dump.cs` is the complete managed surface and answers most questions on its own, which is why it is worth grepping first; dropping to Binary Ninja is for the cases where the shape of a type is not enough and the actual logic matters.

That last table row covers a whole class of behaviour that is not in code at all. Serialized ScriptableObjects, scene and prefab data are not emitted by the dumper, so the game's Rewired key bindings live in an input-manager asset: `MyInputManager`'s action names (`Jump`, `Interact`, `MapOverlay`, and the rest) are plainly visible in `dump.cs`, but which physical key each action binds is not recorded anywhere the dump can see. Questions of that shape get settled by trying it in the game, not by reading harder.

### Ghidra

Ghidra is available as an alternative to Binary Ninja for reading `GameAssembly`. `task ghidra:install` downloads the pinned release into `$HOME/.local/opt/ghidra`, points `$HOME/.local/opt/ghidra/current` at it, and on macOS builds the native components (decompiler, sleigh) with the bundled Gradle wrapper, because the macOS release ships without them. Every step checks its result first, so re-running is a no-op once everything is in place. `task ghidra:run` installs if needed and launches the GUI.

Ghidra 12.1 needs Java 21 or newer. The tasks use the `java` pinned in `.tool-versions` through mise, and `JAVA_HOME` is set per command rather than globally. The version is pinned in `taskfiles/ghidra.yml` (`GHIDRA_VERSION`, `GHIDRA_DATE`); a new version installs beside the old one and `current` moves to it. The first GUI launch may quarantine the locally built natives under Gatekeeper; clear it with `xattr -dr com.apple.quarantine "$HOME/.local/opt/ghidra/current/"`.

#### Using Ghidra through REA

The REA MCP server (`rea` tools: `open_binary`, `analyze_function`, `procedure_pseudo_code`, `xrefs`, and the rest) has a Ghidra provider that runs headless Ghidra against a target. It stays `not_configured` until `GHIDRA_INSTALL_DIR` and `JAVA_HOME` are set, which Claude Code passes on to the REA process. The variables are in the `env` block of the committed `.claude/settings.json`, so they apply only to sessions started in this repo:

| Variable | Value |
| --- | --- |
| `GHIDRA_INSTALL_DIR` | `$HOME/.local/opt/ghidra/current` as an absolute path, so a version bump in `taskfiles/ghidra.yml` needs no change here |
| `JAVA_HOME` | the output of `mise where java`, a JDK 21 or newer (REA rejects a JRE or a 32-bit JDK) |
| `REA_GHIDRA_STARTUP_TIMEOUT_MS` | `3600000`. REA's default deadline for import plus auto-analysis is 330000 ms (5.5 minutes), and `GameAssembly.dll` did not finish within it |
| `GHIDRA_HEADLESS_MAXMEM` | `6G`. REA passes this as the headless JVM's `-Xmx`, falling back to `GHIDRA_MAXMEM` and then `2G`; an Il2Cpp binary has a very large function count, and the machine has 16 GB |

The values are absolute paths for the macOS machine this was set up on (`$HOME` and command substitution are not expanded in `settings.json`), so another machine, including the Linux host, needs its own values in `.claude/settings.local.json`, which overrides the committed file and is gitignored. `JAVA_HOME` also has to be updated when the `java` pin in `.tool-versions` changes. Restart Claude Code after changing either value. Check the setup, outside Claude Code, with `GHIDRA_INSTALL_DIR=... JAVA_HOME=... npx -y rea-agents@6.7.0 doctor --provider ghidra --json` (match the version in the `rea` entry of `~/.claude.json`): the `ghidra`, `ghidra-version`, `ghidra-headless`, `ghidra-native_decompiler` and `ghidra-java` checks should all be healthy.

`REA_ANALYSIS_PROVIDER` is deliberately unset. The same REA server also has a Hopper provider (`HOPPER_LAUNCHER_PATH`), so pass `provider_id: "ghidra"` to `open_binary` to bind Ghidra, and `binary_session` shows which provider is bound. The first import of `GameAssembly.dll` runs Ghidra's full auto-analysis and can take several minutes; REA serves operations only once that finishes. Names and comments set through REA (`annotate_native_function` and the like) live in a session database that is discarded on close, so use the Ghidra GUI project when labels have to persist. The `GameAssembly.dll` to open is in the game directory (see "Enabling"); RVAs from `dump.cs` are offsets from the image base.

REA's documentation describes Ghidra with PE files only on Windows x64, so running it on `GameAssembly.dll` under macOS arm64 is not a documented configuration. What was observed (52 MB `GameAssembly.dll`, 16 GB machine, Ghidra 12.1.4, default 2G heap and 330 s deadline): the PE loader recognised the file as `x86:LE:64:windows` and found its TLS callbacks, the 15 imported Windows libraries were reported "not found in project" (expected, they are not imported), and the first query (`analyze_function` at the `dump.cs` VA of `MyTime.Pause`) failed with `provider_timeout` after 330 s while still analysing. `open_binary` itself returns at once and does not start the work; the first operation does, so that call is the one that waits.

Outcome on a 64 GB arm64 Mac (Ghidra 12.1.4, `REA_GHIDRA_STARTUP_TIMEOUT_MS=3600000`, `GHIDRA_HEADLESS_MAXMEM=16G` from `.claude/settings.local.json`): it works. The first `analyze_function` (`MyTime.Pause`, VA `0x1803E5B20`) was moved to the background by the client after 120 s and finished roughly 12 minutes after `open_binary`; Ghidra's own log reports `Total Time 713 secs` for auto-analysis, dominated by Decompiler Switch Analysis (177 s), Non-Returning Functions - Discovered (156 s), x86 Constant Reference Analyzer (98 s), Stack (95 s) and Disassemble Entry Points (70 s). No analyzer was disabled. Later queries on the same session returned in seconds, and `batch_decompile` of ten functions at once was fine; a single `analyze_function` result can exceed 140,000 characters, so the client saves large results to a file and they are best read with `jq` on the `normalized_result.pseudocode` field.

The pseudocode is usable but unnamed. `GameAssembly.dll` has no symbols for the managed methods, so every function is `FUN_<va>` and every static is `DAT_<va>`. `MyTime.Pause` decompiles to: lazy class-init guard (`FUN_1802696c0` on the class handles), a write of `1` into the first byte of the `MyTime` statics block (`paused`), a call to `FUN_18232cd10(2, 0)` (the dump places `Physics.set_simulationMode` at RVA `0x232CD10`), and a tail call through a delegate stored at statics offset `0x30` (an Action event). Two things make the output readable. First, map each `FUN_1xxxxxxxx` to a dump entry by subtracting `0x180000000` and looking the result up as `RVA: 0x...` in `.tools/il2cpp_dump/dump.cs`; most callees resolve to a managed method name that way (Unity icalls such as `Component.get_gameObject`, `GameObject.SetActive`, `Time.get_time`, and game methods alike). Second, Il2Cpp field accesses show as raw offsets (`*(longlong *)(param_1 + 0x48)`), which match the `// 0x48` offsets printed beside each field in `dump.cs`. Recurring noise to ignore: the `if (DAT_1831... == '\0') { FUN_1802696c0(...) }` blocks at the top of each function (lazy class initialisation), `il2cpp_runtime_class_init` checks, and `FUN_180269910` (null-reference exception thrower) after a failed null check. Shared RVA `0x3321E0` in `dump.cs` is one empty stub reused by many unrelated methods (it resolves to `SecurityParser.OnStartParsing` in a name lookup); a method listed at that RVA has no body of its own.

Observed limits. A procedure given as `0x18054F110` (`LevelupScreen.Open`) failed with `invalid_request` ("File offset ... has no loaded source mapping") in a batch and, retried by name, with "Unknown Ghidra procedure name or address"; Ghidra did not create a function at that address, and the method sits 16 bytes before the next method, so it is probably a tiny stub. Addresses in `dump.cs` order are otherwise accepted as lowercase or uppercase `0x` hex VAs.

Snapshot: `close_binary` with `snapshot_path` set to `.tools/GameAssembly/ghidra.rea-snapshot` succeeded without any annotation made first. The file is 616,732 bytes and reports 1 primitive entry, 4 workflow entries and 5 evidence records, so it holds the evidence for the queries made in the session rather than a database of the full analysis. Whether importing it through `open_binary`'s `snapshot_path` avoids the 12-minute analysis for a function that was not queried before is untested. `.tools/` is gitignored, so the snapshot is local to the machine.

If analysis ever fails or runs impractically long, `REA_GHIDRA_DISABLED_ANALYZERS` (comma-separated exact analyzer names) skips analyzers, and the Ghidra GUI project (`task ghidra:run`) keeps its analysis between sessions instead of redoing it per REA session. A `provider_timeout` is retryable: `close_binary`, then `open_binary` again.

## Player teleport

Confirmed in the running game (CrossOver, Forest level). The player is a `MyPlayer` (static `MyPlayer.Instance`) with a `PlayerMovement playerMovement` field (`0x28`), a `PlayerRenderer playerRenderer` (`0x20`) and a `PlayerInput playerInput` (`0x48`). `PlayerMovement` is a Rigidbody controller (`private Rigidbody rb` at `0x48`, `CapsuleCollider playerCollider` at `0x140`, `float playerHeight` at `0x104`), not a `CharacterController`.

| Method | RVA | Signature |
| --- | --- | --- |
| `MyPlayer.TeleportPlayerImmediate` | `0x4B6E00` | `void TeleportPlayerImmediate(Vector3 position, Vector3 dir, Vector3 cameraDir, float cameraPitch = 20)` |
| `PlayerMovement.TeleportPlayer` | `0x343A80` | `void TeleportPlayer(Vector3 pos)` |
| `PlayerMovement.TeleportPlayerBackToBounds` | `0x343870` | `void TeleportPlayerBackToBounds(Vector3 pos)` |
| `PlayerMovement.VerifyPosition` | `0x344220` | `private void VerifyPosition()` |

Call sequence that worked, on the main thread: `MyPlayer.Instance.TeleportPlayerImmediate(position, me.transform.forward, me.transform.forward, 20f)`. It calls `PlayerMovement.TeleportPlayer(position)`, which writes the Rigidbody position and zeroes its velocity, then `PlayerRenderer.ForceRotation(dir)` and `PlayerInput.SetSpawnDirection(cameraDir, cameraPitch)`. `me.playerMovement.TeleportPlayer(position)` alone also works and leaves facing untouched.

- The call does not change `transform.position` in the same frame. The new position is visible on `MyPlayer.Instance.transform.position` after about a second at most (the Rigidbody position reaches the transform on the next physics sync), so a command has to wait a few frames before reading the position back.
- `position` is the feet point: the body lands at `position.y + 1.925` (half `playerHeight`) on the pivot, so `(120, 0, 80)` on flat ground settles at `y = 1.925`, the same as the spawn pose. Pass the ground height, not the centre height.
- Live physics applies afterwards: a target above the terrain falls, and a target over a lower tile ends up at the bottom of that fall. Teleporting to cell centre `(-200, 0, 200)` in the live game ended at `y = -11` after sliding down a slope. While frozen (editor mode or `freeze`), the body is placed but does not fall.
- Writing `MyPlayer.Instance.transform.position` directly does not work in a live run: the Rigidbody overwrites it within a frame (set to y 15, read back at 1.925). While frozen it sticks, which is not useful because the physics body stays at the old place.
- A target far below the map is not reverted by `VerifyPosition`. A teleport to `y = -100` was left in place and the kill floor then fired (`KillFloor: player fell to y=-98.2, killing`), after which the run is over and `MyTime.paused` is true. A harness teleport must not target below the kill floor.
- The camera follows with no extra call: a screenshot taken after a 40-cell jump showed the player centred on the new position in the game camera.
- Enemies are not moved. Enemies that spawn afterwards appear around the new position (the position label listed three enemies within 30 units a few seconds after a jump to `(-200, 0, 200)`); whether enemies that were already chasing the player at the old position are culled or walk over was not observed.

Open questions about the teleport:

- One teleport sent right after `run.py relaunch` (frozen in editor mode, target `(-200, 0, 200)`) was not applied at all after 5 seconds, while the same call minutes later was. It did not reproduce; the cause is unknown.
- What happens to enemies already chasing at the old position.

The `teleport` command takes exactly one of `position` (world `[x, y, z]`, the feet point) or `cell` (`[cx, cz]`, the same grid as `state`). A cell resolves to the cell centre with `PositionReadout.CellCentre` and the tile surface there (`TeleportTarget.CellStandingPoint`); an empty cell keeps the player's current feet height. Spacing and tile height come from the running level, so a cell teleport needs a loaded custom level. It rejects, with `ok:false` in the result file: no player, a cell outside the grid, a cell given to a game with no level grid, a target below the kill floor, both or neither of `position` and `cell`, and arrays of the wrong length. The result is `{"position":[x,y,z],"cell":[cx,cz]}` (`cell` is `null` without a grid), read from the player's Rigidbody straight after the call, so it is the body position (feet plus `1.925`) at the moment of the teleport, before any fall. `state` agrees with it once the transform syncs.

## Level-up dialog

Confirmed in the running game. The level-up window is `LevelupScreen : BaseEncounterWindow`, owned by `EncounterWindows` (field `levelupScreen`, `0x20`). `LevelupScreen.upgradePicker` (`0x48`) is an `UpgradePicker` whose `UpgradeButton[] buttons` (`0x20`) hold the offers; there were 4 buttons. An `UpgradeButton` keeps `IUpgradable upgradable` (`0xA8`), `bool isItem` (`0xC8`), `ERarity rarity` (`0xD8`) and `TextMeshProUGUI t_name` (`0x60`). The interop proxies expose the private fields.

| Method | RVA |
| --- | --- |
| `EncounterWindows.AddEncounter(EEncounter)` | `0x3DF700` |
| `UpgradeButton.SelectUpgrade()` | `0x55F0A0` |
| `UpgradePicker.SelectUpgrade(IUpgradable, List<StatModifier>, UpgradeButton, ERarity)` | `0x561500` |
| `PlayerInventory.AddUpgrade(IUpgradable, List<StatModifier>, ERarity)` | `0x4DFD80` |
| `EncounterWindows.RewardFinished()` | `0x3E09D0` |
| `LevelupScreen.OnClose()` | `0x54F040` |

Detecting an open dialog: `LevelupScreen.isLevelingUp` (static bool) is true while the level-up window is open, and `EncounterWindows.encounterInProgress` is true for any encounter window. Both were false at rest, true after the window opened, and false after a choice. `MyTime.paused` is true while the window is open.

Finding the objects: `UnityEngine.Object.FindObjectOfType<EncounterWindows>()` and `FindObjectOfType<LevelupScreen>()` both return the live instances; no static accessor is needed.

Choosing without a click, which worked: with `LevelupScreen.isLevelingUp` true, `var button = FindObjectOfType<LevelupScreen>().upgradePicker.buttons[i]; button.SelectUpgrade();`. The same call opened and answered in one frame also worked, so the banish cooldown did not block it. Afterwards `isLevelingUp`, `encounterInProgress` and `MyTime.paused` were all false, and the chosen upgrade was in the player's inventory (a Bow offered as a new weapon appeared in the HUD at `LVL 1`, then `LVL 2` on a second pick). The button's name is `button.upgradable.GetName()` (same as `button.t_name.text`) and its rarity was `New` for the new weapon. With no dialog open `upgradePicker.buttons` is empty, so indexing it throws `IndexOutOfRange`; check `isLevelingUp` first.

To open the dialog for a test, `FindObjectOfType<EncounterWindows>().AddEncounter(EEncounter.Levelup)` (`EEncounter.Levelup` is `0`) opens it at once and sets `isLevelingUp`. It does not change `PlayerXp.level`.

Interaction with the editor freeze: choosing an upgrade runs `LevelupScreen.OnClose`, which calls `MyTime.Unpause()`. While editor mode was on and the run was frozen, a choice left `editor` true but set `frozen` (`MyTime.paused`) to false, so the editor session's freeze was lost and enemies resume. A harness command that dismisses the dialog during an editor session has to call `MyTime.Pause()` again afterwards.

The `dismiss-levelup` command does the choose-without-a-click sequence above: `choice` is a zero-based index into the offers (default 0, negative or non-integer rejected at parse time), and the result is `{"dialogWasOpen":true,"chosen":"<upgrade name>"}`. With no dialog open it succeeds with `{"dialogWasOpen":false,"chosen":null}` and changes nothing. A `choice` past the number of offers is rejected with `ok:false` and the error `choice N is out of range; the dialog offers M upgrades`, and the dialog stays open (confirmed in the running game). It calls `MyTime.Pause()` again after the pick when editor mode is active. Confirmed in the running game: a natural level-up reported `dialogWasOpen:true` with `chosen:"Dice"`, and a second call then reported `dialogWasOpen:false` with `frozen:false` in `state`. The harness has no command to open the dialog, so a test waits for a level-up.

Open questions about the level-up dialog:

- Whether `UpgradePicker.AutoSelectUpgrade()` alone leaves an open dialog behind; it was not called.
- Whether item offers (`isItem` true) and the banish and refresh modes behave the same through `SelectUpgrade`; only upgrade offers were tried.

Result fields for a harness dismiss command: `wasLevelingUp` and `isLevelingUp` (before and after), `chosen` (index), `name` (from `GetName()`), `rarity` (the `ERarity` name), `frozenBefore` and `frozenAfter` (`MyTime.paused`), and `playerLevel` (`MyPlayer.Instance.inventory.playerXp.level`). A call with no dialog open returns `ok:false` with an error rather than throwing an index error.

## Editor mode

Editor mode is a freeze-and-fly overlay for surveying a map while a run is active. It works in any run, not only mod-loaded levels. Toggle it with F8, or with `run.py editor on` and `run.py editor off` when the harness is enabled (the harness cannot press keys). F8 is ignored while the game's debug console (F10) is open and while no run is in progress. The game's own `LookHorizontal` and `LookVertical` Rewired axes read zero while the run is paused, which is why look uses Unity's raw mouse axes. Rewired's key bindings live in a serialized asset that is not readable from code, so that F8 collides with no game binding is only confirmed by pressing it in the game.

Entering calls `MyTime.Pause`, which stops the run timer, enemy spawning, enemies and the player, and detaches the camera from the player. The camera is the game's own `PlayerCamera` camera, rewritten from `OnLateUpdate` the same way the harness `camera` command does it, so no second camera exists to stack across cycles. The free-fly pose starts as a zoomed-out overview of the player (`FreeFlyCamera.OverviewPose`): 60 units above the player and back along +Z, pitched down 40 degrees and facing -Z, so the player is centred, +X runs to the screen's left and the view stays a fixed, near-isometric angle whatever way the game camera was facing.

| Input | Effect |
| --- | --- |
| W, A, S, D | Move along the view direction and sideways |
| Space, Left Alt / Right Alt (Option) | Move up and down in world space |
| Left Shift | Move 4 times faster |
| Mouse move while the right button is held, after pressing it off the palette | Look, read from Unity's raw `Mouse X` and `Mouse Y` axes and scaled by the game's saved mouse sensitivity and axis-invert settings, so it turns 10% faster than normal play |

Exiting clears the camera override, which restores the camera's local pose saved before entry, and calls `MyTime.Unpause` only if the game was running when editor mode was entered. Entering while the game was already paused (a level-up dialog, for example) leaves it paused on exit. If the run ends while editor mode is active, the mode exits on the next frame. Entering and leaving log `EditorMode: entered` and `EditorMode: exited` with the resulting `MyTime.paused`.

The look rate was measured in normal play with a probe comparing `Mouse X` against the player's `PlayerInput.cameraRotation`: the player turns 1 degree per raw mouse unit at a saved `sensitivity` of 1.0, with the same sign convention as editor mode. The sensitivity and the `inverted_horizontal_axis` and `inverted_vertical_axis` flags are read from `SaveManager.Instance.config.cfControlSettings` each time editor mode is entered. Editor mode multiplies the saved sensitivity by 1.1 because the exact normal-play rate felt sluggish when flying with the right button held. Movement speed (60 units per second, 4 times that with Shift) is a fixed choice, not read from the game.

## Catalog palette

While editor mode is active a panel on the left edge lists the placeable prefabs of the loaded map (`MapController.currentMap`). Entering editor mode releases the cursor lock and shows the cursor; leaving restores the lock and visibility the game had. Because the cursor is free, look only applies while the right mouse button is held. Pressing it with the pointer on the panel does not start a look, but a sweep that starts off the panel keeps turning when the pointer crosses it.

The entries come from the game's own prefab catalog, walked by `CatalogPrefabs` (the same code live editing uses to resolve a `catalogId` to a prefab): every `StageData.randomMapObjects[].prefabs[]`, `stageTilePrefabs.flatTilePrefabs[]` and `mapSpecificTilesPrefabs[]` of every stage of the map, `MapData.shrines[]`, and the `SpawnInteractables` `chest`, `chestFree` and `rails[]`. `PaletteCatalogBuilder` turns the counts into `catalogId` strings in the shapes documented in `level-format.md`, grouped by stage and category. `MapData.randomObjectsOverride` has no `catalogId` shape and is not listed.

Entries have no thumbnail. Each row shows the prefab's GameObject name, falling back to a label such as `Random object 1/0` when the name is blank. Rendering prefabs to textures was left out because it needs an off-screen camera and lighting per prefab for little gain over the name.

Clicking a row selects it, scrolling the wheel over the panel scrolls the list, and the panel title shows the current selection. Clicks and scrolling are read from Unity's `Input` directly instead of through a UGUI `EventSystem`, so the game's Rewired input module is untouched. The selection is `EditorPalette.Selection.Current`, a `CatalogId`, with a `Changed` event; the placement tool reads it from there. The palette is rebuilt each time editor mode is entered, so it follows the map; a selection that is not in the new map's entries is cleared. Building logs `EditorPalette: built <n> entries for <map>`.

## Tile tools

While editor mode is active a toolbar at the top centre of the screen shows six tools and a detail line. The digit keys 1 to 6 select Raise, Lower, Slope, Remove, Place and Select (the last two are in "Object tools" below); Select is active on every entry, so the first click edits nothing until an object is pressed; the previous choice is not kept. Pressing 1 to 4 in normal play does nothing, so the game binds no action to them (confirmed in the game, like F8).

The targeted tile is the one under the mouse pointer. A ray from the camera through the pointer is cast against the baked ground collision (`ProceduralTileGeneration.collider`, see "Ground collision after edits" in [runtime-map-structure.md](runtime-map-structure.md)) only, so enemies, props and the player never block it. The hit point is stepped 0.01 units into the surface before it is converted to a cell with `PositionReadout.CellOf`, so a hit on a side wall targets the tile the wall belongs to. A yellow outline traces the targeted tile's top surface, following the ramp on a slope. Nothing is targeted while the pointer is over the palette, outside the grid, or over a removed cell.

A left click applies the selected tool to the targeted tile:

| Tool | Edit |
| --- | --- |
| Raise | `SetTileHeight` one level higher |
| Lower | `SetTileHeight` one level lower; nothing at the lowest level the generator produced on the map (Forest seed 20261007 runs from -3 to 2) |
| Slope | `SetTileSlope` to the next of North, East, South, West, flat |
| Remove | `RemoveTile` |

The op goes through `LiveEditPatch.ApplyLive`, which runs it through a `LiveEditPlanner` (an `EditStack` on the generated grid plus every edit so far, including a loaded level file's) and applies the resulting action with the same applier, fill regeneration and collision rebuild a level file uses at load. Each click logs `EditorTileTools: <tool> (x,z) -> <opType>`. There is no tool to add a tile: a removed cell has no collision to aim at, and undo will restore it. Removing a tile does not yet build walls around the hole, so the sky shows past the neighbours' edges; this is open for both editor and level-file removals.

The tools work in any `Tiles`-map run, not only mod-loaded levels, but the kill floor is armed only on mod-loaded levels; in a vanilla run a fall through a removed tile lands on the game's own catch floor. Pure logic lives in `tile_tool.cs` (what each tile tool emits), `editor_tool.cs` (tool list, hotkeys, toolbar text) and `tile_outline.cs` (the outline corners).

The same toolbar now owns the editing loop controls:

| Control | Effect |
| --- | --- |
| `Undo` button or `Ctrl+Z` | replays inverse ops through the same live path as normal edits (terrain/object applier, fill regeneration, collision rebuild), and removes the last edit from the current save history |
| `Redo` button or `Ctrl+Y` | reapplies the undone edit through the same live path and returns it to save history |
| `Validate` button | runs `ReachabilityValidator` from the live spawn portal cell (name contains `portal` + `spawn`, not `boss`), draws a red outline on each unreachable tile, and reports boss-portal reachability separately (boss portal found dynamically by object name containing `boss` + `portal`, excluding `spawn`) |
| Save row (`name` + `Save`) | writes `<name>.mblevel.json` to `<game>/UserData/Levels/` using `LevelFileSerializer`, with map/stage/tier/seed from the current run plus the full current edit history. By default `Save` writes into the file selected in the `levels/UserData` overlay (the save-name form mirrors the selected file). |
| `Save+Load` | saves first using the current name field, then loads that same file and requests editor auto-re-enter |
| `Load` and right-side list | browses `.mblevel.json` files in `<game>/UserData/Levels/` (case-insensitive sort); click a row or scroll while hovering over the list to select it, which also copies its file stem into the save form; `Load` starts that file through `LevelLoaderPatch.LoadAndStart` and editor mode then auto-re-enters once the new run is active |

Validation overlays are explicitly stale after any edit/undo/redo and are cleared until `Validate` is pressed again.

The status line also shows `save: saved|dirty` with the current edit count. `Load` is not blocked when unsaved edits exist; it immediately starts the selected file's map, stage, tier, and forced seed while handing its edit history to the generation pipeline, so the loaded level is applied on the new run.

## Object tools

Tool 5 (Place) and tool 6 (Select) edit objects. Both place at the cursor's ground point, not snapped: the point is kept inside the targeted cell (clamped to its edges), measured from the same origin as `PositionReadout.CellOf` (via `PositionReadout.CellCentre`). The height is the tile surface at that point (`Height * tileHeight`; on a ramp it rises a full level from the downhill edge to the uphill edge). `tileHeight` and the spacing are read from the live `StageData.mapParameters`. The yellow tile outline shows the targeted cell. While Place is active, or Select has an object selected, thin white lines draw a quarter-tile grid (spacing / 4, 10 units on Forest's 40-unit tiles) over that cell as a visual guide, and, in Place only, an orange circle marks the exact placement point; objects do not snap to the lines.

An identical object cannot be stacked: placing or moving an object is ignored, with a log line, when an object of the same prefab name already stands at the same position (within 0.01 on every axis, generator-spawned or editor-placed). Different objects may share a position.

| Tool | Input | Edit |
| --- | --- | --- |
| Place | left click on a tile with a palette item selected | `PlaceObject` at the cursor point; rotation is the prefab's pitch and roll with yaw set to the camera's yaw plus 180 degrees rounded to 90, so the object faces the camera (assumes a prefab's front is +Z; unconfirmed); scale is the prefab's local scale |
| Select | press an object | selects it (red circle on the ground beneath it, centred on its combined renderer bounds and centred on the object's origin and sized to 40% of the larger horizontal half-extent of its mesh renderers, so a tree's ring sits at its trunk and does not cover neighbours); pressing where nothing is picked deselects |
| Select | keep holding for 0.2 seconds, move, then release | the object is picked up and follows the cursor as a preview, keeping the offset at which it was grabbed, then one `MoveObject` to the release point, keeping rotation and scale; releasing over the palette or off the grid, onto an identical object, or without moving puts it back and makes no edit; a press released before 0.2 seconds only selects |
| Select | `R` / `Shift+R` | `MoveObject` with yaw 90 degrees clockwise / counter-clockwise, keeping pitch, roll and position |
| Select | `Delete` or `Backspace` | `RemoveObject` |
| any | middle click an object | pick block: selects the object's palette entry and switches to Place |

Picking tries a physics raycast first and accepts the hit only when its hierarchy resolves to an indexed object in an `object:*` category or to an editor-placed object; tiles, walls, fill pieces and `tileObject` scenery (ForestParticles and the like, whose renderer bounds span the map) never resolve and so never get a ring. When that finds nothing, the pickable object nearest the cursor's ground point on the XZ plane within half a tile is used. The log line names the path (`raycast` or `nearest`). Selection clears when the tool changes. Nothing is picked or placed while the pointer is over the palette.

Pick block scrolls the palette to the picked entry when it is outside the visible list. It matches a generator-spawned object's prefab name (the `object:{prefabName}:{index}` genId category) against the palette's display names, preferring the current stage's entry, then a stage-independent one (shrines, interactables). An editor-placed object uses the catalogId it was placed with. An object with no matching entry, including every `tileObject`, is logged (`pick block found no palette entry`) and the selection is left alone.

Every action logs `EditorObjectTools: <what> -> <opType>`. Object removal now deactivates the live object (rather than destroying it), so undo/redo can restore the same object identity by toggling it active through a move action. Pure logic lives in `object_tool.cs` (position, grid lines, stacking, facing, the ops), `palette_scroll.cs` (palette scroll offset), `object_picker.cs` (nearest object) and `palette_pick.cs` (pick block lookup).

### Key, mouse and type commands

These commands feed `EditorInput.Queue` (see "Editor input"), so they reach the editor without OS input or window focus. They do not reach the game's own Rewired input, only editor code that reads `EditorInput`.

- `key`: `action` is `tap`, `down` or `up`. `key` is a `UnityEngine.KeyCode` member name from the list below, matched case-sensitively. `modifiers` is an optional array of names from the same list and is only valid for `tap`; the modifiers are held around the tap.
- `mouse`: `action` is `move`, `click`, `down`, `up` or `clear`. `move` requires `x` and `y`. `click`, `down` and `up` take an optional `button` (0 left, 1 right, 2 middle; default 0) and an optional `x` and `y` (both or neither) that move the pointer first. `clear` drops the injected position so the real pointer is used again.
- `type`: `text` is 1 to 200 characters, one character per frame. `\b` is backspace and `\n` is return.

Coordinates are screenshot pixels with the origin at the top left, the same space as a harness screenshot and the `screen` field of `state`. The mod converts them to Unity's bottom-left origin with `ScreenPoint.ToUnity(x, y, Screen.height)`. An unknown key or modifier name, an unknown action, a missing or non-numeric coordinate, an `x` without a `y`, a button outside 0 to 2, `modifiers` on a `down` or `up`, and empty or over-long text are rejected at parse time and reported as `ok:false` in the result file.

Valid key names (`key_names.cs`): `A` to `Z`, `Alpha0` to `Alpha9`, `Keypad0` to `Keypad9`, `F1` to `F12`, `UpArrow`, `DownArrow`, `LeftArrow`, `RightArrow`, `Escape`, `Return`, `Backspace`, `Delete`, `Space`, `Tab`, `LeftShift`, `RightShift`, `LeftControl`, `RightControl`, `LeftAlt` and `RightAlt`. The harness logs a warning at startup for any listed name that `Enum.TryParse<KeyCode>` rejects.

## Editor input

The editor reads keyboard and mouse state through `EditorInput` instead of `UnityEngine.Input`, so scripted input can drive it. `EditorInput` exposes `GetKey`, `GetKeyDown`, `GetKeyUp`, `GetMouseButton`, `GetMouseButtonDown`, `GetMouseButtonUp`, `MousePosition` and `InputString`. Each returns the real `UnityEngine.Input` value or the injected one: key and button reads are true when either source says so, `MousePosition` is the injected position when one is set and the real one otherwise, and `InputString` is the real string followed by the injected character for the frame. `GetAxisRaw` and `MouseScrollDelta` return the real value only, since axes and scrolling cannot be injected. `EditorMode`, `EditorTileTools`, `EditorObjectTools`, `EditorPalette` and `MegabonkLevelsMod.OnUpdate` call `EditorInput`; none of them read `UnityEngine.Input` directly, and neither should new editor code.

The injected state lives in `EditorInput.Queue`, an `InjectedInputQueue` (Unity-free, covered by the xUnit tests). Keys are named by their `UnityEngine.KeyCode` member names as strings, such as `"R"`, `"LeftShift"`, `"Alpha1"` and `"Escape"`; the queue does not check that a name is a real key. `OnUpdate` calls `EditorInput.Queue.BeginFrame(Time.frameCount)` before the harness poll and before any editor code, so every reader in a frame sees the same state.

Each enqueue schedules its steps on consecutive frames, starting at the next `BeginFrame` or after the steps already queued:

| Enqueue | Schedule, with N as its first frame |
| --- | --- |
| `EnqueueTap(key, modifiers)` with modifiers | modifiers down at N, key down at N+1, key up at N+2, modifiers up at N+3 |
| `EnqueueTap(key, modifiers)` without modifiers | key down at N, key up at N+1 |
| `EnqueueKeyDown(key)`, `EnqueueKeyUp(key)`, `EnqueueMouseDown(button)`, `EnqueueMouseUp(button)` | one step at N |
| `EnqueueClick(button)` | button down at N, button up at N+1 |
| `EnqueueMouseMove(x, y)` | position set at N, using no frame of its own, so a click queued after it lands on that position on the same frame |
| `EnqueueText(text)` | one character per frame into `InputStringThisFrame`; `\b` is backspace and `\n` is return |

Pressed and released flags are true for exactly one frame. A held key or button stays held until its up step. An injected mouse position (screen pixels, origin bottom-left) persists until `ClearMouse`, after which `MousePosition` is null and `EditorInput.MousePosition` falls back to the real cursor. Calling `BeginFrame` again with the same frame number does nothing.

### Real keyboard text

Typing on a real keyboard into the level-name box works under plain Wine on macOS: after a click on the box, typed characters, Backspace and Enter (which saves the level under the typed name) all behave as `HandleSaveTyping` intends, through the real `Input.inputString` half of `EditorInput.InputString`. An earlier report of an empty box on the same setup did not reproduce, and its cause is unconfirmed. It was not the text-handling code, since injected text and real text take the same path, and not the game failing to receive text under Wine. Open questions if it reappears: whether the game window had OS focus when the box was clicked, and whether the failure is intermittent. CrossOver and Windows were not compared.
