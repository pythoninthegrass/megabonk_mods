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
| Load a level and start the run | `{"command":"load-level","path":"<file>"}` | `run.py load <level> [--map N] [--stage N] [--tier N] [--seed N]` |
| Load an AssetBundle and read back its assets (see [asset-bundles.md](asset-bundles.md)) | `{"command":"load-bundle","path":"<bundle>"}` | `run.py bundle <bundle>` |
| List the shaders the game ships and the scene materials use (see [asset-bundles.md](asset-bundles.md)) | `{"command":"shader-report"}` | `run.py shader-report` |
| Save the rendered frame as a PNG | `{"command":"screenshot","path":"<file>"}` | `run.py screenshot <out.png>` |
| Freeze gameplay | `{"command":"freeze"}` | `run.py freeze` |
| Resume gameplay | `{"command":"resume"}` | `run.py resume` |
| Make the player survive enemy damage | `{"command":"invulnerable"}` | `run.py invulnerable` |
| Restore normal player damage | `{"command":"vulnerable"}` | `run.py vulnerable` |
| Allow or stop new enemy spawns | `{"command":"spawns","enabled":false}` | `run.py spawns <on\|off>` |
| Check in-game Steamworks readiness | `{"command":"steam-ready"}` | `run.py steam-ready` |
| Read the game's current state | `{"command":"state"}` | `run.py state` |
| Start or stop the kill-floor heartbeat | `{"command":"heartbeat","enabled":true}` | `run.py heartbeat <on\|off>` |
| Start or stop the cell-change log | `{"command":"cells","enabled":true}` | `run.py cells <on\|off>` |
| Enter or leave editor mode | `{"command":"editor","enabled":true}` | `run.py editor <on\|off>` |
| Hold the camera at a pose | `{"command":"camera","position":[x,y,z],"rotation":[rx,ry,rz]}` | `run.py camera X Y Z --rot RX RY RZ` |
| Return the camera to the game | `{"command":"camera-clear"}` | `run.py camera --clear` |
| Tap, press or release a key | `{"command":"key","action":"tap","key":"R","modifiers":["LeftShift"]}` | `run.py key R --mod LeftShift`, `run.py key --down W`, `run.py key --up W` |
| Move, click, press or release the mouse | `{"command":"mouse","action":"click","button":0,"x":960,"y":540}` | `run.py mouse move X Y`, `run.py mouse click [--button N] [X Y]`, `run.py mouse down\|up`, `run.py mouse clear` |
| List the editor widgets, or find the one at a pixel | `{"command":"ui-tree"}` or `{"command":"ui-tree","x":120,"y":35}` | `run.py ui-tree [X Y]` |
| Click an editor widget by name | `{"command":"click-widget","name":"Save"}` | `run.py click-widget Save` |
| Save the editor's level, optionally under a name | `{"command":"save-level"}` or `{"command":"save-level","level":"my_level"}` | `run.py save-level [name]` |
| List the saved custom-level files | `{"command":"list-levels"}` | `run.py list-levels` |
| List loaded Unity objects of a type with chosen fields | `{"command":"query-objects","type":"MapData","fields":["eMap"]}` | MCP `query_objects` |
| Type text | `{"command":"type","text":"chest"}` | `run.py type chest` |
| Move the player | `{"command":"teleport","position":[x,y,z]}` or `{"command":"teleport","cell":[cx,cz]}` | `run.py teleport X Y Z`, `run.py teleport --cell CX CY` |
| Pick an upgrade in the open level-up dialog | `{"command":"dismiss-levelup","choice":0}` | `run.py dismiss-levelup [--choice N]` |
| Quit the game | `{"command":"quit"}` | `run.py quit` |
| Relaunch the test level in editor mode | Multiple commands | `run.py relaunch [level] [--map N] [--stage N] [--tier N] [--seed N]` |

`load-level` takes optional integer fields `map`, `stageIndex`, `tier` and `seed` that replace those fields of the level file for that load only. The mod merges them in memory after reading the file, so the file on disk is not modified and no temporary level file exists. `run.py load` and `run.py relaunch` spell them `--map`, `--stage`, `--tier` and `--seed`; the MCP `load` and `relaunch` tools take `map`, `stage`, `tier` and `seed`. `map` is an `eMap` value as listed in `level-format.md` (Forest 1, Desert 2, Graveyard 8, Dungeon 16, Hell 64). A value that is not an integer, or a `map` that is not one of those values, is rejected when the command is parsed, naming the field; the CLI and MCP reject a non-integer before sending anything. A `stage` outside the chosen map's stage range is rejected by the loader with `LevelLoader: load failed: stageIndex N out of range for <map> (M stages)` in the game log, which `relaunch` reports as a failed load, with that log line in its error. Without overrides the level file is loaded as written.

`run.py cycle <level> <out.png>` runs load, waits `--settle` seconds (default 5), takes the screenshot, then quits. `--invulnerable` makes the player invulnerable right after the load, before the settle wait. `--freeze` freezes gameplay and `--camera X Y Z RX RY RZ` poses the camera after the settle wait and before the screenshot. `--timeout` (before the subcommand, default 15 seconds) sets how long to wait for each command and for the PNG to appear. The exit code is 0 only if every step succeeded, 1 if a step failed or timed out, and 2 if the harness is not enabled (`run.py` prints `harness not enabled at <dir>; run 'run.py enable' and relaunch the game`).

On macOS, every quit (`run.py quit`, and the quit inside `relaunch` and `cycle`) also stops the Wine system processes a game leaves behind (`services.exe`, `conhost.exe`, `explorer.exe /desktop` and the like), which otherwise pile up as extra MelonLoader console windows. It skips that cleanup while any other Windows process is running, such as the Steam client under Wine, so a relaunch never takes Steam down.

`run.py relaunch` quits the running game, starts a fresh process through `task game:run` (`task crossover:run` when `MEGABONK_MACOS_RUNTIME=crossover`), waits for a new `DevHarness: enabled` log entry, then polls the in-game Steamworks client before loading `levels/example-forest.mblevel.json`. It retries the load until `KillFloor: armed` appears, then enables invulnerability and editor mode. It allows at least 60 seconds for readiness checks, even when `--timeout` is lower. Pass an optional level path to use a different level file. Use this command between interactive editor sessions; do not send another `load` to an existing run. A second `load` while in editor mode is survivable: `LiveEditPatch` hides its session while the old tile generator is destroyed, so the editor tools find no grid until the reloaded level finishes generating, and the editor re-enters on the new run.

An unknown command, malformed JSON, a missing or empty `path`, or a command that fails while running logs an error and moves the file to `rejected/` without replaying it.

The paths in `load-level` and `screenshot` are interpreted by the game process, so `run.py` converts them (see below).

### Results

Before moving a command file to `done/` or `rejected/`, the mod writes `harness/results/<command file name>`: UTF-8 JSON, one object, written to `<name>.tmp` and renamed so a reader never sees a partial file. A command that succeeds writes `{"command":"<wire name>","ok":true,"result":<object or null>}`. A command that fails while running writes `{"command":"<wire name>","ok":false,"error":"<message>"}`. A file that does not parse writes the same failure shape with `"command":null`. Every command other than `state`, `ui-tree`, `click-widget`, `save-level`, `list-levels`, `query-objects`, `teleport`, `dismiss-levelup` and `steam-ready` has `"result":null`. The result file is written before the command file moves, so a caller that sees the file in `done/` or `rejected/` can read the result at once. Result files are never deleted by the mod.

`run.py` reads them with `read_result(harness, name)`, which returns `None` when the file is absent or not valid JSON. Every subcommand that sends a command exits 1 and prints the `error` text on stderr when the result has `ok:false`, even if the command file landed in `done/`. A missing result file does not fail a command, so `run.py` still works against a mod built before results existed.

### Steamworks readiness

`steam-ready` succeeds with `{"ready":true,"buildId":"<id>"}` once the game's Steamworks client answers `GetAppBuildId`, and with `{"ready":false}` while it is still starting. The not-initialized fault is an expected answer during startup, so `SteamReadiness.Probe` catches that one message (`Steamworks is not initialized`) and returns it as data instead of letting it reach the harness's generic error handler, which would log an ERROR with an IL2CPP stack trace on every poll. Any other fault still propagates and is logged. `run.py steam-ready` exits 1 on `ready:false`, and `run.py relaunch` keeps polling until it sees `ready:true`. A mod that returns no result counts as ready. A long-running caller such as the MCP server has to be restarted to pick up a changed `run.py`; an old one treats any `ok:true` as ready.

### State

`run.py state` prints the `result` object of the `state` command as one line of JSON. A field the mod cannot source is `null`.

| Field | Type | Source and when it is `null` |
| --- | --- | --- |
| `levelLoaded` | bool | `CustomLevelState.IsActive`: the run was started through the mod's level loader |
| `killFloorArmed` | bool | The kill-floor watcher armed for the current level |
| `editor` | bool | Editor mode is active |
| `frozen` | bool | `MyTime.paused` |
| `invulnerable` | bool | The harness's invulnerability is active on the current player's inventory |
| `spawnsOff` | bool | The harness has stopped enemy spawns on the current `EnemyManager` |
| `player` | object or null | `{"position":[x,y,z],"cell":[column,row]}`. `null` when there is no player in the scene (menu, loading). `cell` is `null` when the position label's grid is not armed (no kill floor), and can lie outside the grid |
| `editorTool` | string or null | The active tool name (`Raise`, `Lower`, `Slope`, `Remove`, `Place`, `Select`). `null` outside editor mode, where the tool is not read |
| `selected` | string or null | The selected object as `gen:<genId>` or `placement:<id>`. `null` outside editor mode or when nothing is selected |
| `paletteEntries` | int or null | The number of entries in the catalog palette. `null` outside editor mode, where the palette is not read |
| `edits` | object or null | `{"count":n,"dirty":bool,"lastSavedName":s,"saveStatus":s}`. `count` is the number of edits on the stack, `dirty` is whether that differs from the last save or load, `lastSavedName` is the file name of the last save or load (`null` until one happens) and `saveStatus` is the outcome of the last save attempt: `none`, `saved` or `failed`. `null` outside editor mode |
| `screen` | `[width, height]` | `Screen.width` and `Screen.height` in pixels; screen coordinates for input use this space |

## MCP server

`scripts/mcp_server.py` exposes the harness as an MCP server named `megabonk`, so an agent can call typed tools instead of shelling out to `run.py`, and gets screenshots back as inline `image/png` content. It is a PEP 723 script (`uv run --script scripts/mcp_server.py`) that reuses `run.py`'s helpers rather than duplicating them, and resolves the game directory the same way `run.py` does.

stdout is the MCP protocol channel, so the server writes nothing to stdout; everything reaches the client as tool results. Blocking waits (sending a command, waiting for the game to exit, the whole relaunch sequence) run off the event loop so one tool call never stalls the server.

Tools: `relaunch(level?, map?, stage?, tier?, seed?)` (reports progress through the MCP context and returns the final `state`), `load(level, map?, stage?, tier?, seed?)`, `quit()`, `screenshot(directory?, filename?, overwrite?, scale?, crop?)` (returns the PNG inline), `state()`, `editor(on)`, `freeze()`, `resume()`, `invulnerable(on)`, `spawns(on)`, `camera(position?, rotation?, clear?)` `log_tail(pattern?, since_launch?, max_lines?)`, `log_wait(pattern, timeout?, since_launch?)`, `paths()`, and the input and gameplay tools `key(key, modifiers?, action?)`, `mouse(action, x?, y?, button?)`, `ui_tree(x?, y?)`, `click_widget(name)`, `save_level(level?)`, `list_levels()`, `query_objects(type, fields?, jq?)`, `type_text(text)`, `teleport(position?, cell?)` and `dismiss_levelup(choice?)`. A command the mod rejects, a timeout, or a result with `ok:false` surfaces as a tool error carrying the result file's `error` text (or `<command> <outcome>` when there is no result file). `log_tail` reads `MelonLoader/Latest.log`: `since_launch` (default true) trims to the last `DevHarness: enabled` line, `pattern` keeps lines matching a regex (an invalid regex is a tool error carrying the parse failure), and `max_lines` (default 50) caps the result to the last N matching lines. The input tools validate their arguments before sending anything and raise a tool error for a bad combination: `teleport` needs exactly one of `position` (three numbers) or `cell` (two integers), `mouse` `move` needs both `x` and `y` and the other actions take both or neither, `key` accepts `modifiers` only with `action` `tap`, and `key` checks the key and modifier names against the mod's list (a mirror of `key_names.cs`, kept in step by a test) so an unknown name fails with the valid names before anything is sent. `ui_tree` takes both or neither of `x` and `y`. `paths()` returns `{game_dir, harness, latest_log, levels_dir}`, where `levels_dir` is `<game_dir>/UserData/Levels`, the folder the editor saves custom levels to. `log_wait` polls `Latest.log` until a line matches the regex `pattern`, returns that line, and is a tool error after `timeout` seconds (default 30) or for an invalid regex; `since_launch` (default true) ignores lines before the last `DevHarness: enabled`. Use it after `load` or `relaunch` instead of sleeping, for example `log_wait("KillFloor: armed")`. Each returns the result file's object (`ui_tree`, `click_widget`, `save_level`, `list_levels`, `teleport` and `dismiss_levelup` carry data; the others return `null`). Coordinates are screenshot pixels with the origin at the top left, as in "Key, mouse and type commands", which also lists the valid key names. Input is queued over the next frames, so a `screenshot` straight after may predate its effect.

### Retaining screenshots

`screenshot(directory=None, filename=None)` returns two content blocks: the inline PNG and text reporting its saved absolute path. With no arguments it saves `megabonk-<timestamp-in-nanoseconds>.png` in the repository's gitignored `.tools/evidence`, so captures never land in the working tree. Optional keyword arguments select the destination:

```python
screenshot()
screenshot(directory=".tools/evidence")
screenshot(directory=".tools/evidence", filename="final-editor-slope.png")
screenshot(directory="/Users/lance/Pictures/megabonk", filename="forest.png")
```

Relative directories resolve against the server's working directory; absolute directories are supported. Missing directories, including parents, are created automatically. `filename` must be a single basename ending in `.png`, not a path; path separators and invalid filename characters are rejected. Omit it for a timestamped name in the chosen directory.

Existing files, directories and symlinks are not overwritten by default: a collision returns a tool error asking for another filename or directory, including if the destination appears during capture. `overwrite=True` replaces an existing file instead (the capture is moved over it atomically; a directory at the destination is still an error). The server captures into a temporary subdirectory, validates the PNG, and publishes it using an exclusive hard link on the same filesystem; the filesystem must support hard links. Temporary captures are cleaned up on success or failure, though newly created destination directories remain. Invalid destinations, permissions and capture failures return actionable tool errors rather than a saved path. `crop=[x, y, width, height]` (screenshot pixels, applied first) and `scale` (greater than 0, at most 1) shrink the inline image to cut token cost; the saved file is always the full capture. A crop outside the capture or a bad `scale` is a tool error. A server restart is needed to pick up changes to its tool signatures.

To verify retention through MCP, call `screenshot(filename="editor-check.png")`, inspect the inline image and open the reported path as a PNG. A second call with the same arguments must return a collision error and leave the first PNG unchanged.

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

### Result encoding

Structured tool results (every tool that returns the harness result, plus `paths`) pass through one function, `_encode` in `scripts/mcp_server.py`. The `MEGABONK_MCP_ENCODING` environment variable, read through python-decouple (process environment, then `.env`; the `megabonk` entry of `.mcp.json` can also set it), selects the format:

| Value | Text content | `structuredContent` |
| --- | --- | --- |
| `json` | indented JSON | present, identical to the payload |
| `json-min` (default, also when unset) | JSON without whitespace | omitted |
| `toon` | [TOON](https://github.com/toon-format/toon) | omitted |

`json-min` and `toon` omit `structuredContent` because a client that forwards it would send the payload twice and cancel the saving. An unknown value is a tool error raised before the command is sent, so a bad setting does not follow a game action. Errors, screenshots (image content), `log_tail`, `log_wait` and `quit` are never re-encoded.

`toon-format` is pinned to `1.2.0` in the script header and in the `scripts:test` command. An unpinned install resolves to `0.1.0`, a stub whose `encode()` raises `NotImplementedError`; `test_toon_encode_is_not_the_stub_release` fails on it.

The default was chosen by a rule fixed before measuring: switch to TOON only if its total token count is at least 15% below minified JSON across the captured `state`, `list_levels` and `ui_tree` payloads, and no single payload is more than 5% worse than minified JSON. The payloads are in `tests/fixtures/mcp_payloads/`, captured from a live editor session on the example forest level. Tokens were counted with tiktoken `cl100k_base`, a proxy for Claude's tokenizer, so treat the percentages as approximate.

| Payload | JSON (indented) | JSON (minified) | TOON | TOON vs minified |
| --- | --- | --- | --- | --- |
| `state` | 176 | 100 | 122 | 22.0% worse |
| `list_levels` | 95 | 69 | 71 | 2.9% worse |
| `ui_tree` (54 widgets) | 3128 | 1979 | 1375 | 30.5% better |
| Total | 3399 | 2148 | 1568 | 27.0% better |

TOON wins on the uniform array of widgets and loses on the small nested `state` object, so the total passes the 15% bar and the per-payload bar fails. The default is therefore `json-min`, which was 37% below indented JSON in total on the same payloads (2148 tokens against 3399) and does worse than TOON only on `ui_tree`. Set `MEGABONK_MCP_ENCODING=toon` for sessions that read many `ui_tree` results, or `json` to get indented text with `structuredContent` back. `json-min` was checked live through Claude Code: `state`, `list_levels` and `ui_tree` return parseable compact JSON, errors stay plain text and `screenshot` still returns an image. The uniform-rows case from the live-object query was not measured because that query does not exist yet; re-measure once it lands, since its rows are the shape TOON suits best.

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
task game:editor                                  # same, through the taskfile
task game:editor -- levels/other.mblevel.json     # a different level
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

## Launching without a Steam session

Steam allows one session per account across every device, so a second Mac that starts Steam signs the account out on the first. The mod is load-only, but the level loader reads the app build id through Steamworks, so a game that cannot see a Steam session cannot `load-level`. `tools/steamstub/` provides a drop-in `steam_api64.dll` that stands in for the real shim so the game launches and plays with Steam stopped, no login, and no `SteamAppId`/`SteamGameId` environment variables.

The game's managed Steamworks.NET resolves its P/Invokes against the native shim `Megabonk_Data/Plugins/x86_64/steam_api64.dll`. That shim normally loads the real `steamclient.dll` from the Steam install, which needs a running client. The stub exports the same symbol set, so every P/Invoke the runtime can already resolve still resolves; most interface methods return a safe default, while the few the game needs for init, `load-level` and the offline save path return real values (`GetAppBuildId` returns the depot build id `21750826`, matching every shipped level file so the loader records no mismatch).

### Building and installing

The stub is generated from the game's own shim, built with mingw-w64, and deployed by swapping the file in the game directory. The swap is fully reversible.

```sh
task game:mingw:install                 # mingw-w64 x86_64 GCC, if not already present
task steamstub:generate                 # regenerates steamstub.c from the original shim's exports
task steamstub:build                    # builds tools/steamstub/steam_api64.dll
task steamstub:status                   # report active vs stub, and the backup
task steamstub:install                  # build if needed, back up the real shim, drop in the stub
```

`scripts/swap_steam_stub.py`, wrapped by the `steamstub:` tasks, resolves the game directory the same way `game_paths.py` does (process environment, then the nearest `.env`, then the built-in default). The game must be quit before install or restore, because a loaded DLL cannot be overwritten. `install` copies the current shim to `<shim>.steamstub.bak` before replacing it; `restore` puts the backup back. `status` prints the shim hash, the stub hash, the backup path, and whether the active file is the stub or the original.

### Launching

With the stub installed and Steam stopped, launch through the normal task:

```sh
task game:run        # Megabonk.exe, detached; no Steam client, no SteamAppId variables needed
```

The game reaches the main menu, and `load-level` works:

```sh
uv run scripts/run.py relaunch            # quits, relaunches, loads the example level, enters editor
uv run scripts/run.py load levels/example-forest.mblevel.json
```

The stub is a drop-in, so a normal Steam install is unaffected: run `task steamstub:restore` and relaunch to return to the logged-in path.

### The degraded-init verdict

`MEGABONK_STEAM_FAIL_INIT=1` makes the stub's `SteamInternal_SteamAPI_Init` return `k_ESteamAPIInitResult_NoSteamClient` (3) and `SteamAPI_IsSteamRunning` return 0, exactly as it would with no Steam client, while `CreateInterface` still returns the fake interface. This is the intended way to confirm the game's degraded behaviour in a live run:

```sh
task steamstub:test:fail    # quit, relaunch with the variable set, print steam-ready and state
task steamstub:test:ok      # same without it; expect ready:true
```

Observed with Steam stopped:

- `steam-ready` returns `{"ready":false}` — the game's `SteamManager` logs the failed init and reports not-initialized, matching the static verdict that `SteamManager.Load` logs and continues rather than quitting.
- The game still reaches the main menu with no quit loop, and `load-level` still starts a run, because the stub's `CreateInterface` returns a non-null `ISteamApps` whose `GetAppBuildId` returns the depot build id. The loader's `GameBuildIdPatch.CurrentBuildId()` therefore does not throw.

The one degraded behaviour that does **not** appear this way is a `load-level` rejected with `Steamworks is not initialized`. That happens only when `CreateInterface` returns null, which is the real shim with no Steam client at all — not the stub. On this Mac the macOS Steam `ipcserver` (the process that provides the game's `SteamClient` interface to the real shim) respawns within about a second of being killed and is reparented to init, so the real shim's `Init` still succeeds even when the Steam app is stopped. The genuinely hard-degraded path — `steam-ready` `ready:false` and `load-level` rejected — is reproduced by the real shim only when that ipcserver is absent, which means quitting the macOS Steam app (and, like any Steam quit, signing the account out on every other machine).

### Saving and reloading a custom level offline

The mod's editor writes a custom level to `<game dir>/UserData/Levels/<name>.mblevel.json` — the offline, `steamId 0` save path. The name is whatever is in the editor's name field, normalized to letters, digits, `-` and `_` (the `.mblevel.json` suffix is stripped if present); an empty field normalizes to `level`, so the Save button overwrites `level.mblevel.json`. The field auto-saves its text while focused, but the level file itself is only written when the Save button is clicked.

To save from the harness, click the Save button, which sits at the right end of the editor toolbar. Its center is at display coordinates about `(1001, 86)` on the 1512x982 frame (the toolbar is the gray bar across the top; the Save button is the wide button to the right of the name field, just left of Load). A click there overwrites `level.mblevel.json` with the current edits:

```sh
uv run scripts/run.py mouse click 1001 86
```

Mouse coordinates are the screenshot's top-left pixels (see the "Commands" table), so the value above is the on-screen position directly. Reload the saved file with `run.py load <path>`; the game reads it back through the same loader, and the edits are present on the next run. A level saved, then reloaded, then edited again, keeps the previously saved edits — confirming the round trip through the offline path.

### Degraded and absent features

With the stub, the game is playable but Steam is faked, so anything that would have talked to Steam returns a default or does nothing:

- No authenticated Steam identity. `GetSteamID` returns 0, which is exactly what selects the offline `steamId 0` save path, so saves go to `UserData/Levels/` rather than any Steam cloud location.
- Achievements, leaderboards and stats return defaults. The mod suppresses those writes entirely for mod-loaded levels anyway (see `steam_write_guard_patch.cs`), so this changes nothing for custom levels.
- Steam cloud, remote storage,UGC, screenshots, chat and the overlay are unavailable; the game's code paths that would use them read a default or no-op.
- `SteamAPI_RestartAppIfNecessary` returns 0, so the game never relaunches itself.

### Second Mac

The stub swap is a one-file change in the game directory, so it copies along with the prefix (see "Setting up a second machine" above). A copied prefix already has the game's original shim; run `task steamstub:install` once on the new machine, then `task game:run` with Steam stopped. The stub build is reproducible from the shim with `task steamstub:generate` + `task steamstub:build`, so it can be rebuilt there too if the deployed file is ever replaced.

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

## Enemy spawns

`spawns` with `enabled:false` (`run.py spawns off`, MCP `spawns(on=false)`) sets `EnemyManager.enabledWaves` to false, which stops the wave spawner; `enabled:true` sets it back. `state` reports `spawnsOff`, true only while the current `EnemyManager` is the one the harness switched off. The switch does not outlive a scene: a level load or new run builds a new `EnemyManager` with the default `enabledWaves`, so spawns are on again after `relaunch` or `load`; send `spawns off` again after each.

Enemies already alive are not cleared. Clearing them would mean calling `EnemyManager.RemoveEnemy` outside the game's own death path, which skips drops, XP and pool bookkeeping. They keep chasing the player until they die, fall to the kill floor, or the run is frozen. Run `spawns off` straight after the load to keep the count low.

Verified on the example forest level with the kill-floor heartbeat: with spawns on, `enemies` stayed between 2 and 5. After `spawns off` the existing enemies died off within about 25 seconds and `enemies` stayed 0 for the following 67 seconds. `spawns on` brought 4 enemies back within 2 seconds.

Limits:

- Only the wave spawner is switched off. Whether bosses, shrine or summoner spawns, which call `EnemyManager.SpawnBoss` and `SpawnEnemy` directly, also respect `enabledWaves` is unconfirmed; the forest level run above had none of them.
- The level-load reset was confirmed through `relaunch`, which starts a fresh process; a `load` into a running game was not tried, because the harness advises against it.

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

The harness does not press menu buttons or open the level-up dialog. Only `state`, `ui-tree`, `click-widget`, `save-level`, `list-levels`, `query-objects`, `teleport` and `dismiss-levelup` return data; the other commands report success or failure and nothing else, and `state` does not report health, inventory, enemies or the level-up dialog. Use `freeze` to stop an idle player dying during a screenshot, or `invulnerable` when enemies must keep moving.

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

Editor mode is a freeze-and-fly overlay for surveying a map while a run is active. It works in any run, not only mod-loaded levels. Toggle it with F8, or with `run.py editor on` and `run.py editor off` when the harness is enabled; `run.py key F8` exercises the same editor hotkey path. F8 is ignored while the game's debug console (F10) is open and while no run is in progress. The game's own `LookHorizontal` and `LookVertical` Rewired axes read zero while the run is paused, which is why look uses Unity's raw mouse axes. Rewired's key bindings live in a serialized asset that is not readable from code, so that F8 collides with no game binding is only confirmed by pressing it in the game.

The editor supports `EMapType.Tiles` maps (Forest, Graveyard) fully and `EMapType.ProceduralMesh` maps (Desert, Hell) for objects only. `EditorMapSupport.Check` decides: a Tiles map allows every tool; a ProceduralMesh map is one heightmap mesh from `MapGenerator` that never fills `ProceduralTileGeneration.proceduralTiles`, so there is no grid, no tile tools and no cell. On such a map the live-edit session holds objects only (`LiveEditPatch.IsTerrainMap`), the cursor raycasts against the heightmap mesh's `MeshCollider` (`MapGenerator.mesh`), Place and Select use the hit point directly (Y is the terrain height there, no cell snapping and no quarter-tile guide, only the placement ring), and the kill floor arms from the lowest point of that collider with the usual margin and catch-floor rule (`KillFloor: armed at y=... (terrain low y=...)`). Pressing a tile tool (Raise, Lower, Slope, Remove) shows a toast and keeps the current tool. Tile edits in a loaded level file are skipped with a `LiveEdit: N tile edit(s) skipped` warning. Teleport by cell and the cell readout need a grid and do not work on a terrain map. A map type that is neither is refused: the log has `EditorMode: unsupported map: <reason>` (also written when generation completes), `run.py editor on` is rejected with the reason, and `run.py relaunch` stops with `relaunch: the editor does not support this map` instead of retrying until the kill floor never arms. The `GridShape: proceduralTiles is null` lines on Desert are the missing grid, not a fault.

Hell is `EMapType.ProceduralMesh` too (`MapHell`, `mapType=1`), so the editor treats Hell like Desert (object editing only). Confirmed in the running game: Hell has a populated `MapGenerator.mesh` with a `MeshCollider`, the kill floor arms at `y=-12` (`terrain low y=-6.31`, catch floor `-20`), and place, select, rotate, drag-move, remove, undo/redo, save and reload all work. On Hell a click on the world selects a placed object through the `nearest` path, and generation is deterministic for a given seed, so a saved Hell level reloads onto the same terrain. To repeat the check, run `relaunch` with `map` 64 (MCP) or `run.py relaunch --map 64`. Prefab lookup for a catalog id goes through `Resources.FindObjectsOfTypeAll<MapData>()` (`CatalogPrefabs.TryFindMap`), not `DataManager.maps`, which omits Hell. Hell's `MapData` asset has `eMap = 64`, not the `4` the Il2Cpp `EMap` enum lists, so `LevelLoader` matches on the asset's value and the mod's `EMap` uses `64`. `MapDungeon` (`eMap = 16`) is also loaded but is in neither the enum nor `DataManager.maps`; Hell and Dungeon are missing from `DataManager.maps` too, so look maps up through `Resources.FindObjectsOfTypeAll<MapData>()`. A load whose `MapData` is still missing 20 seconds after it was queued logs `LevelLoader: load failed: no MapData found for map=<n>; available: ...` and is dropped, and `run.py relaunch` stops on that line instead of retrying, with the error `relaunch: the level failed to load: <log line>`. The `EditorMode: unsupported map` stop is reported the same way (`relaunch: the editor does not support this map: <log line>`). The line is the first match after the last `DevHarness: enabled`; when none is found the error falls back to a fixed hint to read the game log. The MCP `relaunch` tool returns the same text as its error.

Entering calls `MyTime.Pause`, which stops the run timer, enemy spawning, enemies and the player, and detaches the camera from the player. The camera is the game's own `PlayerCamera` camera, rewritten from `OnLateUpdate` the same way the harness `camera` command does it, so no second camera exists to stack across cycles. The free-fly pose starts as a zoomed-out overview of the player (`FreeFlyCamera.OverviewPose`): 60 units above the player and back along +Z, pitched down 40 degrees and facing -Z, so the player is centred, +X runs to the screen's left and the view stays a fixed, near-isometric angle whatever way the game camera was facing.

| Input | Effect |
| --- | --- |
| W, A, S, D | Move along the view direction and sideways |
| Space, Left Alt / Right Alt (Option) | Move up and down in world space |
| Left Shift | Move 4 times faster |
| C | Snap the camera back to the overview pose over the player, from anywhere on the level; ignored while a text field has focus or Ctrl is held. When the player is outside the tile grid, the overview frames the centre tile instead |
| Mouse move while the right button is held, after pressing it off the palette | Look, read from Unity's raw `Mouse X` and `Mouse Y` axes and scaled by the game's saved mouse sensitivity and axis-invert settings, so it turns 10% faster than normal play |

The Graveyard spawn is about 2000 units from its 19x19 grid (state reports cell `[59,59]`), so an overview over the player would show no tiles and clicks would place nothing. When the player's cell is outside the grid, `OverviewTarget.Of` aims the overview at a body standing on the centre tile (`PlayerBodyOffsetY`, 1.925, above the tile surface, as the harness teleport does) rather than the bare surface, which rendered the ground as sky. The editor can be entered before the grid session exists, so the pose is recomputed once when the grid first appears. The player itself is not moved.

Exiting clears the camera override, which restores the camera's local pose saved before entry, and calls `MyTime.Unpause` only if the game was running when editor mode was entered. Entering while the game was already paused (a level-up dialog, for example) leaves it paused on exit. If the run ends while editor mode is active, the mode exits on the next frame. Entering and leaving log `EditorMode: entered` and `EditorMode: exited` with the resulting `MyTime.paused`.

The look rate was measured in normal play with a probe comparing `Mouse X` against the player's `PlayerInput.cameraRotation`: the player turns 1 degree per raw mouse unit at a saved `sensitivity` of 1.0, with the same sign convention as editor mode. The sensitivity and the `inverted_horizontal_axis` and `inverted_vertical_axis` flags are read from `SaveManager.Instance.config.cfControlSettings` each time editor mode is entered. Editor mode multiplies the saved sensitivity by 1.1 because the exact normal-play rate felt sluggish when flying with the right button held. Movement speed (60 units per second, 4 times that with Shift) is a fixed choice, not read from the game.

## Catalog palette

While editor mode is active a palette on the left edge shows the placeable prefabs of the loaded map (`MapController.currentMap`) as a paged grid of icon slots, in a grayscale scheme. A column of category tabs sits on the far left, the panel title (map and current selection) and the search field are above the grid, and a footer under it shows `<`, `n/m` and `>`, where `n/m` is the current page over the page count. Entering editor mode releases the cursor lock and shows the cursor; leaving restores the lock and visibility the game had. Because the cursor is free, look only applies while the right mouse button is held. Pressing it with the pointer on the palette does not start a look, but a sweep that starts off the palette keeps turning when the pointer crosses it.

The entries come from the game's own prefab catalog, walked by `CatalogPrefabs` (the same code live editing uses to resolve a `catalogId` to a prefab): every `StageData.randomMapObjects[].prefabs[]`, `stageTilePrefabs.flatTilePrefabs[]` and `mapSpecificTilesPrefabs[]` of every stage of the map, `MapData.shrines[]`, and the `SpawnInteractables` `chest`, `chestFree` and `rails[]`. `PaletteCatalogBuilder` turns the counts into `catalogId` strings in the shapes documented in `level-format.md`, grouped by stage and category. `MapData.randomObjectsOverride` has no `catalogId` shape and is not listed.

The tabs are `All` plus one per category the map has (random objects, flat tiles, specific tiles, shrines, interactables, and `Packs` when a pack asset is listed), so all stages of a category share one tab and the stage is shown in the tooltip. A tab shows the thumbnail of its category's first entry, or a short text label when that entry has no thumbnail. The grid is 4 columns by 6 rows of 61.6 px slots. The wheel over the palette or the `<` and `>` buttons change page, one page per notch, stopping at the first and last page without wrapping. Changing the search or the tab returns to the first page, or to the page holding the selected entry when the filters leave it visible. Selecting an entry elsewhere (picking an object in the world) also jumps to its page. The slots are a fixed pool that is rebound on every filter or page change.

Assets from installed packs under `UserData/LevelPacks/` are appended after the game entries as one `Packs` tab, on every map, because packs are not map-scoped. Each entry has the `catalogId` `bundle:<pack>/<asset>`, the asset name as its display name and stage 0, and `PackPaletteEntries` orders them by pack id and then asset name. A pack with a valid `manifest.json` lists the manifest assets its bundle also holds; a manifest asset the bundle lacks is warned about once and not listed, and a bundle asset the manifest omits is not listed. A pack with no manifest, or an invalid one, lists every prefab in its bundle. Packs load once per session and a missing pack is cached, so a pack installed after launch appears only after a relaunch. With no packs installed the palette has no `Packs` tab and no extra entries.

Each slot shows a rendered thumbnail of the prefab, or its display name when the prefab could not be rendered. The selected slot has a white border and a lighter fill; the hovered slot has a lighter fill. Hovering a slot shows a tooltip with the display name, the `catalogId` and the stage and category; hovering a tab shows the category name. Clicking a slot selects it, and the selection is `EditorPalette.Selection.Current`, a `CatalogId`, with a `Changed` event that the placement tool reads. Clicks and wheel input are read from Unity's `Input` directly instead of through a UGUI `EventSystem`, so the game's Rewired input module is untouched. The palette is rebuilt each time editor mode is entered, so it follows the map; a selection that is not in the new map's entries is cleared. Building logs `EditorPalette: built <n> entries for <map>`.

Thumbnails are drawn by `PrefabThumbnails`. It does not instantiate the prefab, because that would run the game's own `Awake` and `Start` code (shrines, chests). Instead it copies each `MeshFilter` and `SkinnedMeshRenderer` mesh, its shared materials and its pose relative to the prefab root onto a proxy object parked at y = -5000 on layer 31, skipping meshes whose names mark a lower LOD (`LODGroup.GetLODs` is not exposed by the interop assemblies). A temporary camera that only sees layer 31, with a transparent background, a 30 degree field of view and a 3/4 view framed from the combined bounds, and a directional light on the same layer render it into a 128x128 render texture, which is read back into a `Texture2D`. Fog is switched off for the render and restored. The proxy, camera and light are destroyed after each render. A prefab with no mesh, empty bounds or a render that throws yields no thumbnail and the slot shows its name instead.

Textures are kept in a static `ThumbnailCache` keyed by `catalogId`, including failed renders, so re-entering editor mode on the same map renders nothing. Entering editor mode logs `EditorPalette: rendered <n> thumbnails in <ms> ms (cached <k>)`. On Forest the first entry rendered 75 thumbnails in about 0.7 s on a cold cache and a second entry rendered none; the renders run in one frame because that cost is acceptable. A few Forest prefabs (the ones labelled `Forest<stage>_Prefab<n>`) show their names instead of an image; the cause per prefab has not been checked.

Click the search field below the title to filter by any part of the display name or `catalogId`, ignoring case. Search uses `EditorInput.InputString` (Unity's `Input.inputString` plus harness text), with backspace and a 128-character limit. Enter or a click outside the field ends focus without clearing the query. In either search or the save-name form with text, the first Esc ends focus and keeps the text, the second Esc clears that form, and the third Esc opens the game menu. If that form is already empty, Esc opens the menu immediately instead of consuming a blur/clear step; text in the other form does not affect this decision. Refocusing a form starts again with blur; entering/leaving the editor resets the sequence.

While typing, camera movement/look, centering, tool hotkeys, object shortcuts and undo/redo hotkeys are suppressed, including the frame focus ends. The game's `UiManager.Update` reads cancel/abort actions and calls `PauseUi.Toggle`; a prefix blocks that toggle while a form owns input or the Esc sequence still has a blur/clear step to consume. The shared `EditorEscapeSequence` records the consumed frame so the guard works whether the game's update runs before or after the editor's. `PauseUi.Update` is not the cancel handler: it switches between the pause menu and map. Outside text entry/the Esc sequence, the game's menu input is unchanged; no Rewired or EventSystem configuration is modified. `WindowManager.RefreshCursor` also respects active editor mode, keeping the cursor visible and unlocked even when a game window closes.

Search and the level-save name share one single-line text model (`TextFieldModel`) with a caret. Left and Right move the caret and repeat while held (0.4 s delay, then 25 per second, `KeyRepeater`), Home and End jump to the ends, Delete removes the character after the caret, and Backspace the one before it; typing inserts at the caret and the length limit still applies (128 characters for search, 80 for the save name). Focusing a field puts the caret at the end. The fields are monospace, so `TextWindow` works in whole characters: a text longer than the field scrolls horizontally just far enough to keep the caret visible, and scrolls back when the caret moves left or the text shrinks. `TextFieldView` draws the visible slice and a blinking caret. Arrow keys are read through `EditorInput`, so the harness `key` tool can drive them (Home and End are not in its key list).

Both search and save text use a fixed baseline rather than glyph-geometry centering, so adding tall letters or descenders does not move the word vertically. Search text and placeholder are white; a focused search field takes the selected-slot fill.

A double chevron tab on the right edge of the panel, vertically centred and just outside it, collapses the palette to a single column; in that state it reads `>>`. The compact panel keeps the category tab column and shows one column of 6 slots, only as wide as the footer `<` and `>` buttons side by side (about 100 px of panel against 274 px expanded). The title shrinks to the map name over the selected entry's name, cut with an ellipsis when too long; the search field and page label are hidden, and a magnifying glass button, as wide as a slot, takes the search field's place. Compact slots are enlarged to span both footer buttons (84 px against 61.6 px expanded), their thumbnails scale with them, and the panel grows taller to fit. Clicking `>>` expands the palette again; clicking the magnifying glass expands it and focuses the search field. The wheel and the `<` `>` buttons page the column as they page the grid. The active search and category stay applied while compact, and are cleared only by hand once expanded (Esc sequence or Delete in the field); collapsing never clears them. Collapsing blurs a focused search field, so keyboard capture ends the same way as a click outside the field. The state resets to expanded on each editor entry. After a state change the page shown is the one holding the selected entry when the filters leave it visible, otherwise the one holding the first entry that was visible. `EditorPalette.Width` (which includes the chevron tab) and `PointerOverPanel` follow the current panel, and the tile toolbar re-centres every frame from `Width`, so the empty space left by the collapsed palette does not block map clicks or look. The magnifying glass is a 24 px texture drawn from `MagnifierIcon.Mask` rather than a font glyph, so it does not depend on the RobotoMono TMP asset covering one. The grid shape and page shift on a state change live in the Unity-independent `palette_layout.cs`.

Search and category combine, and `No matching entries` appears when nothing matches. Changing either filter never changes the selected prefab, even if it is hidden. Search and category reset on editor entry. Filtering, paging and caching live in the Unity-independent `palette_filter.cs`, `palette_pager.cs`, `palette_layout.cs`, `magnifier_icon.cs`, `thumbnail_cache.cs` and `palette_search_input.cs`; selection always retains the full catalog separately from the visible slots.

## Tile tools

While editor mode is active a toolbar at the top centre of the screen shows the six tools, the undo, redo, validate, save and load controls, and a status line. The toolbar and the level list use the palette's gray bordered panel, buttons and input style (`EditorUi`). The digit keys 1 to 6 select Raise, Lower, Slope, Remove, Place and Select (the last two are in "Object tools" below); Select is active on every entry, so the first click edits nothing until an object is pressed; the previous choice is not kept. Pressing 1 to 4 in normal play does nothing, so the game binds no action to them (confirmed in the game, like F8).

The targeted tile is the one under the mouse pointer. A ray from the camera through the pointer is cast against the baked ground collision (`ProceduralTileGeneration.collider`, see "Ground collision after edits" in [runtime-map-structure.md](runtime-map-structure.md)) only, so enemies, props and the player never block it. The hit point is stepped 0.01 units into the surface before it is converted to a cell with `PositionReadout.CellOf`, so a hit on a side wall targets the tile the wall belongs to. A yellow outline traces the targeted tile's top surface, following the ramp on a slope. Nothing is targeted while the pointer is over the palette, outside the grid, or over a removed cell.

Hovering a tool in the toolbar shows a tooltip under the toolbar with what the tool does (`EditorTools.Description`), for example `Click a tile to raise it one level`. It uses the same `EditorTooltip` box as the palette's slot, tab and button tooltips, and every tooltip shares one timing rule (`hover_delay.cs`): a tooltip appears after the pointer has rested on its item for 3 seconds, and moving to another item, in the toolbar or the palette, shows that item's tooltip at once as long as a tooltip was visible within the last 2 seconds. Resting elsewhere for longer than 2 seconds restarts the 3 second delay.

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
| `Load` and right-side list | browses `.mblevel.json` files in `<game>/UserData/Levels/` (case-insensitive sort); the list shows 4 files per page with `<` and `>` buttons and an `n/N` page counter in its title row; the wheel over the list changes page, one page per notch, stopping at the first and last page (the same `PalettePager` as the palette); click a row to select it, which also copies its file stem into the save form; the selected row has a lighter fill and yellow text, the hovered row a lighter fill; after `Save` the list shows the page holding the saved file; `Load` starts that file through `LevelLoaderPatch.LoadAndStart` and editor mode then auto-re-enters once the new run is active |
| `F8` | toggles editing and live playtesting of the same run; no save or stage reload is required, and undo/redo history is retained |

Validation overlays are explicitly stale after any edit/undo/redo and are cleared until `Validate` is pressed again.

The status line also shows `save: saved|dirty` with the current edit count. `Load` is not blocked when unsaved edits exist; it immediately starts the selected file's map, stage, tier, and forced seed while handing its edit history to the generation pipeline, so the loaded level is applied on the new run.

Edits apply immediately to the running level. Press **F8** to leave the editor, restore the normal follow camera and resume gameplay; press it again to freeze the run and continue editing. There is no separate Playtest button or restart: player position, health, enemies and timer continue from where they were paused. Unsaved edits, undo/redo and save bookkeeping remain intact across toggles; a different run starts a new edit session. A game already paused before editor entry remains paused on exit (for example, while a level-up dialog is open). Harness invulnerability is independent of F8; disable it explicitly when testing damage.

Entering the editor marks the current run unscored immediately, even if it began as a normal run and no edits have been made. Leaderboard, achievement and stats writes stay suppressed after leaving the editor; only starting a new normal run clears the guard. The open tile maps bake no navmesh and enemy movement is physics-based, so tile edits need no navigation rebuild.

The toolbar is as wide as its widest row (the tool row or the action row) plus a margin, and sits centred between the right edge of the palette and the left edge of the level list, which is flush against the right screen edge and is as tall as the toolbar. A toast appears directly under the toolbar for 3 seconds after a save or load: orange text for success, red text for a failure (save, load and validate errors, plus validate with no live level or no spawn portal). The failure text also stays in the status line. Toasts stack under the toolbar with the newest nearest it, each expiring on its own 3 second timer, and at most 5 show at once (a sixth drops the oldest). Clicking a toast dismisses just that one, and the click does not reach the map or the tools. The stack logic is in `toast_stack.cs`.

## Object tools

Tool 5 (Place) and tool 6 (Select) edit objects. Both place at the cursor's ground point, not snapped: the point is kept inside the targeted cell (clamped to its edges), measured from the same origin as `PositionReadout.CellOf` (via `PositionReadout.CellCentre`). The height is the tile surface at that point (`Height * tileHeight`; on a ramp it rises a full level from the downhill edge to the uphill edge). `tileHeight` and the spacing are read from the live `StageData.mapParameters`. The yellow tile outline shows the targeted cell. While Place is active, or Select has an object selected, thin white lines draw a quarter-tile grid (spacing / 4, 10 units on Forest's 40-unit tiles) over that cell as a visual guide, and, in Place only, an orange circle marks the exact placement point; objects do not snap to the lines.

An identical object cannot be stacked: placing or moving an object is ignored, with a log line, when an object of the same prefab name already stands at the same position (within 0.01 on every axis, generator-spawned or editor-placed). Different objects may share a position.

| Tool | Input | Edit |
| --- | --- | --- |
| Place | left click on a tile with a palette item selected | `PlaceObject` at the cursor point; rotation is the prefab's pitch and roll with yaw set to the camera's yaw plus 180 degrees rounded to 90, so the object faces the camera (assumes a prefab's front is +Z; unconfirmed); scale is the prefab's local scale |
| Select | press an object | selects it (red ring on the ground at its base, sized to its footprint — see below); pressing where nothing is picked deselects |
| Select | keep holding for 0.2 seconds, move, then release | the object is picked up and follows the cursor as a preview, keeping the offset at which it was grabbed, then one `MoveObject` to the release point, keeping rotation and scale; releasing over the palette or off the grid, onto an identical object, or without moving puts it back and makes no edit; a press released before 0.2 seconds only selects |
| Select | `R` / `Shift+R` | `MoveObject` with yaw 90 degrees clockwise / counter-clockwise, keeping pitch, roll and position |
| Select | `F` / `Shift+F`, `G` / `Shift+G` | `MoveObject` turning the object 90 degrees about the world X axis (pitch) or Z axis (roll), positive / negative with Shift, keeping position and scale; the rotation is composed in world space and written back as Unity euler angles, so the same orientation can read differently (an upside-down object saves as `0,180,180`, not `180,0,0`) |
| Select | `Delete` or `Backspace` | `RemoveObject` |
| any | middle click an object | pick block: selects the object's palette entry and switches to Place |

Picking tries a physics raycast first (`RaycastAll`, trigger colliders included) and takes the nearest hit whose hierarchy resolves to an indexed object in an `object:*` category or to an editor-placed object (`ObjectPicker.NearestHit`). A trigger collider only counts when the ray also crosses the object's model renderer bounds, because triggers are far larger than the model (a shrine's 12.5-unit charge sphere, a tree's canopy `FadeCollider`) and would otherwise swallow clicks meant for the chest or rock beside them; a solid collider that is not an object, such as terrain, hides everything behind it; tiles, walls, fill pieces and `tileObject` scenery (ForestParticles and the like, whose renderer bounds span the map) never resolve and so never get a ring. When that finds nothing, the pickable object nearest the cursor's ground point on the XZ plane within an eighth of a tile (5 units on Forest) is used. The log line names the path (`raycast` or `nearest`).

The selection ring marks the object's base footprint, not a cross-section of its overall bounds. Radius (`ObjectTools.RingRadius`) is the enclosing circle of the footprint's XZ extents plus 10% clearance, floored at 0.5. The footprint is the union of the object's enabled colliders — solid colliders first, then trigger colliders (a chest's or pot's only body collider is a trigger), falling back to the model-bounds union when there are none. Base Y (`ObjectTools.RingBaseY`) is the physical ground under the footprint centre: a downward `Physics.RaycastAll` that skips the object's own colliders and triggers, picking the hit nearest the object's origin (`ObjectTools.SupportY`) so overhanging geometry above a chest cannot lift the ring off its floor; clamped to never sink below the object's own base, and falling back to the tile surface under the object when nothing is hit. The model-bounds union (`ObjectTools.IsModelRenderer` — disabled renderers, particles and `MinimapIcon` skipped) also excludes zero-thickness renderers (`FlatDecalEpsilon`): a pot's flat 9x9 indicator `Quad` at y=5 is a decal, not model geometry, and would balloon the ring. The ring material uses the `UI/Default` shader, which honours `unity_GUIZTestMode`, on render queue 4000, so it draws over terrain and mesh that would occlude it (`Sprites/Default` ignores the ZTest override and would silently depth-hide a ring buried in a large rock's mesh). Setting `MEGABONK_RING_DIAG=1` in the game environment logs one `[ring-diag]` block per selected object (bounds, footprint extents, ground/base Y, radius, shader) for diagnosing ring placement. The Forest ruins (`Castle`, `Ruins (1)`, `Pillar`, `Cube`, `Crate (n)` and similar) are deliberately unpickable: they are scene roots without a `(Clone)` suffix placed by the tile-object generator, so they are not in the genId index, and the `tileObject:####` entries are empty `Forest0_PrefabN(Clone)` placeholders with no renderers. Making them editable would need a new genId category and index order, which the edit replay depends on. Selection clears when the tool changes. Nothing is picked or placed while the pointer is over the palette.

Pick block scrolls the palette to the picked entry when it is outside the visible list. It matches a generator-spawned object's prefab name (the `object:{prefabName}:{index}` genId category) against the palette's display names, preferring the current stage's entry, then a stage-independent one (shrines, interactables). An editor-placed object uses the catalogId it was placed with. An object with no matching entry, including every `tileObject`, is logged (`pick block found no palette entry`) and the selection is left alone.

Every action logs `EditorObjectTools: <what> -> <opType>`. Object removal now deactivates the live object (rather than destroying it), so undo/redo can restore the same object identity by toggling it active through a move action. Pure logic lives in `object_tool.cs` (position, grid lines, stacking, facing, the ops), `palette_scroll.cs` (palette scroll offset), `object_picker.cs` (nearest object) and `palette_pick.cs` (pick block lookup).

### Key, mouse and type commands

These commands feed `EditorInput.Queue` (see "Editor input"), so they reach the editor without OS input or window focus. They do not reach the game's own Rewired input, only editor code that reads `EditorInput`.

- `key`: `action` is `tap`, `down` or `up`. `key` is a `UnityEngine.KeyCode` member name from the list below, matched case-sensitively. `modifiers` is an optional array of names from the same list and is only valid for `tap`; the modifiers are held around the tap.
- `mouse`: `action` is `move`, `click`, `down`, `up` or `clear`. `move` requires `x` and `y`. `click`, `down` and `up` take an optional `button` (0 left, 1 right, 2 middle; default 0) and an optional `x` and `y` (both or neither) that move the pointer first. `clear` drops the injected position so the real pointer is used again.
- `type`: `text` is 1 to 200 characters, one character per frame. `\b` is backspace and `\n` is return.

Coordinates are screenshot pixels with the origin at the top left, the same space as a harness screenshot and the `screen` field of `state`. The mod converts them to Unity's bottom-left origin with `ScreenPoint.ToUnity(x, y, Screen.height)`. An unknown key or modifier name, an unknown action, a missing or non-numeric coordinate, an `x` without a `y`, a button outside 0 to 2, `modifiers` on a `down` or `up`, and empty or over-long text are rejected at parse time and reported as `ok:false` in the result file.

### Widget commands

`mouse` needs pixel coordinates read off a screenshot, and a click aimed at a toolbar button that lands a few pixels off hits the terrain instead. The editor knows its own widget geometry, so two commands work by name. Both need editor mode and fail with `editor mode is off` otherwise.

- `ui-tree` returns `{"widgets":[{"name","x","y","width","height","enabled"}, ...]}` with each rect in screenshot pixels (origin top left, the space of `mouse` and `screen`). With both `x` and `y` it also returns `"at"`, the name of the first listed widget containing that pixel, or `null` over the world; a half pair is rejected at parse time. Specific widgets are listed before the panels around them (`Toolbar`, `LoadPanel`, `PalettePanel`), so `at` names the innermost widget.
- `click-widget` takes `name`, matched case-insensitively against the `ui-tree` names, and queues a left click on the widget's centre through the same path as `mouse click`, so the editor handles it like a real click and the effect lands over the next frames. It returns the widget's rect. An unknown name is rejected with `no widget named '<name>'; known: ...`, and a disabled widget with `widget '<name>' is disabled`.

Widget names: the toolbar's tool labels `Tool:<tool>` (`Tool:Raise`, `Tool:Lower`, `Tool:Slope`, `Tool:Remove`, `Tool:Place`, `Tool:Select`); toolbar buttons `Undo`, `Redo`, `Validate`, `Save`, `Load`; the save-name field `SaveInput`; the load list `LoadRow<n>`, `PreviousLevels`, `NextLevels` and `LoadPanel`; palette entries `Palette:<catalog id>` (the id as `state` and level files serialize it); palette tabs `Tab:<label>`; and `PaletteChevron`, `PalettePrevious`, `PaletteNext`, `PaletteSearch`, `PalettePanel`. Toasts appear as `Toast<n>` while shown. `enabled` is false for a widget that ignores clicks: `Undo` and `Redo` while the stack has nothing to undo or redo. A hidden widget is not listed: palette entries off the current page or filter, and toasts that are not shown. Clicking a tool label, with the mouse or `click-widget`, selects that tool exactly like its hotkey (`Alpha1` to `Alpha6`, which still work), and the click is consumed by the toolbar so it never edits the terrain underneath. To click one that is missing, change the page or filter first, then call `ui-tree` again.

Valid key names (`key_names.cs`): `A` to `Z`, `Alpha0` to `Alpha9`, `Keypad0` to `Keypad9`, `F1` to `F12`, `UpArrow`, `DownArrow`, `LeftArrow`, `RightArrow`, `Escape`, `Return`, `Backspace`, `Delete`, `Space`, `Tab`, `LeftShift`, `RightShift`, `LeftControl`, `RightControl`, `LeftAlt` and `RightAlt`. The harness logs a warning at startup for any listed name that `Enum.TryParse<KeyCode>` rejects.

### Save and list commands

`save-level` does what the editor's Save button does without a click. With `level`, that name replaces the save field's text first; the editor normalizes it to a safe file name (`my level` becomes `my_level.mblevel.json`), and the field keeps the saved name afterwards. Without `level`, the field's current text is used. It returns `{"name","path","edits"}`: the file name, its full path in the custom-level directory, and the edit count saved. It fails with `editor mode is off` outside the editor, and with the editor's save error when there is no live run or the write fails. `state` then reports `edits.lastSavedName`, `edits.saveStatus` and `edits.dirty`.

`list-levels` returns `{"directory","levels"}`: the custom-level directory (`<game dir>/UserData/Levels`) and the saved `*.mblevel.json` names, sorted as the editor's Load list shows them. It works outside the editor. A saved file reloads with `load-level` given its full path (`directory` joined with the name), or with the `Load` widget in the editor.

### Querying live objects

`query-objects` reads the running game without a rebuild: it finds every loaded `UnityEngine.Object` of the class named in `type` (short name such as `MapData`, or the full name when the short one is ambiguous) and returns `{"type","count","objects":[{"name", ...fields}]}`. `fields` lists public fields or properties to read besides `name`. Enum values come back as their integer, so a live asset that disagrees with the Il2Cpp dump is visible. Other non-primitive values come back as their `ToString()`. An unknown type or field is a failed result naming it, also when no instance is loaded. The command is read-only and does not depend on the run's pause state.

The MCP tool `query_objects(type, fields?, jq?)` returns that `result` object (not the `command`/`ok` envelope). `jq` is an optional jq expression, run with the jq.py bindings against the result before it is encoded: one output is returned as is, none or several as a list. A jq expression that does not compile fails the call before anything is sent, with the jq parse message; a runtime jq failure is a tool error too. Which map assets exist and what their `eMap` is, in one call:

```text
query_objects(type="MapData", fields=["eMap"])
-> {"type":"MapData","count":5,"objects":[{"name":"MapDesert","eMap":2},{"name":"MapDungeon","eMap":16},{"name":"MapForest","eMap":1},{"name":"MapGraveyard","eMap":8},{"name":"MapHell","eMap":64}]}

query_objects(type="MapData", fields=["eMap"], jq=".objects[] | select(.eMap == 64) | .name")
-> "MapHell"
```

`MapHell` is 64 in the live asset while the Il2Cpp dump's `EMap` enum has Hell at 4, which is the kind of mismatch this exists to expose.

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

Pressed and released flags are true for exactly one frame. A held key or button stays held until its up step. An injected mouse position (screen pixels, origin bottom-left) yields to the real mouse: it is dropped when the real cursor moves more than 2 pixels from where it was at the last injected move, after 10 seconds without a move or button event (unless an injected button is still held, which keeps it for a real-time drag), or on `ClearMouse`; after any of these `MousePosition` is null and `EditorInput.MousePosition` falls back to the real cursor. Calling `BeginFrame` again with the same frame number does nothing.

## Static recomp

The mod runs inside the game through MelonLoader, which loads the mod DLL into the Il2Cpp runtime. A static recomp of `GameAssembly.dll` — rebuilding the game code into a separate native library so the mod can run without Steam or MelonLoader — is a large lift and not yet implemented. This section records the exploration and the path to an offline, macOS-native dev copy.

### Scale

`GameAssembly.dll` is a Windows x86_64 il2Cpp assembly (54.8 MB). The dump `.tools/il2cpp_dump/dump.cs` lists 114,472 methods across 73 images. Image 3, `Assembly-CSharp.dll`, is the game code: 1,221 types and 8,697 methods, of which 841 are the shared empty stub at RVA `0x3321E0`/`0x3321F0`, leaving about 7,850 real bodies. The other 72 images are Unity modules and third-party packages (Rewired, `com.rlabrecque.steamworks.net`, Discord, Newtonsoft, ProBuilder, TextMeshPro, Localization, Splines, Postprocessing, MK.Toon, Coffee.UIParticle, …). The ~18,200 types in the dump are the game's, not the mod's; the mod source (`src/MegabonkLevels.Mod/`, net6.0, ~14k lines) binds a small subset. libil2cpp is statically linked into `GameAssembly.dll` (it exports 240 `il2cpp_*` functions), so there is no separate runtime to embed. REA + Ghidra analysis of the binary takes ~12 minutes per session. REA (`/morluto/rea`) is an analysis CLI/MCP (decompile, xrefs, def-use tracing); it does not emit compilable source — reconstruction is hand-authored. The Mac runs the Windows build under CrossOver, so a recomp buys macOS-native execution and drops Steam/MelonLoader from the dev loop rather than cross-platform portability (the game already ships Linux and Windows builds).

### Entry point

The mod is a MelonLoader plugin: `megabonk_levels_mod.cs` carries `[assembly: MelonGame("", "Megabonk")]` and `[assembly: MelonInfo(...)]`, and `MelonMod.OnInitializeMelon()` is the hook. MelonLoader's Il2Cpp bootstrap loads `MelonLoader/Il2CppAssemblies/*.dll` stubs and a set of `version.dll` overrides (`version=n,b;d3d11,d3d10core=n,b`, see `launch_game.py`). A recomp's first call back into the game must be a Unity/Mono/Il2Cpp entry (`Il2CppSystem.Reflection.Assembly.LoadFrom` or a game `dllmain`-style hook) to resolve types — there is no "just call the game's main" without the runtime. Candidate entry points are a `version.dll`/`game.dll` proxy (the existing MelonLoader entry point) or the native executable's own import table.

### Interop surface

The mod already mirrors the game's `EMap` flags enum by value (`level_file.cs`) and binds `Il2Cpp`, `Il2CppAssets.Scripts.*` (Managers, Actors/Player, Steam, MapGeneration/ProceduralTiles, Game/Other), `Il2CppTMPro`, `Il2Cppcom.rlabrecque.steamworks.net`, `Il2CppSystem.Action`, `Il2CppSystem.Collections.Generic.List<GameObject>`, `Il2CppReferenceArray<T>`, and `Il2CppConsistentRandom`. The dump confirms methods carry `// RVA: 0x... Offset: 0x... VA: 0x18...` (VA = image base + RVA). The interop surface spans every Unity module plus Rewired, Discord, Newtonsoft, and ProBuilder. A recomp must reproduce the Il2Cpp runtime's managed/native bridge (MelonLoader/Il2CppInterop-style type resolution, delegate marshalling, Il2CppString) or the mod code cannot bind — this is the single largest chunk.

### Steamworks and the offline gate

The game initializes Steam itself before mod code runs (`steam-ready: done` after retries). The mod's only Steam coupling is `Il2CppSteamworks.SteamApps.GetAppBuildId()` in `game_build_id_patch.cs`, called from the harness `SteamReady` case and from level load and save.

Static analysis of the `SteamManager` methods (`SteamManager.Load` `0x18052AC00`, `IsInitialized` `0x18052ABB0`, `Update` `0x18052B310`, `.cctor` `0x18052B3B0`, with callees resolved through `dump.cs`, RVA = VA − 0x180000000) shows the game tolerates a failed `SteamAPI.Init()`: a false result logs `Debug.LogError` and returns, with no `Application.Quit`, no throw and no retry, so `initialized` stays false and `InitComponents` never runs. The main menu, level load and gameplay are not gated on `initialized`. What degrades without Steam: language falls back to a non-Steam default; achievements, stats and leaderboards never init; Discord rich presence and server-real-time skip their Steam parts; `Chatbox` passes a `steamId` of 0; and `SaveManager.Load(bool)` forwards that 0 into `Load(ulong, …)`, where whether it still finds the existing save is unverified. `RestartAppIfNecessary` is called once from `Load` with `AppId_t.Invalid` (0) rather than the real `APP_ID` (3405340, set in the `.cctor`); a true result logs and returns with no quit, but what Steam returns for an invalid id is not verified here. No caller calls `SteamAPI.IsSteamRunning()` or `SteamApps.GetAppBuildId()` — both have only data refs and no code callers.

The verdict is *degraded*, not runtime-verified: the game runs without Steam, but several paths need a live run to confirm. Not covered by this analysis is any DRM or Steam wrapper outside `GameAssembly.dll` (the `UnityPlayer.dll` or the exe); a snapshot of those binaries would be needed.

The non-throwing readiness probe is the game's own `SteamManager.IsInitialized()` (`0x18052ABB0`): it reports the game's own Init result, cannot throw (class-init check plus a static read), and is what the harness's `steam-ready` command targets. `SteamAPI.IsSteamRunning()` only says a Steam client process exists, not that Init succeeded, and the game never calls it. (`SteamClient.IsValid()` is the Facepunch Steamworks API and is not in this game, which uses `com.rlabrecque.steamworks.net`.)

A UnityPy read of `Megabonk_Data/globalgamemanagers` shows `PlayerSettings.forceSingleInstance` False and `runInBackground` True, so Unity itself allows a second copy on one machine; only Steam's single-session-per-account rule blocks it. That single-session conflict is the real gate for running several copies at once:

- A native build launched through Steam still conflicts — one session per account across all devices.
- Several copies at work therefore need either (1) the game running without a Steam session, which counts only if the game tolerates a failed `SteamAPI.Init()` and never calls `RestartAppIfNecessary` with a real id — the offline dev copy below — or (2) separate accounts or licences.
- If (1) holds, several copies already work today on CrossOver, Linux and the Windows VM, with no recomp.

So the offline dev copy (drop Steam from the session) and the macOS-native build (drop CrossOver) are two separate goals: the first unblocks multi-machine development now and needs no recomp; the second is a larger, independent lift.

### Build / relink

The mod builds to `MegabonkLevels.Mod.dll` + `.pdb`, deployed to `$(GameFolder)/Mods/` by the csproj `CopyOutputToModsFolder` target; it references `MelonLoader.dll`, `0Harmony.dll`, `Il2CppInterop.Runtime.dll`, and the Il2Cpp stub assemblies as `<Reference>` (not copied, `<Private>False`). A recomp's output is a native DLL (or patched executable), not a managed assembly, and the linking decision gates everything: if it links the game's own native runtime, it must be loaded by the patched exe; if it bundles a runtime, it is effectively a redistributable.

### Routes

Three ways to a macOS-native, Steam-free build, largest first:

- **A — Full static recomp of the Linux build.** XenonRecomp-style recompile of the Linux `UnityPlayer.so` and `GameAssembly.so` (SysV ABI, Vulkan), plus a Linux-to-macOS shim for libc, windowing and Vulkan-through-MoltenVK. About 85 MB of x86-64 to lift, and no maintained lifter produces rebuildable code at this scale (McSema is archived; remill lifts but its output does not rebuild here). Largest.
- **B — Re-host `GameAssembly` only.** Translate the Linux `GameAssembly.so` into a macOS x86-64 dylib (running under Rosetta) paired with Unity's official 2023.2.22f1 macOS player, reusing `global-metadata.dat` and resolving icalls by name. Blockers: libil2cpp's Linux OS layer (Boehm GC thread suspension, signals) ported to macOS, and shaders — the shipped data is DX11/12 or Vulkan/GL blobs while macOS needs Metal (SPIR-V → MSL via SPIRV-Cross, repacked). Count shader variants with UnityPy.
- **C — pt-pc-style reimplementation.** AssetRipper export, reimplement the ~7,850 `Assembly-CSharp` bodies in C# from `dump.cs` and Ghidra pseudocode, add the packages (TMP, ProBuilder, Localization, Addressables, Splines, PostProcessing, AI Navigation, Steamworks.NET and Coffee.UIParticle are free or OSS; Rewired and MK.Toon are paid), and build for macOS. The mod becomes source in the project with no loader. Risk is behaviour drifting from the shipped game. The pt-pc project (github.com/LoreanXavier/pt-pc) is a reimplementation on its own engine reading the original assets, not a static recomp — the model for this route. AssetRipper's weak spot is shaders.

### Recommendation

Keep MelonLoader for the dev loop. It is proven and works today, and a recomp is a large, hand-authored lift whose make-or-break is the Il2Cpp runtime bridge, not per-function reconstruction. The two goals split cleanly:

- **Offline copy (drop Steam)** — unblocks multi-machine development now and needs no recomp. De-risk it first: confirm in a live run that the game tolerates a failed `SteamAPI.Init()` and that level load/save work with a `steamId` of 0 (or a Steamworks stub that answers `GetAppBuildId`). This is the direct path to "several Macs at once".
- **macOS-native build (drop CrossOver)** — a separate cost-benefit choice between routes B and C, A last. Only worth it if running under CrossOver/Wine is itself the bottleneck.

### Effort / de-risking

The Il2Cpp runtime bridge is the make-or-break; per-function reconstruction is tedious but bounded. Smallest first steps: (1) confirm the game's startup Steamworks behavior under a non-Steam launch — hard-fail or lazy? — which gates whether the offline copy is possible; (2) confirm a recomp can bind the game runtime by symbol (a single native call into `Assembly-CSharp`) with a "hello world" function decompiled from `dump.cs`.

### Real keyboard text

Under plain Wine on macOS (Wine Devel 11) the game receives real key state but no text: `Input.GetKey` and `Input.GetKeyDown` report W/A/S/D, tool hotkeys and Backspace, while `Input.inputString` stays empty for every key. `TextFieldModel.Type` reads characters, Backspace (`\b`) and Return only from the text string, so a text field never saw any of them and typing in the level-name and palette search boxes did nothing. An earlier retest that found typing working on the same setup is unexplained. Return does not arrive as a key-down at all, because Wine shows its window title bar instead, so Enter cannot save a level there; use the Save button. Keypad Enter was not tried because the test keyboard had no numpad. CrossOver and Windows were not compared.

`EditorInput.InputString` therefore uses the real `Input.inputString` when it is non-empty and otherwise rebuilds text from this frame's key-downs through `KeyTextMapper` (`key_text_mapper.cs`, Unity-free and unit tested). The mapper assumes a US keyboard layout: letters, digits, the punctuation keys, Space and the keypad, with Shift selecting the upper character, and Backspace and Return mapped to `\b` and `\n`. A held key does not repeat, because only key-downs are read. On a runtime that delivers `inputString`, the fallback never runs.

With the dev harness enabled and the editor active, `EditorInput.LogRealTextInput` writes a `RealInput:` line to `Latest.log` for every frame in which the real keyboard produced text or a Backspace or Return key-down. A line carries the escaped `Input.inputString`, its character codes, the key-downs, and `focused=true|false` for whether an editor text field had focus. It reads `UnityEngine.Input` only and never the injected queue, so harness-typed text and the key-down fallback do not appear as text. To use it, relaunch, click the game window and a text box, press keys on the real keyboard, and read the log with `log_tail` and the pattern `RealInput`. No line for a keypress means the game never received it. A line with `focused=false` means a key arrived but no field had focus. A line with `focused=true` and an unchanged box means the field received the input and did not take it.
