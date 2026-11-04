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
| List the shader, keywords, textures and colours of every material under the objects whose name contains the argument, default Warehouse (see [asset-bundles.md](asset-bundles.md)) | `{"command":"material-dump","object":"<name>"}` | `run.py material-dump [object]` |
| Save the rendered frame as a PNG | `{"command":"screenshot","path":"<file>"}` | `run.py screenshot <out.png>` |
| Freeze gameplay | `{"command":"freeze"}` | `run.py freeze` |
| Resume gameplay | `{"command":"resume"}` | `run.py resume` |
| Make the player survive enemy damage | `{"command":"invulnerable"}` | `run.py invulnerable` |
| Restore normal player damage | `{"command":"vulnerable"}` | `run.py vulnerable` |
| Apply 1–99 integer damage, preserving 1 HP by default | `{"command":"damage","amount":37,"nonlethal":true}` | `run.py damage 37` |
| End the run at once by killing the player (ignores invulnerability) | `{"command":"kill"}` | `run.py kill` |
| Run the game's own restart, the death screen's Retry button | `{"command":"restart-run"}` | `run.py restart-run` |
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
| Read or set a player item amount | `{"command":"item","name":"Mirror"}` or `{"command":"item","name":"Mirror","amount":3}` | `run.py item Mirror`, `run.py item Mirror 3` |
| Profile frame time over a measurement window (see "Frame-time profiling") | `{"command":"perf","action":"start"}`, `{"action":"report"}`, `{"action":"status"}`, `{"action":"reset"}`, `{"action":"spawn","count":120}`, `{"action":"timescale","value":4}`, `{"action":"toggle","target":"KillFloor","enabled":false}`, `{"action":"vsync","enabled":false}`, `{"action":"health","hp":1000000}` | `run.py perf start\|report\|status\|reset`, `perf spawn --count N`, `perf timescale [--value X]`, `perf toggle --target NAME --enable\|--disable`, `perf vsync --disable`, `perf health [--hp N]` |
| Hold or release the slide button the grind gate reads (see "Grind gate") | `{"command":"grind-slide","held":true}` or `{"command":"grind-slide"}` | `run.py grind-slide <on\|off\|auto>` |
| Read the live player's fall-damage inputs (see "Fall damage") | `{"command":"fall-damage"}` | `run.py fall-damage` |
| Move the player | `{"command":"teleport","position":[x,y,z]}` or `{"command":"teleport","cell":[cx,cz]}` | `run.py teleport X Y Z`, `run.py teleport --cell CX CY` |
| Pick an upgrade in the open level-up dialog | `{"command":"dismiss-levelup","choice":0}` | `run.py dismiss-levelup [--choice N]` |
| Close, pick or skip the open reward window (level-up, shrine offers, chest, microwave) | `{"command":"dismiss-offers"}` / `{"command":"dismiss-offers","choice":N}` / `{"command":"dismiss-offers","skip":true}` | `run.py dismiss-offers [--choice N] [--skip]` |
| Activate the nearest interactable through the game's own `Interact` (see "Interactables") | `{"command":"interact"}` / `{"command":"interact","type":"Magnet","maxDistance":8,"force":true}` | `run.py interact [--type SUBSTRING] [--max-distance N] [--force]` |
| Decode or audition runtime mp3 PCM (see "Runtime music probe") | `{"command":"music-probe","action":"play","path":"01 Police Truck.mp3"}` | `run.py music-probe <action> [path] [--variant il2cpp\|managed] [--value N]` |
| Quit the game | `{"command":"quit"}` | `run.py quit [--stop-steam] [--stop-menu]` |
| Relaunch the test level in editor mode | Multiple commands | `run.py relaunch [level] [--map N] [--stage N] [--tier N] [--seed N] [--stop-steam] [--stop-menu]` |
| Run the quit teardown with no harness marker and no running game | — | `run.py teardown [--stop-steam] [--stop-menu]` |

`load-level` takes optional integer fields `map`, `stageIndex`, `tier` and `seed` that replace those fields of the level file for that load only. The mod merges them in memory after reading the file, so the file on disk is not modified and no temporary level file exists. `run.py load` and `run.py relaunch` spell them `--map`, `--stage`, `--tier` and `--seed`; the MCP `load` and `relaunch` tools take `map`, `stage`, `tier` and `seed`. `map` is an `eMap` value as listed in `level-format.md` (Forest 1, Desert 2, Graveyard 8, Dungeon 16, Hell 64). A value that is not an integer, or a `map` that is not one of those values, is rejected when the command is parsed, naming the field; the CLI and MCP reject a non-integer before sending anything. A `stage` outside the chosen map's stage range is rejected by the loader with `LevelLoader: load failed: stageIndex N out of range for <map> (M stages)` in the game log, which `relaunch` reports as a failed load, with that log line in its error. Without overrides the level file is loaded as written.

`run.py cycle <level> <out.png>` runs load, waits `--settle` seconds (default 5), takes the screenshot, then quits. `--invulnerable` makes the player invulnerable right after the load, before the settle wait. `--freeze` freezes gameplay and `--camera X Y Z RX RY RZ` poses the camera after the settle wait and before the screenshot. `--timeout` (before the subcommand, default 15 seconds) sets how long to wait for each command and for the PNG to appear. The exit code is 0 only if every step succeeded, 1 if a step failed or timed out, and 2 if the harness is not enabled (`run.py` prints `harness not enabled at <dir>; run 'run.py enable' and relaunch the game`).

On every platform, every quit (`run.py quit`, `run.py teardown`, and the quit inside `relaunch` and `cycle`) also stops the processes a game leaves behind: Wine's session stubs (`services.exe`, `plugplay.exe`, `rpcss.exe`, `svchost.exe`, `winedevice.exe`, `conhost.exe`, `explorer.exe /desktop`, `tabtip.exe`, `lsass.exe`, `winemenubuilder.exe`), which otherwise pile up as extra MelonLoader console windows; orphaned game helpers such as `UnityCrashHandler64.exe`, which the game leaves running after its own process exits; and Steam's own launcher wrappers for app id 3405340 (`reaper SteamLaunch AppId=3405340`, `srt-bwrap`, `pv-adverb`), which hold a Proton prefix open after the game dies. The stop is a `SIGTERM`, but a Wine stub whose `wineserver` died first never processes it — a `winedevice.exe` in that state sits on forever — so after a 1.5-second grace the cleanup `SIGKILL`s whatever is still running (`quit: force-killed N stubborn Wine processes`). Leftover stubs make the next boot race stale Wine plumbing, one way a fresh launch can die seconds after MelonLoader's `0 Plugins loaded` line, and a Linux box whose quit skipped this step accumulated dozens of stubs and a `(not responding)` console window per run. A leftover `wineserver` is not killed by the quit; `relaunch` waits for it to exit (killing it after a short grace) before launching, so a fresh session never races the previous one's teardown — a relaunch into a prefix that was not fully torn down used to die several seconds into boot, right after MelonLoader's `0 Plugins loaded` line.

Only processes belonging to the resolved prefix are killed. A process is ours when its `WINEPREFIX` names that prefix, when its `STEAM_COMPAT_DATA_PATH` names the directory holding it (Proton exports that instead of `WINEPREFIX`, so it is the signal a Steam-launched run actually leaves behind), or when one of its argv entries contains a `drive_c` or `pfx` root that resolves to it; anything attributed to another prefix is never touched, so a second prefix — another game, another Proton version — survives a quit. Even our own stubs wait while another live Windows process shares the prefix, which is what keeps the cleanup from pulling Wine's services out from under a Steam client that itself runs inside it (the Wine-under-CrossOver layout). A process nothing can attribute waits unless no Windows process is live at all, the old blanket rule kept for exactly that case (CrossOver's stubs expose no readable `WINEPREFIX`, and a host without `/proc` cannot be asked). When anything is held back the quit says so, `quit: leaving Wine leftovers alone while other Windows processes run (pids …)`. The Steam client is never a candidate: it is the basename `steam` or `steam.sh` in argv[0], or the Flatpak id `com.valvesoftware.Steam` anywhere in argv, so a Linux quit clears its own stubs with the client up. The `steam.exe` Proton runs inside the prefix for the overlay is a different thing: it names the game's own directory in its argv, so it is reaped as a game helper, which is right — the steamruntime launcher starts it for that run, so it is part of what the run leaves behind.

Everything the harness needs to know about live processes comes from one provider rather than parsed shell text. On Linux that is `/proc/<pid>/cmdline` and `/proc/<pid>/environ`, both NUL-separated, so the backslashes and spaces in a `C:\Program Files\…` path cannot corrupt field splitting and the environment is available for attribution; kernel threads and zombies have an empty `cmdline` and are skipped. Everywhere else it is one `ps -axo pid=,args=` with `LC_ALL=C` and the header suppressed — `pid` and `args` being the two keywords the BSD and the GNU family both accept, and a pinned locale keeping the columns predictable — with no environment, which is what makes attribution fall back to the blanket rule. Windows keeps its `tasklist /FO CSV` branch. Nothing runs `pgrep` or `pkill`: candidates are matched by exact, casefolded Windows basename over argv, so `C:\games\svchost_my.exe` is not a stub and `tabtip.exe` is, and a signal is only ever sent to a pid the same call listed.

The Steam client and the OS-level menu input service (`run.py menu start`, see [gamepadui.md](gamepadui.md)) outlive a run on purpose, because a relaunch needs both, so they are torn down only when asked for: `--stop-steam` and `--stop-menu` on `quit`, `relaunch` and `teardown`, or `task game:stop -- --stop-steam --stop-menu`. `--stop-steam` asks the client down through `steam steam://shutdownsteam`, or `flatpak run com.valvesoftware.Steam steam://shutdownsteam` where only the Flatpak exists, waits for it, then `SIGTERM`s the pids it listed and allows 10 seconds before `SIGKILL`ing survivors — deliberately not the Wine stub's 1.5-second grace, because a client that is saving state needs longer and was being killed outright. It reports `stop-steam: Steam is not running` when nothing was listed, and `stop-steam: stopped N Steam process(es) after SIGTERM` when the signals did the work. Expect the request itself to be ignored on the current Linux client: like the gamescope session noted in [gamepadui.md](gamepadui.md), it prints its confirmation and does nothing, so the `SIGTERM` is what actually lands. Two more caveats from that host: the gamescope session brings the client straight back, and `--stop-steam` on a `relaunch` means the launch that follows starts Steam again, so the next run pays for the client's logon. `run.py teardown` is the same teardown with no harness marker and no running game required, for clearing a box that is already littered; `menu: input service not running` is a success, so `--stop-menu` is safe to repeat.

A game can also be alive but unable to answer: the harness polls from MelonLoader's `OnUpdate` on the Unity main thread, and a window macOS has suspended (typically an editor left idle for a long time) stops that thread, so a `quit` sits in `harness/commands/` unprocessed until it times out. `quit` escalates in that case: after the command times out, if the process is still running it force-kills every process running out of the game directory (`quit: force-killed N game processes`) and waits again. Only a game that survives even the force kill is reported as a failed quit. Because a timed-out command stays in the queue and a fresh session would run it at boot (a stale `quit` would quit the new run), `relaunch` empties `commands/`, `processing/`, `done/`, `rejected/` and `results/` before launching.

`run.py relaunch` quits the running game, waits for the previous session's `wineserver` to exit (killing it after a 15-second grace if it lingers, printing `relaunch: force-killed N lingering wineserver(s)` and `SIGKILL`ing any Wine stub that outlives it), empties the harness queue, starts a fresh process through `task game:run` (`task crossover:run` when `MEGABONK_MACOS_RUNTIME=crossover`), waits for the new session's `DevHarness: enabled` log entry — the log must have been written after the launch, so the previous session's line cannot satisfy the wait — then polls the in-game Steamworks client before loading `levels/example-forest.mblevel.json`. Both waits also watch the game process: once the startup grace passes, a missing Megabonk process ends the relaunch at once with `relaunch: game exited during startup (see <Latest.log>)` instead of waiting out the timeout. That error first copies the dead boot's logs — `MelonLoader/wine-latest.log`, `Latest.log`, and the two Unity `Player*.log` files — into `~/Library/Logs/megabonk-relaunch-failures/<timestamp>/` (`MEGABONK_EVIDENCE_DIR` overrides the root) and appends `evidence saved to <dir>`, because every later launch rotates `wine-latest.log` over its `.prev` and destroys the only copy. Every relaunch failure then force-kills any game process and reaps the Wine leftovers, so a failed relaunch leaves no wedged game or stale stub behind for the next attempt. A Steamworks client that answers `ready:false` and keeps answering — the offline case on the Steam stub, where the game's `SteamManager` has already failed init and will not retry — is accepted after a 15-second grace with the step `relaunch: Steamworks not ready (offline run); continuing`; only a client that never answers at all fails with `relaunch: Steamworks did not become ready`. It retries the load until `KillFloor: armed` appears, then enables editor mode. The player gets 2 Feathers (extra jumps) through the `item` command; `MEGABONK_RELAUNCH_FEATHERS` sets another amount from 0 to 999, and 0 leaves them alone. Enemy spawns stay on and the player takes normal damage by default. Set `MEGABONK_RELAUNCH_SPAWNS=false` in the environment or `.env` to stop spawns after the load (see "Enemy spawns") and `MEGABONK_RELAUNCH_INVULNERABLE=true` to make the player invulnerable (see "Player invulnerability"); `task` loads `.env` through the `dotenv` directive in `taskfile.yml`, so `task game:editor` sees both. The MCP `spawns` and `invulnerable` tools and `run.py spawns` and `run.py invulnerable` change either at runtime. It allows at least 60 seconds for readiness checks, even when `--timeout` is lower. Pass an optional level path to use a different level file. `--no-level` (MCP `relaunch(no_level=true)`) stops at the main menu once Steamworks is ready, with no level loaded and no editor, for checking the stock menu screens. Use this command between interactive editor sessions; do not send another `load` to an existing run. A second `load` while in editor mode is survivable: `LiveEditPatch` hides its session while the old tile generator is destroyed, so the editor tools find no grid until the reloaded level finishes generating, and the editor re-enters on the new run.

The game is launched with `--melonloader.agfoffline` (in both `scripts/launch_game.py` and the CrossOver `cxstart` task), keeping the assembly generator's version checks offline and using its locally cached dependencies. This flag does not fix missing macOS graphical-session access under SSH.

Under plain Wine, `scripts/launch_game.py` does not start `wine` directly: it detaches a small watcher process (`launch_game.py watch --log FILE -- wine …`) that runs the game, sends its stdout and stderr to `MelonLoader/wine-latest.log`, and appends `wine: game process exited with status N` when the game exits — only the game's parent can reap it, and a negative `N` means it was killed by signal `N`. The previous launch's log rotates to `wine-latest.prev.log` the way Unity rotates `Player.log`. The game launches with `WINEDEBUG=-all,err+seh,warn+seh,err+module,trace+loaddll` so an unhandled exception prints its Wine backtrace, a missing DLL reports an `err:module` line, and the last `trace:loaddll` line shows how far module loading got before an early exit, while everything else stays silent. MoltenVK and DXVK need their own caps — `MVK_CONFIG_LOG_LEVEL=1` and `DXVK_LOG_LEVEL=error` — because they write to stderr outside Wine's debug channels, and MoltenVK's descriptor-pool warnings alone pour out hundreds of megabytes a minute at their default level. When the game dies during startup and `Latest.log` stops mid-boot, that file holds the reason the terminal never showed; compare it with the two Unity logs under `drive_c/users/crossover/AppData/LocalLow/Ved/Megabonk/` (`Player.log` for the failed boot, `Player-prev.log` for the healthy one before it). The watcher opens the log with a `watch: launched pid=… ppid=… session=… cwd=… tty=…` header, the full argv, and the environment variables whose names start with `WINE`, `DOTNET_`, `DYLD_`, `MVK_`, `DXVK_`, `MEGABONK_`, or `Steam`, so two launches can be compared after the shells that started them are gone.

`MEGABONK_RELAUNCH_DIAG=true` (environment or `.env`) enables extra exception diagnostics: `UnityCrashHandler64.exe` is renamed to `UnityCrashHandler64.exe.disabled` before the launch and `+seh` is appended to `WINEDEBUG` (through `MEGABONK_WINEDEBUG_EXTRA`), with Wine's `ShowCrashDialog` registry value set to 0. The next non-diagnostic relaunch restores the handler and drops the extra channel. Exit status 1 alone is not evidence of a native crash: Unity also deliberately exits that way after a failed window creation, without raising an unhandled exception.

An unknown command, malformed JSON, a missing or empty `path`, or a command that fails while running logs an error and moves the file to `rejected/` without replaying it.

The paths in `load-level` and `screenshot` are interpreted by the game process, so `run.py` converts them (see below).

### Launching and driving the game from SSH on macOS

For plain Wine, use the same commands from SSH as from the desktop:

```sh
task game:editor
uv run scripts/run.py state
uv run scripts/run.py screenshot /path/to/frame.png
uv run scripts/run.py quit
```

The same user must already be logged in to the Mac's graphical desktop. `scripts/launch_game.py` checks `Security.SessionGetInfo` for graphical access. A caller without it is handed off to a one-shot LaunchAgent in `gui/<uid>`; the watcher and Wine then run in the GUI session, while the existing file-based harness remains accessible over SSH. `task game:steam` uses the same handoff. No sudo, debugger wrapper, or desktop-terminal command is needed. This handoff does not cover the separate CrossOver launcher.

Without the handoff, Wine's macOS display driver can reject the SSH security session and unload before graphics initialization. Unity then exits with `Failed to create window`; MelonLoader can stop at `0 Plugins loaded` and `Player.log` can contain only physics initialization. Disabling the crash handler or redirecting stdin does not fix graphical-session access.

LaunchAgent definitions live under `~/Library/Application Support/Megabonk/launchd/`, not `~/Library/LaunchAgents/`, so nothing is configured to start at the next login. Jobs run once, without automatic restart. A stopped job is removed before reusing its prefix/target-specific label; a running or pending job is refused rather than killed. The resolved argv, Wine overrides and working directory are preserved. Only runtime environment settings (Wine, .NET, graphics, locale, path and the mod's diagnostic flags) are forwarded; unrelated SSH credentials and API tokens are not copied into the plist. Game output still goes to `MelonLoader/wine-latest.log`; Steam's launch output goes beside its plist. A missing GUI domain or rejected bootstrap reports a launch error instead of silently falling back to a headless start.

Omit the old machine-local `.tools/exit-trace/wine` override and leave `MEGABONK_RELAUNCH_DIAG` unset or false for ordinary SSH launches. The Mac must remain logged in and awake; this is not a headless replacement for its desktop session.

### Runtime music probe

With the harness enabled and a run loaded, copy an mp3 into the game's `UserData/CustomMusic/`, then use:

```sh
uv run scripts/run.py music-probe decode "01 Police Truck.mp3"
uv run scripts/run.py music-probe native-info
uv run scripts/run.py music-probe native-tone
uv run scripts/run.py music-probe native-play "01 Police Truck.mp3"
uv run scripts/run.py music-probe pitch --value 0.55
uv run scripts/run.py music-probe pitch
uv run scripts/run.py music-probe lowpass --value 400
uv run scripts/run.py music-probe lowpass
```

`native-info` resolves internal calls and reports their module/RVA and a short code prefix without creating a clip. `native-tone` creates a two-second, 440 Hz test clip; `native-play` decodes the mp3 into a real clip using the shared bounded decoder/resource owner. Both use the game's normal `MusicTrack` playback with no injected filter, and report clip length and maximum PCM roundtrip error across every uploaded block. Input is limited to 64 MiB compressed and 256 MiB decoded PCM per track; see [music.md](music.md#production-decoder-and-ownership). The native ABI is verified only on Win64 (including Wine); other platforms are rejected pending inspection. Native calls can crash the process if the ABI changes, so use a disposable test run. Relaunch to restore stock music after a native probe; `stop` and `detach` affect buffer injection only. Native resources are also released once another game track takes over.

For comparison, the older buffer-injection path is:

```sh
uv run scripts/run.py music-probe play "01 Police Truck.mp3"
uv run scripts/run.py music-probe status
uv run scripts/run.py music-probe detach
```

Paths are interpreted by the game; a file name resolves under `UserData/CustomMusic/`. Both playback paths decode the entire file synchronously. `play` loops PCM through a filter without resampling; `native-play` declares the clip's source rate so Unity handles sampling. This is a diagnostic, not a level music format. `decode` reports sample rate, channels, decoded samples, duration and peak; `status` reports callback counts, consumed frames, average copy time, source controls and probe errors. After `native-play`, its `decodeMs` includes native creation/readback as well as decoding. Its `playing` and `attached` fields describe buffer injection only, not native clip playback; inspect `sourceIsPlaying`, `sourceClip` and `stockTrack` for that. A failure can be reported as `error` inside the returned probe object; inspect it as well as the harness envelope.

Actions are `decode`, `native-info`, `native-tone`, `native-play`, `play`, `stop`, `status`, `restart`, `duck`, `unduck`, `pause`, `unpause`, `mute`, `unmute`, `clip-null`, `pitch`, `lowpass`, `detach`, `radio-next`, `seek`, `menu-music` and `stage-music`. `duck` defaults to 0.2; `--value` overrides it, sets source pitch, or sets source low-pass cutoff in Hz. Pitch and cutoff with an explicit value are held by a postfix after `MusicController.Update`, because the game otherwise resets them before a listener can compare. `pitch` without a value releases the hold and sets 1; `lowpass` without a value releases the hold and sets 22,000 Hz, then leaves subsequent changes to the game. Confirm `heldPitch`/`heldCutoff` and a later property reading when testing. `unduck` sets both duck multipliers to 1. `stop` stops overwriting samples; `detach` also removes the injected component and releases held controls. Neither restores a clip removed with `clip-null` nor resets mute; relaunch for a clean stock baseline after destructive comparisons. `restart` restarts the source, but is not required when attaching to a playing source.

For integration checks, `radio-next` invokes the scene boombox's real `Interact` method, `seek --value <seconds>` moves within the current clip (use near its end to exercise progression), and `stage-music` calls the normal stage playback path. `menu-music` calls the music controller's menu handler, exercising session cleanup without navigating the UI; it does not leave the run itself. `status` includes `levelMusicReference` and `runtimeSession`. Relaunch with a level containing a `track:` reference to test production startup discovery/selection, rather than using `native-play`, which bypasses them.

The default `--variant il2cpp` uses the working `Il2CppStructArray<float>` signature. `managed` reproduces the unsupported `float[]` callback, which Unity never dispatches. Detach before comparing variants. Frozen editor gameplay is not an audio pause and does not prevent the game resetting audio properties; use the held controls for comparisons. Duck multiplier propagation through `MusicController.Update` was observed with resumed gameplay. See [music.md](music.md#runtime-pcm-probe) for the audible results and limitations.

### Results

Before moving a command file to `done/` or `rejected/`, the mod writes `harness/results/<command file name>`: UTF-8 JSON, one object, written to `<name>.tmp` and renamed so a reader never sees a partial file. A command that succeeds writes `{"command":"<wire name>","ok":true,"result":<object or null>}`. A command that fails while running writes `{"command":"<wire name>","ok":false,"error":"<message>"}`. A file that does not parse writes the same failure shape with `"command":null`. Every command other than `state`, `ui-tree`, `click-widget`, `save-level`, `list-levels`, `query-objects`, `teleport`, `grind-slide`, `dismiss-levelup`, `dismiss-offers`, `interact`, `music-probe` and `steam-ready` has `"result":null`. The result file is written before the command file moves, so a caller that sees the file in `done/` or `rejected/` can read the result at once. Result files are never deleted by the mod.

`run.py` reads them with `read_result(harness, name)`, which returns `None` when the file is absent or not valid JSON. Every subcommand that sends a command exits 1 and prints the `error` text on stderr when the result has `ok:false`, even if the command file landed in `done/`. A missing result file does not fail a command, so `run.py` still works against a mod built before results existed.

### Steamworks readiness

`steam-ready` succeeds with `{"ready":true,"buildId":"<id>"}` once the game's Steamworks client answers `GetAppBuildId`, and with `{"ready":false}` while it is still starting. The not-initialized fault is an expected answer during startup, so `SteamReadiness.Probe` catches that one message (`Steamworks is not initialized`) and returns it as data instead of letting it reach the harness's generic error handler, which would log an ERROR with an IL2CPP stack trace on every poll. Any other fault still propagates and is logged. `run.py steam-ready` exits 1 on `ready:false`. `run.py relaunch` polls the same verdict: it proceeds on `ready:true`, continues after a 15-second grace once a definite `ready:false` has stood (the offline case, where the client will never become ready), fails with `relaunch: Steamworks did not become ready` only if the game never answers at all, and ends at once with `relaunch: game exited during startup` if the game process dies while polling. A mod that returns no result counts as ready. A long-running caller such as the MCP server has to be restarted to pick up a changed `run.py`; an old one treats any `ok:true` as ready.

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

Tools: `relaunch(level?, map?, stage?, tier?, seed?)` (reports progress through the MCP context and returns the final `state`), `load(level, map?, stage?, tier?, seed?)`, `quit()`, `screenshot(directory?, filename?, overwrite?, scale?, crop?)` (returns the PNG inline), `state()`, `editor(on)`, `freeze()`, `resume()`, `invulnerable(on)`, `kill()`, `restart_run()`, `spawns(on)`, `camera(position?, rotation?, clear?)` `log_tail(pattern?, since_launch?, max_lines?)`, `log_wait(pattern, timeout?, since_launch?)`, `paths()`, and the input and gameplay tools `key(key, modifiers?, action?)`, `mouse(action, x?, y?, button?)`, `ui_tree(x?, y?)`, `click_widget(name)`, `save_level(level?)`, `list_levels()`, `query_objects(type, fields?, jq?)`, `type_text(text)`, `teleport(position?, cell?)`, `item(name, amount?)`, `grind_slide(held?)`, `dismiss_levelup(choice?)`, `dismiss_offers(choice?, skip?)` and `interact(type?, max_distance?, force?)`. A command the mod rejects, a timeout, or a result with `ok:false` surfaces as a tool error carrying the result file's `error` text (or `<command> <outcome>` when there is no result file). `log_tail` reads `MelonLoader/Latest.log`: `since_launch` (default true) trims to the last `DevHarness: enabled` line, `pattern` keeps lines matching a regex (an invalid regex is a tool error carrying the parse failure), and `max_lines` (default 50) caps the result to the last N matching lines. The input tools validate their arguments before sending anything and raise a tool error for a bad combination: `teleport` needs exactly one of `position` (three numbers) or `cell` (two integers), `mouse` `move` needs both `x` and `y` and the other actions take both or neither, `key` accepts `modifiers` only with `action` `tap`, and `key` checks the key and modifier names against the mod's list (a mirror of `key_names.cs`, kept in step by a test) so an unknown name fails with the valid names before anything is sent. `ui_tree` takes both or neither of `x` and `y`. `paths()` returns `{game_dir, harness, latest_log, levels_dir}`, where `levels_dir` is `<game_dir>/UserData/Levels`, the folder the editor saves custom levels to. `log_wait` polls `Latest.log` until a line matches the regex `pattern`, returns that line, and is a tool error after `timeout` seconds (default 30) or for an invalid regex; `since_launch` (default true) ignores lines before the last `DevHarness: enabled`. Use it after `load` or `relaunch` instead of sleeping, for example `log_wait("KillFloor: armed")`. Each returns the result file's object (`ui_tree`, `click_widget`, `save_level`, `list_levels`, `teleport`, `grind_slide`, `dismiss_levelup`, `dismiss_offers` and `interact` carry data; the others return `null`). Coordinates are screenshot pixels with the origin at the top left, as in "Key, mouse and type commands", which also lists the valid key names. Input is queued over the next frames, so a `screenshot` straight after may predate its effect.

### Retaining screenshots

`screenshot(directory=None, filename=None)` returns two content blocks: the inline PNG and text reporting its saved absolute path. With no arguments it saves `megabonk-<timestamp-in-nanoseconds>.png` in the repository's gitignored `.tools/evidence`, so captures never land in the working tree. Optional keyword arguments select the destination:

```python
screenshot()
screenshot(directory=".tools/evidence")
screenshot(directory=".tools/evidence", filename="final-editor-slope.png")
screenshot(directory="/path/to/screenshots", filename="forest.png")
```

Relative directories resolve against the server's working directory; absolute directories are supported. Missing directories, including parents, are created automatically. `filename` must be a single basename ending in `.png`, not a path; path separators and invalid filename characters are rejected. Omit it for a timestamped name in the chosen directory.

Existing files, directories and symlinks are not overwritten by default: a collision returns a tool error asking for another filename or directory, including if the destination appears during capture. `overwrite=True` replaces an existing file instead (the capture is moved over it atomically; a directory at the destination is still an error). The server captures into a temporary subdirectory, validates the PNG, and publishes it using an exclusive hard link on the same filesystem; the filesystem must support hard links. Temporary captures are cleaned up on success or failure, though newly created destination directories remain. Invalid destinations, permissions and capture failures return actionable tool errors rather than a saved path. `crop=[x, y, width, height]` (screenshot pixels, applied first) and `scale` (greater than 0, at most 1) shrink the inline image to cut token cost; the saved file is always the full capture. A crop outside the capture or a bad `scale` is a tool error. A server restart is needed to pick up changes to its tool signatures.

To verify retention through MCP, call `screenshot(filename="editor-check.png")`, inspect the inline image and open the reported path as a PNG. A second call with the same arguments must return a collision error and leave the first PNG unchanged.

### End-to-end check

A walkthrough that exercises the whole chain (agent, MCP, harness files, mod, game) using only the `megabonk` tools, in editor mode on the example forest level:

1. `relaunch()` quits any running game, starts a fresh one, loads `levels/example-forest.mblevel.json` and enters editor mode. The returned state has `editor: true`.
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

## Remote Steam hosts and gamepadui

Standing up a gamescope + Steam gamepadui session, forcing the Proton baseline
and measuring the real prefix, installing and verifying the player package,
transferring THPS content, and driving stock menus over SSH with `run.py menu`
are documented in [gamepadui.md](gamepadui.md). The player package needs Python
3.11 or newer on the target, but no repository checkout, uv, .NET SDK or separate
Wine installation.

### GNOME screenshots over SSH

GNOME exposes screenshot capture through D-Bus. Direct calls to
`org.gnome.Shell.Screenshot` can return `AccessDenied` over SSH; use the session
bus's `org.freedesktop.portal.Desktop` service at
`/org/freedesktop/portal/desktop`, calling
`org.freedesktop.portal.Screenshot.Screenshot` with an empty parent window and
`interactive=false`. Subscribe to `org.freedesktop.portal.Request.Response`
before calling: the method returns a request handle, while the response supplies
the saved PNG's `uri` (on success, response code 0). This worked over SSH in the
logged-in GNOME session, saving under `~/Pictures`; retrieve that file with
`scp`. Unlike a nested Xwayland capture, it showed the game's warning overlay.

### Verified menu regression under Proton

Verified on 2026-10-31 under Proton Experimental with Megabonk 1.0.69 and MelonLoader 0.7.3 (see [gamepadui.md](gamepadui.md) for the host setup), the installed Windows THPS pack, and Calcium selected. Input came through Linux uinput mouse clicks (with X11 absolute pointer positioning) and a virtual Xbox 360 controller into the stock menus; the harness supplied screenshots, read-only object queries and quit between DLL builds. No save reset, developer character override or `load-level` command was used.

1. On Forest, select Tier 3, then select Warehouse. Only Tier 1 remains visible, selected and selectable; hidden tiers are unselected and cannot be selected. Click Tier 1 and Confirm with the mouse: Warehouse renders and the pause panel identifies `Warehouse / Tier 1`.
2. Using controller D-pad/A, select Forest Tier 3, move left to the map list, down to Warehouse and select it. Focus lands on visible Tier 1. Down goes directly to Challenges and Up returns to Tier 1. Selecting Tier 1 again moves focus to Confirm; A starts Warehouse. The final launch logged `LevelLoader: starting map=Forest stage=0 tier=0 seed=20261007`, then `KillFloor: armed`, and the rendered pause panel identified Warehouse.
3. Switch from Warehouse to a native map before starting. Forest again offers its three unlocked tiers, and controller navigation can select Tier 3. Graveyard retains its native single-tier layout. Selecting a different native map can leave focus in the map list; select the same entry again to move into its tiers, as in the unmodified menu.

Regression unit tests cover a locked first tier with a stale higher-tier selection, navigation repair on refresh without premature selection, and repair after native visibility has been restored. Keep the group indexes stable during the native handler; hiding buttons alone reproduces the stale hidden-tier bug.

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

Process detection uses the standard library only: `/proc/<pid>/cmdline` and `/proc/<pid>/environ` on Linux, one `ps -axo pid=,args=` with `LC_ALL=C` on macOS and any host without `/proc`, and `tasklist` on Windows (not exercised on a Windows host); see the process enumeration under "Commands". A process counts as the game only when its argv is the game executable itself, `...\Megabonk.exe` under Wine or `Megabonk.x86_64` natively. Helpers that only mention the executable, such as `winewrapper.exe` and a shell running the launch command, are ignored — `UnityCrashHandler64.exe` and `winemenubuilder.exe` are reaped as leftovers instead. If `quit` times out because the game is hung, it force-kills every process running out of the game directory.

### Loading the THPS level

`levels/thps.mblevel.json` is generated, and its Warehouse mesh and soundtrack clip live in the `thps` pack, so a launch needs both. The level's `music` field names the clip (`bundle:thps/04_Superman`); see [music.md](music.md).

```sh
task thps                                          # extract, build and install the level and the pack
task mod:build                                     # only when the C# changed
task game:editor -- levels/thps.mblevel.json
```

`task thps` (`taskfiles/thps.yml`) runs four steps, each of which skips itself when its inputs are unchanged, so a second run takes under a second:

- `thps:extract` cuts the Warehouse mesh, textures and nodes out of the disc image into `.tools/thps1/warehouse/`. It is skipped once `warehouse.obj` exists; otherwise it needs the disc image in `tools/thps1/` and `THPS2_TOOLS_DIR` in `.env` pointing at a thps2-tools checkout (see [thps-warehouse.md](thps-warehouse.md)).
- `thps:level` regenerates `levels/thps.mblevel.json` with `scripts/build_thps_level.py`. The output is byte-for-byte the same for the same inputs.
- `thps:pack` builds the bundle for Windows and Linux with Unity from `.tools/thps1/warehouse/` and `tools/ost/*.mp3` (both gitignored; without the mp3s the pack builds with no music).
- `thps:install` copies the bundle and manifest into `UserData/LevelPacks/thps` and the level into `UserData/Levels`, through `task pack:install PACK=thps`.

Building a pack requires the disc image, the mp3s and Unity 2023.2.22f1 on the authoring machine. A test machine can instead receive the built bundle with its matching manifest and attachment metadata; the [gamepadui workflow](gamepadui.md#transfer-thps-content-and-test-the-player-menus) shows the transfer and installer commands. Select the bundle for the game runtime, not the host: Proton uses the Windows bundle. The disc path, the extraction marker and the level path are variables that default to their usual values, so `task thps DISC=<path>` and `task thps LEVEL=<path>` override them. Rebuild runs whenever `ThpsPack.cs` or the pack inputs change, and a running game only sees the pack and level after a relaunch.

A missing pack does not fail the load. The level opens with a placeholder at the Warehouse position and the log shows `Packs: 'bundle:thps/Warehouse': pack 'thps' is not installed; using a placeholder.` Packs load once per session, so install the pack before the relaunch.

### Preserving the shipped Warehouse

Construction-piece grind and support defaults live in
`unity/pack-authoring/packs/thps/attachments.json`. Regenerate them with
`uv run scripts/build_thps_attachments.py` after rebuilding `pieces.json` or
changing path ownership; `task pack:thps` does both steps and installs the
metadata beside the bundle. Existing saved placements retain their explicit
attachments, so place a fresh piece to test changed defaults. Ctrl-click selects
a hidden grind path instead of its visible owner; posts are normally selectable.
The [attachment contract](asset-bundles.md#piece-attachments) explains ownership,
local transforms and avoiding duplicate supports in a kit assembly.

Run `uv run scripts/check_thps_preservation.py` to compare the shipped Warehouse with
`tests/fixtures/thps-preservation.json`. The same check runs in `task scripts:test`
and therefore `task check`. It regenerates into a temporary directory in a fresh
Python process, never overwriting `levels/thps.mblevel.json`. Both copies must match
the baseline byte-for-byte, including whitespace and the final newline. Differences
include field paths, changed file hashes, missing files, and level text diffs.

The baseline contains the complete level text, derived footprint, placement, boss
spawn, kept cells, coping rails and collectible transforms, required pack entries,
and SHA-256/size fingerprints. The file inventory covers extraction OBJ/MTL/nodes
and PNGs, item overrides, the generated Warehouse prefab, render/collision meshes,
`Warehouse_*.mat` materials, `WarehouseTextures/*.png` textures, their importer
metadata, and the default Superman clip and its source MP3. Unrelated pack assets
and manifest entries may be added; the existing pack id/version and dependencies
must remain unchanged. Whole bundle hashes are deliberately not pinned, since an
additive asset changes the bundle without changing the legacy assets.

This is a strict check, not a skip when proprietary inputs are absent. Prepare the
extraction, soundtrack and generated Unity assets with the THPS setup above before
running it. After pack-authoring changes, rebuild the pack before checking: the
check fingerprints the generated assets on disk, not the C# builder's future
output. It does not inspect an installed bundle or certify in-game rendering.

To deliberately accept a shipped Warehouse change, first review the level and
asset changes, regenerate the level to a separate path and compare it, and rebuild
the pack. Then run:

```sh
uv run scripts/check_thps_preservation.py --refresh
uv run scripts/check_thps_preservation.py
task check
```

Refresh refuses missing inventoried files or a level the generator cannot reproduce.
Review and commit the baseline diff with the intentional change. **Refreshing means
the shipped level or its dependencies changed**; it is not a way to make an
unexplained failure green. Construction-kit additions must preserve this baseline
and use a separate level instead of refreshing it.

The level also places the game's boombox beside the player spawn as a radio. To check it, `relaunch` the level, leave the editor, walk to the boombox and press the interact key; the log shows `Radio: playing '<clip>'.` and each further press plays the next clip in soundtrack order. `Music: using clip '04_Superman'` at load confirms the default track.

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

`relaunch` works unchanged offline. The stub's `SteamAPI_Init` succeeds, so the game's Steamworks client answers `ready:true` and the readiness poll passes normally. If the client instead reports `ready:false` and keeps reporting it (a `MEGABONK_STEAM_FAIL_INIT=1` run, or any degraded init where `SteamManager` has already failed init and will not retry), `relaunch` accepts that after a 15-second grace with the step `relaunch: Steamworks not ready (offline run); continuing` and loads the level anyway, since the loader only needs `GetAppBuildId`, which the stub answers either way. A relaunch that never gets a verdict, or whose game process exits during startup, fails fast with the matching `relaunch:` error rather than waiting out the timeout.

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

## Player items

The `item` command reads or sets the player's stack count of one game item. `name` is a case-sensitive `EItem` member (`Mirror`, `Feathers`, and the rest of the enum in `.tools/il2cpp_dump/dump.cs`). Without `amount` it only reads; with `amount`, an integer from 0 to 999, it sets the count exactly and 0 removes the item. The result is `{"item":name,"before":n,"after":n}`. An unknown or wrongly cased name, a missing `name`, or an `amount` that is negative, above 999, or not an integer is rejected with an error and changes nothing. With no player in the scene the command fails with `no player: start a run first`.

`ItemInventory.RemoveItem` drops one stack per call, so lowering an amount repeats it; raising one is a single `AddItem(item, count)`. `invulnerable` and `vulnerable` use the same routine. Items sent through `item` while invulnerable are not tracked: `vulnerable` still restores the Mirror and Feathers amounts held when `invulnerable` was sent.

## Controlled player damage

`run.py damage <amount>` and MCP `damage(amount=<amount>, nonlethal=true)` accept **any integer from 1 through 99**, not just presets. Each call requests one hit. The independent nonlethal flag defaults to true and caps that hit to preserve at least 1 HP. To permit death explicitly, use `run.py damage 99 --no-nonlethal` or MCP `damage(amount=99, nonlethal=false)`. The flag applies only to that command; it is not persistent invulnerability against enemies or the kill floor. Invalid amounts, nonboolean flags, absent players and dead players are rejected before damage is attempted.

The hit calls `PlayerHealth.DamagePlayerExternal` with `ignoreShield=true`, zero knockback, no attacker and the stock `Enemy` source. It exercises the normal damage checks, `A_TakeDamage` reactions and music danger history; it does not overwrite HP, clear cooldowns, remove items or force pitch. Armor and other game modifiers can change the requested damage. Harness Mirror invulnerability does **not** reliably block this attacker-less external hit: it applied in Wine with the toggle on. Use the default nonlethal flag for safety, not Mirror.

Results include `requestedDamage`, `submittedDamage`, `effectiveDamage` (after game checks and the safety cap, or null if gated earlier), `actualDamage` (sum of positive HP/shield/overheal losses), individual signed losses, `before`/`after` snapshots with HP, max HP, shield, max shield, overheal and max overheal, plus `blocked`, `clamped`, `reason` and cooldown state. `damageEvents` counts actual `A_TakeDamage` callbacks for the hit. A blocked command succeeds as a diagnostic operation but applies no hit; inspect its result rather than assuming the requested damage landed.

- **Cooldown:** the normal enemy-damage cooldown is respected. While the editor freezes gameplay it does not expire, so repeated commands can return `reason: damage-cooldown` with identical snapshots. Leave the editor briefly to advance gameplay before another hit. Disable spawns first in a disposable test run; existing enemies remain.
- **Shield:** all harness damage bypasses shield, in both nonlethal and lethal modes. Shield is left unchanged; results report `ignoreShield: true`. Ordinary enemy hits outside the harness keep their normal shield behavior. The 1 HP nonlethal floor applies even when shield is full.
- **Overheal:** damage still consumes overheal before HP. Native HP subtraction truncates floats, so the nonlethal cap conservatively uses `hp - 1 + floor(overheal)`. Fractional overheal may remain. The cap runs after `CheckStopDamage` item modifiers and only during the harness call; at the floor, a fully capped hit emits no damage callback. Nonlethal calls fail closed if the guard patch is absent.

For danger testing, first obtain a low-health state with a hit, advance gameplay past cooldown, then hit again below 25% HP if needed. Inspect `music-probe status` (`sourcePitch`, with `heldPitch` null) and `query_objects(type="MusicController", fields=["currentDangerPitch"])`. Editor pause filtering is not the low-health reaction; exit the editor to observe the natural pitch change. These are source-state checks, **not an audible confirmation**; listening remains a human check. Overheal, cooldown and the 1 HP floor can prevent a requested follow-up from being an actual HP hit.

## Player invulnerability

`invulnerable` gives the player 20 stacks of the game's own Mirror item (`EItem.Mirror`) and sets the item's `cooldown` and `minCooldown` to 0. Mirror stops a hit through `PlayerHealth.A_CheckStopDamage` and normally waits out a cooldown before it can stop the next one; with no cooldown it stops every hit. `invulnerable` also adds 2 stacks of Feathers (`EItem.Feathers`, extra jumps) so the player can reach tall structures. `vulnerable` sets Mirror and Feathers back to exactly the amounts the player held when `invulnerable` was sent, so a held Mirror stack survives the round trip and an item the player did not hold is removed. Each command logs `DevHarness: player invulnerable, Mirror amount=20, Feathers amount=2.` or the `vulnerable` equivalent. Issuing the same command twice logs `already invulnerable` or `already vulnerable` and changes nothing. A new run builds a new inventory, so send `invulnerable` again after each `load`.

Verified in the running game on a mod-loaded Forest level: an idle player kept full HP and shield for 47 seconds of game time while kills went from 6 to 51. Setting only the stacks, with the default cooldown, was not enough: HP fell to 36/72 within 40 seconds.

Caveats:

- It is not a god mode. Damage that does not go through `A_CheckStopDamage` is still applied, and stronger enemies such as mini bosses can still kill the player. Which damage sources bypass Mirror was not enumerated.
- Mirror reflects damage back at the attacker, so enemies take damage from hitting the player.
- A surviving, idle player can still reach the level-up dialog, which pauses play and puts a window in the frame. `freeze` after the settle wait does not close it, so keep the settle time short or take the screenshot before the first level-up.
- The kill floor still wins. `KillFloorWatcher` ends a fall through `PlayerHealth.KillPlayer()`, which does not pass through the damage check. Verified with a level that removes every tile but one: the invulnerable player logged `KillFloor: player fell to y=-49.8, killing` and the run ended on the death screen. For the same reason it also bypasses the hit-point floor that `perf health` sets; a long profiling window has to move the player back rather than only make them tough (see "Frame-time profiling").

`perf health` is the same grant plus a `PlayerHealth.hp`/`maxHp` floor in one command, for measurement windows that must outlast a swarm (see "Frame-time profiling").

## Fall damage

`run.py fall-damage` (MCP `fall_damage()`) reads what decides fall damage in the live run in one round trip: `character`/`characterId`, `hp`, `maxHp`, `shield` and `overheal`, the thresholds and the landing stamp off `PlayerHealth` (dump.cs:364467 — `minFallDamageSpeed` `0x38`, `maxFallDamageSpeed` `0x3C`, `fallDamageTakenAtTime` `0x40`), `stats` for `FallDamageReduction`, `MaxHealth` and `DamageReductionMultiplier` through `PlayerStatsNew.GetStat` (`PlayerStatsNew` at dump.cs:365731), the active character's `CharacterData.statModifiers`, and the same rows for both Warehouse-playable characters straight from `DataManager.GetCharacterData` so one read compares them. It adds `grounded`, `fallSpeed` and the rigidbody's `velocityY` from `PlayerMovement`, and a `fallDamageOverride` block saying what `FallDamagePatch` does to the next landing: `levelNames`, `referenceId`, `activeCharacterId`, `active`, `referenceValue`, `swaps`, and the `lastPlayerValue` / `lastReferenceValue` / `lastReadBack` of the most recent swap.

`fallDamageTakenAtTime` is the tell that the landing path ran. It is stamped even when the reduction takes the damage to nothing, so a zero-damage landing is distinguishable from one that never reached `PlayerHealth.OnPlayerLanded` (dump.cs:364539, `private void OnPlayerLanded(float speed)` at RVA `0x429640`). Each harness command costs about half a second of round trip, so a single before-and-after pair can straddle the impact; sample while `fallSpeed` is climbing until `grounded` flips, and read the peak from those rows.

**Fall damage is a per-character stat, not a per-character threshold.** Both Warehouse characters share the one `PlayerHealth`, so the thresholds measured at runtime are identical (30 and 140 m/s); what differs is `EStat.FallDamageReduction` (`EStat` at dump.cs:360037, `FallDamageReduction = 27` at 360068), which Tony McZoom's `statModifiers` carry as `{stat: 27, modifyType: 2 (Flat), modification: 1}` and Calcium's do not. A character's total for a stat is `PlayerStatsNew.GetBaseValue(EStat)` (static, RVA `0x445920`) with that character's rows applied onto it: `Addition` (0) and `Flat` (2) sum, `Multiplication` (1) scales the sum (`EStatModifyType` at dump.cs:365703, `StatModifier` at 365967). `FallDamagePolicy.StatTotal` is that arithmetic, tested against the two characters' own rows.

**A landing on a slope is exempt, so a repro needs flat ground.** `PlayerMovement.CanTakeFallDamage(Vector3 normal)` (dump.cs:328579, RVA `0x33BBE0`) weighs the surface normal against `minBreakFallAngle`/`maxBreakFallAngle` (`0x88`/`0x8C`): a 92-unit drop onto the Warehouse's starting slope arrived at ~60 m/s and dealt exactly nothing, `fallDamageTakenAtTime` still 0. The half pipes are exempt for the same reason, which is also why a big air that lands back on a transition costs nothing. The Warehouse bundle is open-topped, so the flat floor inside it at `(100, 0.5, 0)` (cell 10,7) is the surface to measure on, and nothing above it caps the height.

Measured there as Calcium, unpatched, spawns off and vulnerable:

| impact `fallSpeed` | damage | hp after |
| --- | --- | --- |
| ~29 m/s | none, below the 30 threshold | 100/100 |
| ~59 m/s | 21 | 79/100 |
| ~154 m/s | 72 | 9/81 |
| ~234 m/s | 99 | 1/100 |

Fall damage is floored at 1 HP, so a fall cannot kill: the largest drop the map allows, a teleport to `y=1000`, left Calcium alive at 1/100 with the damage vignette and blood decals on screen. A level's real lethality for a character with no reduction is what reaches them at 1 HP, not the fall itself.

With `fallDamageCharacter` naming a reference character (see [level-format.md](level-format.md)), `FallDamagePatch` (`fall_damage_patch.cs`) is a Harmony prefix and postfix on that one method. The prefix asks `FallDamagePolicy.Applies(customLevelActive, referenceId, activeCharacterId)` — false unless a mod-loaded level names a reference character and the player is not that character — then writes the reference character's total into `PlayerStatsNew.stats` and `rawStats` for `EStat.FallDamageReduction` and hands the old values to the postfix through `__state`, which puts them back. `GetStat` reads the dictionary the patch writes, which is what `lastReadBack` shows: on the Warehouse as Calcium it reports 1, Tony's own value, while the same command outside a landing reports Calcium's 0. Only `PlayerHealth`'s `OnPlayerLanded` is patched, so `PlayerCamera.OnPlayerLanded` (dump.cs:330001) and `ControllerShaker.OnPlayerLanded` (333097) keep reacting and a landing still shakes the frame. The swap lasts one call, and `LogOnce` prints the first three of them (`FallDamagePatch: landing at hp 100 scored with FallDamageReduction 0 -> 1 (GetStat 1)`) and stays quiet after, leaving `swaps` and the `last*` values as the running record.

Verified on the Warehouse with the field set to `tonymczoom` and Calcium playing: the 1000-unit drop that unpatched took him to 1/100 left him at 100/100 at a ~246 m/s impact, a 60-unit drop (~45 m/s) likewise, and a drop from `y=40` — above the 35.85 start platform, the tallest geometry the level authors — likewise, each with `fallDamageTakenAtTime` stamped, so the game's own landing path ran and the borrowed stat is what emptied it. `swaps` rose by one per landing and the player's own stat read 0 between landings, which is the restore working. The reference character is never patched while playing his own level: on the same 1000-unit drop (~231 m/s) he stays 70/70 with shield 10/10, `active` false and `swaps` 0, because `Applies` refuses when the reference character is the player. A level that names no reference character leaves `levelNames` and `referenceId` null, `active` false and `swaps` 0, and keeps the curve above: as Calcium on `levels/example-forest.mblevel.json`, a 45.2 m/s landing took him to 82/100 and a 44.8 m/s landing to 67/100, both with `fallDamageTakenAtTime` stamped. The pairs are what make the case — a 44.0 m/s landing on the patched Warehouse costs Calcium nothing where the same speed on the unpatched forest costs 17, and the forest run's own readout is identical to the patched one except that every override field is empty. Landings on the forest's slopes (two candidates at `(-10, -10)` and `(-10, 10)`, both ~76 m/s) took nothing and stamped nothing, which is the slope exemption above working in a level the patch never touches.

## Death screen restart

The death screen's summary window (shown after Confirm on "you ded") has a retry button, `DeathScreen.restartBtn` (the object named `B_Retry`, in `StatsWindows/W_Stats/.../Buttons`). The game ships it inactive and nothing in `Awake`, `StartDeathScreen`, `DoTransition` or `Update` turns it on, so a normal run's death screen shows Confirm alone. A second object named `B_Restart` exists in the scene and is a different button; do not read it as the death screen's.

`DeathRestartPatch` postfixes `DeathScreen.StartDeathScreen` and calls `restartBtn.SetActive(true)` when `CustomLevelState.IsActive`, so only mod-loaded runs get the button. Pressing it runs `DeathScreen.Restart`, which calls `MapController.RestartRun`. `RestartRun` keeps the stored `RunConfig` and does not call `MapController.StartNewMap`, so `LevelLoaderPatch.StartOnce` and the `CustomLevelState` start hook do not run again. Three things carry the custom level across the restart:

- `CustomLevelState.IsActive` keeps its value, so `SteamWriteGuard` keeps suppressing scores, achievements and stats.
- The forced seed (`SeedForcePatch` level-seed mode), the grass flag, the player start, the slope limit, the music and the title live in statics that nothing clears between generations.
- `LiveEditPatch` clears its pending edits once a generation has applied them, so a `RestartRun` prefix in `DeathRestartPatch` calls `LiveEditPatch.RearmLevelEdits()`, which queues the loaded level's edits again. Without it the level regenerates without its edits and the kill floor stays disarmed.

Edits made in the editor during the run are not kept; a restart reloads the edits the level file had when it was loaded.

Reach the screen with the `kill` command (`run.py kill` or the MCP `kill` tool), which calls `PlayerHealth.KillPlayer` and so ignores `invulnerable`, then click Confirm in the game. The harness injects input for the editor only, so Confirm and the retry button need a real click. To drive the restart itself without any OS-level input, `run.py restart-run` (MCP `restart_run()`) calls `MapController.RestartRun` directly, which is what `DeathScreen.Restart` calls; it skips Confirm, so the death screen and its summary window are what a click-driven check still has to do by hand. The log shows `DeathRestart: retry button shown for the custom run`, then after the click or the command `DeathRestart: restarting the custom run, level edits queued again` and `DevHarness: restart-run requested.`.

The `RestartRun` prefix is also where the startup cover is armed, because `RestartRun` never reaches `StartNewMap` — see "Custom-level startup cover".

Not checked: `PauseUi.Restart` and the hold-to-reset `ResetRunUi` may also reach `RestartRun`, and with the prefix in place they would re-arm the edits the same way. What natively enables `B_Retry` on some maps (a report that Desert and Graveyard show it more often) was not found; it is not driven by any code reached from the death screen.

## Custom-level startup cover

A custom level is not playable when the run starts. The game generates its own baseline map, spawns the player inside it, and only then does the mod tear that baseline down and apply the level's edits, which for the Warehouse is 1241 edits including every rail and pack mesh. Measured from the stock menu (Confirm to sound), the order is fixed:

```text
t=0.000 MapController.StartNewMap, then TransitionUI.A_transitionStart, A_MapTransitionStart, MapController.A_NewRunStarted
t=1.225 MapGenerationController.A_PreGeneration           the game's own baseline map
t=1.262 MyPlayer.Spawn (120, 0, 0), A_PrePlayerSpawn, MyPlayer.StartPlayer (Calcium)
t=3.166 MapGenerationController.A_GenerationComplete      then the mod indexes, clears and edits
t=5.2   level content in the world, player placed
```

Two consequences drive the design. The stock transition's fade is finished about a second in, long before the content is ready, so it cannot be the thing that hides the build-up; and the player is spawned once, inside generation, at the baseline map's own spawn point, well before there is anything to stand on.

`StartupGate` (`startup_gate.cs`) decides what happens and when, in plain C# with no Unity or game types, so the rules are unit-tested in `tests/MegabonkLevels.Tests/startup_gate_tests.cs`. It moves through `Idle`, `Covering`, `Placing` and `Open`, and only ever reacts to events: a run starting (cover only for a custom run), the game spawning the player, the content being ready, the spawn portal opening and closing, a placement landing, a harness teleport, a cancel or failure, and the clock for the timeout. It never looks at where the player is. `StartupCover` (`startup_cover.cs`) applies what the gate decided: it shows and hides the cover, pins the body, and calls `MyPlayer.TeleportPlayerImmediate` once per placement.

The three rules that matter:

- **One placement.** The authored start is applied once, when generation and the level's edits are in the world and the stock spawn portal has finished. Nothing re-applies it because the player drifted. An earlier version watched the XZ distance from the authored start for 5 seconds and teleported whenever it passed 1 metre, which on the Warehouse's 26 degree half-pipe was never satisfied: the player fell about 7 metres, was yanked back, and fell again about every 0.84 seconds, re-arming the pipe launch each time, until the window expired.
- **A game-driven spawn is corrected once.** `MyPlayer.Spawn`, `MyPlayer.StartPlayer` and `MyPlayer.TeleportPlayerNextStage` postfixes tell the gate the game moved the player, and the next Tick places it at the authored start once. The menu flow fires all three within about 4 milliseconds, so triggers inside 0.25 seconds count as one. This assumes a level file describes one stage (`stageIndex` and one `playerStart`): a portal's next-stage teleport also resolves to that start. Multi-stage levels are not supported by this placement policy; they will need stage-specific starts and transition handling before this hook can distinguish their destinations.
- **The player is held, not chased.** Between the game's spawn and the placement the body is pinned where the game put it (`Rigidbody.position` written back, velocity zeroed each Tick), which keeps it from falling through a map that is being torn down underneath it. The hold ends at the placement, or at the timeout, and movement, falling and sliding are the game's from then on.

`SpawnPlayerPortal.MovePlayer` is a separate late writer: its native code moves the player's Transform along cached baseline spawn positions, without calling any of the three spawn hooks. Placing while that animation is pending does not stick. On macOS Wine, a trace showed the same body at the authored start for about 1.8 seconds before the portal moved it back to `(120, 2, -3)`, underneath Warehouse. Direct body/Transform assignments do not solve a later animation write. Instead, custom starts wait for `SpawnPlayerPortal.A_PortalClosed` as well as content readiness, in either order. Native code confirms that the event follows the portal's movement phase and also fires when the animation is skipped. The single placement runs on the next Tick, after the event's remaining game callbacks have returned. Duplicate completion events do not request another placement. No extra physics write, fixed delay, distance enforcement or additional Harmony hook is needed.

The cover is a canvas the mod owns (`EditorUi.NewCanvas`, `Image`, `TextMeshProUGUI`, sorting order 30000) showing black with the level's title. It is built on first use and hidden otherwise, so it is absent from the main menu. It arms in the `MapController.StartNewMap` prefix next to `CustomLevelState.OnRunStarting`, so a vanilla launch never sees one, and it is released by the placement, by `LevelLoaderPatch`'s `StartNewMap` exception path, by a cancelled load waiting on the character screen, and by the inactivity timeout, whichever comes first. The timeout releases the cover and the hold together and logs a warning, so a level that never finishes building degrades to the run being visible rather than to a screen that stays black; a placement still happens if the content or the player arrive afterwards.

`MEGABONK_STARTUP_TIMEOUT_SECONDS` sets the real-time no-progress interval (default 8 seconds). Set it in the game's environment, or in `.env` when launching through `task`, and relaunch for changes to take effect. Values must be positive, finite seconds with a decimal point independent of locale; missing, malformed, zero, negative, NaN and infinite values use the default. `A_PreGeneration`, changing generated tile/flat-tile/fill-tile counts, `A_GenerationComplete`, successful edit actions, content readiness and the awaited portal completion renew the deadline. Ticks, `isGenerating` staying true, and unsuccessful placement retries do not: slow-but-advancing generation can stay covered beyond 8 seconds, but a stalled stage still releases. Terrain generation has no tile-count heartbeat, so increase the interval for terrain maps whose generation goes longer between milestones. Progress after release never brings the cover back. If the portal never finishes, the cover and hold still time out, but an owed placement waits until the portal stops owning the position. A blocked game main thread cannot draw or process a timeout until it resumes; initial Il2Cpp assembly generation happens before this run-start cover exists.

What to read in `MelonLoader/Latest.log` for one startup:

```text
StartupCover: player placed at the level start (109.00, 36.08, -116.00)
```

One such line per placement, `LiveEdit: indexed ...` and the `LiveEdit: spawned ...` lines before it, and nothing that moves the player after it. Repeated placements, or a `StartupCover: startup cover released after the timeout` warning, both point at a specific cause: the former means the game spawned the player more than once, the latter that generation or the edits did not finish in time.

To see the cover itself, send the harness `screenshot` a couple of times during the window, a second or two apart. Do not burst it: each capture does a synchronous `Texture2D.ReadPixels` of the whole backbuffer, a `GetPixels32` copy and a PNG encode on the game's main thread, and one every half second for fifteen seconds reads as several seconds of heavy stutter. A run measured that way is not a run worth measuring frame times on; judge smoothness only from a run that sent no harness commands at all.

The gate's decisions are recorded as commands (`ShowCover`, `HideCover`, `HoldPlayer`, `ReleaseHold`, `PlacePlayer`, `Log`), which the tests assert on. The adapter drains this decision log each Tick to update the UI and emit messages. `PlacePlayer` and `ReleaseHold` are explicitly acknowledged log entries, not executable actions: placement (including retries) and hold release are driven by polling `ShouldAttemptPlace` and `ShouldHoldPlayer`. This avoids executing a placement twice or applying stale release side effects from an earlier run's queued decisions.

### A restart is a second startup

The death screen's Retry runs `MapController.RestartRun`, which never calls `MapController.StartNewMap`, so the `StartNewMap` prefix that arms the cover does not run either. Without arming there is no cover, no hold and no owed placement, and the baseline map's `SpawnPlayerPortal` becomes the last writer: it lerps the body from its cached baseline `playerStart` (`(120.00, 1.93, -3.00)`, one-second move timer, `movePlayer=True`) onto the baseline `CombinedCollisionMesh` whose surface is at `y=-20`, so the player ends the restart at body `y=-18.08` about 121 units from the authored start while the level's own edits are in the world correctly. `DeathRestartPatch`'s `RestartRun` prefix therefore calls `StartupCover.OnRunStarting(true)` next to re-arming the level edits. A restarted run reads the same as a first one:

```text
DeathRestart: restarting the custom run, level edits queued again
StartupCover: held where the game put the player
LiveEdit: applied 1241 edit(s)
KillFloor: armed at y=-35 (authored, catch floor y=-80)
StartupCover: player placed at the level start (109.00, 36.08, -116.00)
```

The `RestartRun` prefix is the only arming point on that path, and `CustomLevelState.IsActive` stays true across the restart, so the arming needs no level lookup. A harness `load` is not a substitute for testing it: `load` goes through `LevelLoaderPatch.LoadAndStart` and reaches `StartNewMap`, so a load-restart has always armed correctly and never showed this. `run.py restart-run` (MCP `restart_run()`) calls `MapController.RestartRun` directly, which is what makes the path reachable without OS-level input on the Rewired death menu.

Two rules keep the portal from undoing a placement, on the restart path and on any other:

- **The last portal wins, so the cover re-takes ownership after it.** `SpawnPlayerPortal.A_PortalOpen` is subscribed as well as `A_PortalClosed`. A portal that opens after the authored start landed re-owns the player: the cover comes back, the body is pinned to it, and `A_PortalClosed` owes exactly one more placement. A portal that opens before the first placement changes nothing about holding — the game's own spawn still decides that. `A_PortalOpen` fires on both the first boot and a stock restart, before the placement lands, so this is not a hypothetical hook. A portal that opens and never reports back gives up its wait when the cover timeout passes, so a later game spawn is still corrected once.
- **A harness teleport is the player's last word.** The harness `teleport` command calls `StartupCover.OnHarnessTeleported()`, which drops the adapter's cached hold point and tells the gate. The owed placement is cancelled, the cover and hold are released, and if a portal animation is still pending the player stays pinned on the harness point until it finishes rather than being dragged back to the authored start. `StartupCover: harness teleport kept` is the record of that, and a placement line after a `DevHarness: teleport` line is the bug. The next `MyPlayer.Spawn` starts a normal covered startup again, so suppressing the cover for one teleport does not disable it for the run.

The cached hold point matters on its own: the hold follows a point the adapter remembers, so an un-cleared point from before a teleport pulls the player back to it on the next Tick. That is what turned a mid-restart teleport into a fall through a map that was still rebuilding.

Both paths are verified in the running game by killing the player (`run.py kill`), restarting (`run.py restart-run`), and sampling `run.py state` for ten-odd seconds: the body comes to rest on the Warehouse's start platform (`(109, 29.75, -111.18)`, floor ray hit `y=29.19`), one placement line per restart, no repeat `KillFloor: armed`, and nothing from the cover before the first `load-level` on a stock boot.

## Enemy spawns

`spawns` with `enabled:false` (`run.py spawns off`, MCP `spawns(on=false)`) sets `EnemyManager.enabledWaves` to false, which stops the wave spawner; `enabled:true` sets it back. `state` reports `spawnsOff`, true only while the current `EnemyManager` is the one the harness switched off. The switch does not outlive a scene: a level load or new run builds a new `EnemyManager` with the default `enabledWaves`, so spawns are on again after a `load`; send `spawns off` again after each. `relaunch` sends `spawns off` itself before entering editor mode only when `MEGABONK_RELAUNCH_SPAWNS` is false.

Enemies already alive are not cleared. Clearing them would mean calling `EnemyManager.RemoveEnemy` outside the game's own death path, which skips drops, XP and pool bookkeeping. They keep chasing the player until they die, fall to the kill floor, or the run is frozen. Run `spawns off` straight after the load to keep the count low.

Verified on the example forest level with the kill-floor heartbeat: with spawns on, `enemies` stayed between 2 and 5. After `spawns off` the existing enemies died off within about 25 seconds and `enemies` stayed 0 for the following 67 seconds. `spawns on` brought 4 enemies back within 2 seconds.

Limits:

- With spawns off the HUD stage clock stops and no timeline event fires (mini bosses from `SummonerController.EventMiniboss`, swarms). The clock does not lose that time: after 63 seconds off, the HUD went from 7:30 to 6:20 within about 14 seconds of `spawns on`, and a `MinibossGolem` due inside the skipped window spawned 0.1 seconds after the switch. Events that fell inside the pause fire together on re-enable, so spawns off defers timed events and does not cancel them. Inferred from one run; the timer code was not read.
- The HUD stage clock counts down from 10:00. The first miniboss (`MinibossPig`) spawned at 6:59 remaining, about 3:01 elapsed, in two separate runs, read off the HUD to the second; the exact `TimelineEvent.timeMinutes` is unread. Turning spawns off before about 3:00 elapsed (7:00 remaining) delays the miniboss to the next `spawns on`, which does not skip it.
- Spawns that do not come from the stage timeline, such as shrine or coffin fights that call `EnemyManager.SpawnBoss` or `SpawnEnemy` directly, may ignore `enabledWaves`; unconfirmed.
- The level-load reset was confirmed through `relaunch`, which starts a fresh process; a `load` into a running game was not tried, because the harness advises against it.

## Boss spawn redirect

The Warehouse's boss portal is a game `InteractableBossSpawner` stood inside the hanging glass box, and the game always summons its boss at the spawner's own position: the boss materialises in or on the box, climbs its walls, and "Defeat the Boss" cannot complete. `BossSpawnRedirectPatch` (`boss_spawn_redirect_patch.cs`) patches `InteractableBossSpawner.Interact` with a prefix that arms the redirect, and postfixes on `EnemyManager.SpawnBoss` and the positional `EnemyManager.SpawnEnemy(EnemyData, Vector3, int, bool, EEnemyFlag, bool, float)`; only spawns carrying the game's Boss flag (`Enemy.IsBoss()`) are moved, and only while a mod-loaded level runs. The decision logic is Unity-free in `BossSpawnRedirect` (`boss_spawn_redirect.cs`).

The Boss Curse shrine (`InteractableShrineCursed`) increments `GameManager.bossCurses`, and the same `Interact()` then summons `1 + bossCurses` bosses through the same path, so the arming expects that many moves. It closes when the count is met or the `ArmWindowFrames` (2) window passes, and logs the shortfall once when it expires early. `SpawnBoss` calls the positional `SpawnEnemy` internally, so both postfixes see one spawn; a pointer set moves each enemy at most once. The arming resets on every `Interact` and on `Disarm` (level edits applied).

Each boss is teleported to a walkable spot in the interior chosen from a random ring around the spawner's XZ at 35-68 units (`MinDistanceFromSpawner`, `MaxDistanceFromSpawner`) — 35 clears the box footprint (half-diagonal ~16 units) with room to spare, so a boss can neither land beside the shrine nor on the box; the ceiling keeps copies inside the arena. The ring is seeded from the tick count at arming plus the move count (`SeedPerCopy`), so curse copies never iterate the same candidate sequence. Every candidate is tested — a down-ray hit against every collider with `normal.y` > 0.8 (the highest hit wins, so a rail or light above the floor does not win), its surface above `killFloorY + 5`, at least 20 units (`MinSpacingBetweenCopies`) from every copy already placed, and `PlacementProbe.ClearPoint` clearance above it — and `BossSpawnRedirect.PickSpot` keeps the usable spot whose nearest placed copy is farthest (maximin), not the first that passes. The game's spawn lift (its `actual - requested` offset, ~11.9 units) is preserved onto the chosen floor point so the boss's feet, not its pivot, land on the surface. Every move logs from- and to-position; when no candidate is usable the boss is left where the game put it and the log says so.

Live findings behind the shape:

- Anchoring every copy to one authored `bossSpawnPosition` stacked curse copies (the game's own `BaseInteractable.GetOffset` stagger between the summons measured only 2.7/2.9 units in a live run), and bosses released at the half-pipe floor under the box climbed its walls toward the portal — hence the keep-out from the spawner rather than an authored point.
- A spacing floor of 8 let copies land 14.7 units apart and they still fought on the same spot, so `MinSpacingBetweenCopies` is 20 — but first-fit then landed the next pair 21.2 apart, just over the floor and still reading as stacked, because both copies iterated one shared-seed candidate list and the first survivor past the keep-out always wins. Hence the per-copy seed and maximin `PickSpot`: with 48 candidates the farthest-from-taken pick routinely lands copies dozens of units apart instead of hugging the floor.
- Dropping each boss straight down under its own spawn fails on this level: `LiveEditPatch.GroundCollider()` is the generated tile mesh, which knows nothing about the bundle-placed warehouse mesh (the redirect logged `no ground under the boss` for both spawns), and gravity alone left the bosses in the pipe at the box foot. Hence the all-collider raycast around a ring instead of a drop at the spawn point.

## Kill-floor heartbeat

The kill floor (see "Kill floor" in [runtime-map-structure.md](runtime-map-structure.md)) logs a line for every actor it kills. The heartbeat adds a second line every 5 seconds that says what the watcher can see, which is what to read when something that should have died did not:

```text
KillFloor: watch enemies=26 stageBosses=1 lowestEnemyY=-69.03 lowestBossY=-66.47 bosses=['Enemy1(Clone)' id=18 y=-66.2 lowest=-66.4 inEnemies=True]
```

`enemies` is the size of `EnemyManager.enemies` and `stageBosses` the size of the manager's stage boss list. `lowestEnemyY` and `lowestBossY` are the lowest point any enemy or boss reached since the previous heartbeat, and each boss entry gives its id, pivot `y`, current `lowest` point, and whether it is also in `enemies`. A boss is only identified by id, because it has the same `Enemy1(Clone)` name as every other enemy.

The lowest figure is the collider bottom where one was read and the pivot otherwise. The watcher reads an actor's collider only while its pivot is within `KillFloor.ColliderProbeMargin` (25 units) of the kill floor, because Unity builds bounds lazily and asking a freshly spawned actor for them rebuilds them; the heartbeat's running minimum therefore reports pivots for actors standing well above the floor. The kill decision itself always gets the collider when the actor is in that band, so nothing falls through unseen: by the time an actor reaches the floor its pivot is below it and is always probed. A heartbeat line is also where a mod-side hitch shows up first — `perf report`'s `maxMs` for the `KillFloor` tick is the figure to compare when one appears.

It is off by default, because it adds a line every 5 seconds. Turn it on with `run.py heartbeat on` and off with `run.py heartbeat off`; both log `KillFloor: heartbeat on` or `off` and apply at once, including to a level that is already running. To start with it on, set `MEGABONK_KILL_FLOOR_HEARTBEAT` to `1` or `true` in the environment of the game process, for example in the `.env` that the taskfile reads or in front of the launch command. The variable is read once when the mod loads, and a later command overrides it. Verified in the game that the variable reaches the process under CrossOver.

The kill line itself always carries the actor's id, world position and `lowest` point, with `(still present, attempt N)` appended when an actor stays in the game after a kill.

## Position readout

With the harness enabled, a mod-loaded level draws monospace (`RobotoMono`) yellow text anchored under the game's minimap, left-aligned within a box whose right edge sits under the minimap's right edge (the minimap itself is flush with the screen's own top-right corner, so anchoring under its left edge instead would run new lines straight off-screen). The player's own line is labelled `me:`:

```text
me:        pos(120, 2, 3) floor -72
enemy: 4   pos(125, 2, -10)
```

Every line shares the same columns (label, id, then `pos(x, y, z)`), but the column widths are computed each refresh from what is actually on screen that refresh (`PositionReadout.Render`), not a fixed guess: the label column is as wide as the longest label shown (at least `me:`), the id column at least 3 digits (wider only if an id needs more, so ids don't jitter the column within a normal run), and each of x/y/z is as wide as that coordinate's widest current value. A value wider than its column still prints in full, only pushing what comes after it on that line; lines share these widths so the `pos` column lines up between them. `pos` itself is the world position rounded to whole units. `floor` on the player's line is the kill-floor height, and `BELOW FLOOR` is appended when an actor's position is below it (the kill floor uses the lower of the position and the collider bottom, so an actor can be killed a moment before its line is flagged). Boss-tier lines also carry the enemy's type name, directly after the position or the `BELOW FLOOR` flag with a single space — it is not column-aligned across lines, since reserving width for it on every line left large dead space when only one boss-tier actor was shown. The player's line is refreshed ten times a second, the actor lines every 0.75 seconds: that sweep walks every live enemy, so at a few hundred of them a 4 Hz pass was a measurable share of a frame for text nobody reads that fast.

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

The selectors reuse fixed buffers, so a refresh allocates only the few strings it shows. With about 400 enemies a refresh took 0.6 to 1.4 ms and allocated 3 to 5 KB; nothing runs on every frame, and the sweep's cost is now the 0.75 s cadence rather than 0.25 s — at 240 enemies the whole `PositionLabel` tick measured 0.022 ms/frame at the old cadence and 0.012 ms/frame at the new one, with the per-refresh figure unchanged.

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

## Frame-time profiling

The harness carries a frame profiler, for the question "what costs what when the screen is full of enemies". Everything in it is gated on the harness being enabled — every timer, every patch, every verb — so a normal session makes no timing calls at all. Measured results and the follow-ups they opened are in [performance.md](performance.md).

| Verb | What it does | Result |
| --- | --- | --- |
| `start` | Clears the frame buffer and every tick and probe total, so the next report describes only what follows | `window` id, `cleared` |
| `report` | Summarises what has been sampled since `start`, leaving it running | `frames`, `pausedFrames`, `meanMs`, `p50Ms`, `p90Ms`, `p99Ms`, `maxMs`, `minMs`, `modMsPerFrame`, `enemiesMin`/`enemiesMax`, `playerHp`, `timeScale`, `paused`, `vSyncCount`, `targetFrameRate`, and a `ticks` and `probes` array of `{name, ms, calls, maxMs, enabled}` |
| `status` | The same view without ending the window, logged every 2 seconds as `Perf: state:` | as `report` |
| `reset` | Releases a held time scale, re-enables every tick and probe, and revokes the player grant `health` applied | the released values |
| `spawn --count N` | Places N enemies in rings around the player through the game's own spawn path, up to 300, stopping after 10 consecutive null spawns | `requested`, `spawned`, `enemies`, `poolMax` |
| `timescale [--value X]` | Holds `MyTime.timeScale` at 0.05–20 every frame, or releases it when no value is given | `timeScale`, `heldTimeScale` |
| `toggle --target NAME --enable\|--disable` | Switches one mod tick (`KillFloor`), one probe (`EnemyManager.Update`) or `all` | the target's new state |
| `vsync --disable` | Sets `QualitySettings.vSyncCount` to 0 and `targetFrameRate` to 0, which is what uncaps the frame rate enough to measure | `vSyncCount`, `targetFrameRate` |
| `health [--hp N]` | Keeps the player alive through a window: the invulnerability grant (20 Mirror stacks, cooldown zeroed, plus 2 Feathers) and `PlayerHealth.hp`/`maxHp` written to 1,000,000/100,000,000, or `--hp` | `playerHp`, `playerGrantRestored` |
| `census` | Counts loaded instances of `Enemy`, `EnemyHpBar`, `VisualizeTargeting` and `AnimatedMesh`: `scene` = on active game objects, `live` = also enabled and active in hierarchy, `any` = everything `Resources` sees, prefabs included. The way to tell a dead method from a ghost component | `census` array of `{name, scene, live, any}` |

`run.py perf report` and the MCP `perf` tool return the JSON; `perf health` is the invulnerability setup of the "Player invulnerability" section plus a hit-point floor, applied in one command so it can be sent before a spawn.

**Frames.** One sample per frame from `Time.unscaledDeltaTime` in the mod's `OnUpdate`, while `MyTime.paused` is false. While it is true the frame is counted and not sampled (`Perf: pause: on/off` is logged on each transition). Paused frames are UI frames: Unity keeps rendering a frozen run at a rate that says nothing about gameplay, and those frames are long, so a window that contains any is a different measurement than the one being asked for. `pausedFrames` is how the caller finds out.

**Ticks and probes.** Each mod tick is wrapped in `PerfMonitor.Timed`, and eight Harmony prefix/postfix pairs instrument the game's own enemy path: `EnemyManager.Update`, `EnemyManager.FixedUpdate`, `Enemy.MyFixedUpdate`, `EnemyMovementRb.MyFixedUpdate`, `EnemyDissolve.Update`, `AnimatedMesh.Update`, `MinimapUi.Update` and `AlwaysManager.Update`. `Enemy.MyUpdate`, `EnemyHpBar.Update` and `VisualizeTargeting.Update` were probed and dropped: never called, or never instantiated ([performance.md](performance.md#frame-time-against-enemy-count)). Both use `Stopwatch.GetTimestamp()`, never `Time.*`, because a tick can run inside a frame whose delta is the thing being measured. `calls` matters as much as `ms`: 240 enemies produce 83.9 `Enemy.MyFixedUpdate` calls per frame, 0.35 of a call per enemy per frame, which is the 50 Hz fixed update against the ~143 fps a 7.02 ms mean implies. `maxMs` is the one to read when the complaint is a hitch rather than a low average — an average of 0.013 ms/frame can hide a 112 ms single call.

Every `report` and `status` also carries a `probeAttach` array of `{name, patched}` from Harmony's patch info, so a zero-call probe is classified in one step: `patched: false` is an attach failure, `patched: true` with zero calls means the method was not invoked, and `perf census` then separates "never invoked" from "never instantiated" by counting live instances of the components the probes attach to.

`toggle all off` is the control that separates the three kinds of cost: mod work (the `ticks` array), stock work the probes can see (the `probes` array), and everything else, which is engine work — rendering, the physics broadphase and solver, GC. Probes measure the game, they are not part of playing it, and a report should be read as a diagnostic build's numbers.

### Taking a measurement

The sequence that produces a number worth comparing, and the reason each step is there:

1. Relaunch rather than reload. A rebuilt DLL loads once, at startup, and a `load` into a running game restarts the run while leaving whatever the previous run left behind.
2. Load with a fixed `--seed` (and `--tier`/`--map` if they matter), then `spawns off` so the wave spawner cannot move the population during a window.
3. `invulnerable`, `editor off`, `resume`. The editor freezes the run, which is the wrong thing to measure.
4. `perf vsync off`. At a locked 60 fps every window reads 16.7 ms and none of the differences are real.
5. Per window: gate on the run being live (`state`'s `levelLoaded`, `killFloorArmed`, and not `editor` or `frozen`; `perf status`' `paused` false), teleport the player to a fixed point, `perf health`, spawn the top-up to the target count, `perf start`, wait, `perf report`. Spawn and teleport stay outside the window.
6. Keep the report only if `pausedFrames` is 0, `vSyncCount` is 0, the frame count is plausible for the window length, and `enemiesMin..enemiesMax` brackets the target. Otherwise take it again.

Dismiss reward windows during the window, at about 1 Hz: kill-floor deaths award XP, XP opens the level-up screen, and the level-up screen pauses the run. A 160-enemy window collected 784 paused frames this way before it was thrown out.

`scripts/perf_sweep.py` drives all of it — a fresh launch, the load with retries until `KillFloor: armed`, the count sequence, and the two controls at the top count (every tick and probe off, then back on) — writing one JSON per window with the report plus the window's target, attempt count, rewards skipped, and a `_suspect` note when the population thinned below 80% of target:

```sh
uv run scripts/perf_sweep.py --out /tmp/perf                      # the default 0, 40, 80, 120, 160, 200, 240
uv run scripts/perf_sweep.py --count 0 --count 240 --seconds 30 --seed 20261102
uv run scripts/perf_sweep.py --no-relaunch --out /tmp/perf_probe  # measure the run already loaded
uv run scripts/perf_sweep.py --count 0 --count 240 --density strung  # see density A/B section below
uv run scripts/perf_sweep.py --count 240 --captures 2 --capture-dir /tmp/RenderDoc  # RenderDoc F12 frames per window
```

On a direct-Proton Linux host (no `task game:run` available), pass `--launch-cmd` to relaunch instead:

```sh
uv run scripts/perf_sweep.py --count 0 --count 240 --launch-cmd "sh /home/lance/.local/share/scripts/launch-megabonk.sh"
```

The command is split with `shlex` and run without a login shell, so a leading `~` is never expanded — give absolute paths. The launcher must return promptly: detach the game (`setsid ... &`) rather than exec it, and export `DISPLAY`/`XAUTHORITY` yourself — over SSH they are unset, and the Proton launcher inherits them; take `XAUTHORITY` from the running Xwayland's `-auth` argument.

**Density A/B** (`--density gathered|strung`). `gathered` (default) teleports the player to a fixed point so the swarm converges there. `strung` does the same spawn, then teleports the player `--strung-offset` world units along +X so the swarm is left behind — isolating contact-density cost at equal enemy counts. The A/B result and what it showed are in [performance.md](performance.md#attributing-the-unprobed-per-enemy-cost).

**RenderDoc captures** (`--captures N`). Requires the game to have been launched with `ENABLE_VULKAN_RENDERDOC_CAPTURE=1` (the Vulkan implicit layer registered in `~/.local/share/vulkan/implicit_layer.d`). The sweep triggers F12 through `run.py menu drive` N times per window (evenly spaced); new `.rdc` files in `--capture-dir` (default `/tmp/RenderDoc`) are paired with the window JSON and moved under `<out>/captures/`. F12 freezes rendering for the capture frame, so **capture runs perturb frame times** and should be separate from the timing sweep. See "RenderDoc on a direct-Proton Linux host" below.

**GC sampler.** Every `perf report` includes `gcPauseMsPerFrame` and `gcCollections`: time the mod's .NET CLR spent suspended for GC during the window, divided by frames. This measures the mod's own managed GC (which allocates nothing in steady state and reads 0.000 everywhere in practice). The game's il2cpp Boehm GC has no managed events and is invisible here — it appears only as frame-time outliers in `p99Ms`/`maxMs`.

### RenderDoc on a direct-Proton Linux host

The RenderDoc Vulkan implicit layer captures frames from the DXVK layer underneath Proton, making GPU-level frame analysis available without a development build.

**Install (user-level, no root).** Download the official tarball from renderdoc.org, extract to `~/.local/share/renderdoc`, and symlink the binaries:

```sh
curl -sL -o /tmp/renderdoc.tar.gz https://renderdoc.org/stable/1.47/renderdoc_1.47.tar.gz
tar xzf /tmp/renderdoc.tar.gz -C ~/.local/share
mv ~/.local/share/renderdoc_1.47 ~/.local/share/renderdoc
ln -sf ~/.local/share/renderdoc/bin/renderdoccmd ~/.local/bin/renderdoccmd
```

**Register the layer.** Copy the layer JSON and fix its `library_path` to point at the extracted `.so` (the tarball ships `/io/dist/lib/…` which only resolves inside the build container):

```sh
mkdir -p ~/.local/share/vulkan/implicit_layer.d
cp ~/.local/share/renderdoc/etc/vulkan/implicit_layer.d/renderdoc_capture.json \
   ~/.local/share/vulkan/implicit_layer.d/
python3 -c "
import json, pathlib
p = pathlib.Path.home()/'.local/share/vulkan/implicit_layer.d/renderdoc_capture.json'
d = json.loads(p.read_text())
d['layer']['library_path'] = str(pathlib.Path.home()/'.local/share/renderdoc/lib/librenderdoc.so')
p.write_text(json.dumps(d, indent=2))
"
```

**Add the capture env var to the launch.** On a direct-Proton systemd-run launch, add `--setenv=ENABLE_VULKAN_RENDERDOC_CAPTURE=1`. The layer is confirmed loaded when `librenderdoc.so` appears in the game's `/proc/<pid>/maps`.

**Trigger a capture.** F12 is RenderDoc's default capture hotkey. Via `run.py menu drive` (KEY_F12 is in the uinput whitelist): `uv run scripts/run.py menu drive '[["key","KEY_F12"]]'`. Captures land in `/tmp/RenderDoc/` as `wine64-preloader_<date>_frame<N>.rdc`.

**Headless replay, no Qt host.** `scripts/renderdoc_replay.py` opens a capture and reads per-event GPU durations, draw-call counts and the per-enemy submission shapes straight from a plain interpreter — the Qt GUI is not needed, and `renderdoccmd convert -f capture.rdc -o frame.xml` is a dead end because that format carries no GPU timestamps. Three things about v1.47 cost time to find and are the reason an earlier round concluded this was impossible; two more say what the resulting numbers are worth:

- **The pymodule is ABI-pinned to the python it was built against.** Importing `renderdoc.so` under the wrong minor version dies in a way that looks exactly like the "needs the Qt host" failure. `ldd renderdoc.so` names the `libpython3.x` it wants; on the player laptop the module in `~/git/renderdoc-build/renderdoc/build3/lib` is built against `python3.14` while the system `python3` is 3.13, so the tool is run as `python3.14`. Point it at a different build with `MEGABONK_RENDERDOC_LIB`.
- **`InitialiseReplay`/`ShutdownReplay` bracket every call.** No API call is valid before the first or after the second, and they are what the Qt host normally calls for you — that, not a missing GUI, is why the module is documented as unsuitable for standalone use. Omitting `ShutdownReplay()` dumps core during interpreter teardown, which also reads as an import-time crash.
- **Only `renderdoc` exists standalone.** The `qrenderdoc` module (UI windows and docks) is not available outside the GUI, so anything the tool needs must come from the replay controller: `GetRootActions`, `EnumerateCounters`, `FetchCounters([GPUCounter.EventGPUDuration])`, `GetVulkanPipelineState`.

- **`EventGPUDuration` is a relative clock, not a frame clock.** Its sum for a frame the harness measured at 4.88 ms mean came back as 22.8 ms, and the worst captures reported 101 ms on frames carrying a third of the vertices of a 44 ms frame, so the milliseconds are replay artefacts (serialised submission, per-query flush, idle clocks) and only ratios within one session mean anything. The Intel ANV driver offers no whole-frame `GPUCounter.Duration` to cross-check against — `EnumerateCounters` starts at 1 — and this pymodule has no `REVENT`, so a begin/end range cannot be requested either. Use `shapeGpu` and `drawRecords` to ask what share of the frame's work a set of draws accounts for, and get milliseconds from the harness's own frame time.
- **Structured and replay modes agree on draw calls, not on instances.** Both count the same draws; the serialised log's `instanceCount` under-reads a long tail of draws whose instance count the replay controller's action model reports higher (1,635 against 3,209 instances on one capture). Quote draw calls and submitted vertices, which both modes agree on.

```sh
python3.14 scripts/renderdoc_replay.py --baseline "$G/count_0_0.rdc" --pipelines \
  --json /tmp/replay.json "$G"/count_0_0.rdc "$G"/count_240_0.rdc
```

`--baseline` turns the run into a per-enemy split (GPU µs on the replay clock, draw calls, vertices and instances per extra enemy) against an empty-level capture. Replay mode also lists the frame's largest colour targets, so a duration can be read against the resolution it was measured at. `--structured` parses only the capture's serialised API log — draw calls, instances and vertices submitted per shape — with no replay device, so it costs no GPU time and is safe to run while something else owns the box. Replaying is a GPU workload: the tool refuses to open a replay device while `Megabonk.exe` is running, which would skew both the game and the capture, and takes `--force` to override.

Captures are written under `/tmp` and do not survive a reboot; regenerate them with the sweep command above before replaying.

### What ruined a measurement before it was understood

- **A paused window looks like a slow window.** `state`'s `frozen` is the harness freeze, not `MyTime.paused`, so a run held by the death screen reports `frozen: false`; `perf status`'s `paused` and `pausedFrames` are the only reliable gate. `dismiss-offers` cannot close `DeathScreen`.
- **`perf health` alone does not keep the run alive.** A player knocked off the map is killed by the kill floor through `PlayerHealth.KillPlayer`, which bypasses both Mirror and `PlayerHealth.hp`, and the run ends mid-window on the death screen. Teleporting the player back before each window is what keeps a sweep going.
- **Enemy count is not the variable, the swarm's shape is.** Teleporting the player to a fixed point gathers the whole population around them; leaving the player where the run drifted leaves the same 240 enemies strung out across the map. Those two states measured 9.63 ms and 7.02 ms, because physics contacts scale with local density. Fix the position and the counts become comparable — and note that convergence grows through a session, so later windows in a sweep read high.
- **Total frame time is noisy; per-tick totals are not.** Repeating the same 240-enemy window in one session gave means of 6.5, 7.0, 7.8 and 9.6 ms, so anything smaller than about 1.5 ms in a total is not evidence. `ticks` totals and `maxMs` are steady enough to compare builds.
- **Do not screenshot a measured run.** Each capture is a synchronous whole-backbuffer readback on the game's main thread (see "Custom-level startup cover"); a window that took one is not a frame-time measurement.
- **The harness is inside the numbers.** It polls twice a second, so a 20-second window contains about 40 `DevHarnessPoll` ticks — 0.027 ms/frame of diagnostic cost at 240 enemies, in the `ticks` array where it can be subtracted.

Verified on the Windows build under Proton on the gamescope host, over populations of 0 to 240 enemies with the kill floor armed and `perf vsync off`; the resulting tables are in [performance.md](performance.md).

## Not covered

The harness does not press menu buttons or open the level-up dialog. Only `state`, `ui-tree`, `click-widget`, `save-level`, `list-levels`, `query-objects`, `teleport`, `item`, `dismiss-levelup`, `dismiss-offers`, `interact` and `perf` return data; the other commands report success or failure and nothing else, and `state` does not report health, inventory, enemies or the level-up dialog (the profiler's `perf status` reports live enemy counts and the player's hit points). Use `freeze` to stop an idle player dying during a screenshot, or `invulnerable` when enemies must keep moving.

## Character selection

A level can limit its characters with the `allowedCharacters` field (see [level-format.md](level-format.md)); Warehouse allows Calcium (`ECharacter.Calcium`, 1) and Tony McZoom (`ECharacter.TonyMcZoom`, 13). Both ids live in `character_override.cs`, which also holds the name parsing (`calcium`, `tony`, `tonymczoom`, case-insensitive) and the pure grid-order and dev-flag logic. `CharacterPolicy` (`character_policy.cs`) turns a level's names into allowed ids, decides whether a character is permitted and builds the refusal text. A level without the field has no restriction. All of it is unit tested.

With `MEGABONK_DEV` unset, `LevelLoaderPatch.LoadAndStart` (F6 and `load-level`) does not start a level that has `allowedCharacters`; a level without the field starts at once with the character already selected. It holds the level, restricts the game's own Character Selection screen and logs `LevelLoader: waiting for a character to be confirmed`. The player then goes through the stock screens (Play, map, character). When a character is confirmed, a first-priority prefix on `MapController.StartNewMap` replaces the stock `RunConfig` with the held level's (seed, edits, music, title and the custom-run marking are prepared at that moment) and the run starts as the confirmed character. The map and tier picked on the stock screens are discarded; the level file decides them. `run.py character-screen off` (MCP `character_screen(on=false)`) cancels a held load and restores the stock grid. `run.py character-screen on` only restricts the screen.

`CharacterScreenPatch` restricts the screen after `CharacterMenu.OnEnable`, and at once if the grid is already built. It moves Calcium and Tony McZoom to the first two sibling slots under `characterGridParent`, and for every other character clears `canUseCharacter`, tints the icon black and shows `unavailableOverlay`, which is how the game already shows a locked character. The `cantUseCharacterReason` string is set to the refusal text ("Pick Calcium or Tony McZoom for this level"), which the game shows as a popup when a greyed character is clicked. It then reorders the private `characterButtons` list to the new sibling order and calls `SetupButtonNavigation` again, because the game derives keyboard and controller navigation from that list, not from the transforms; without this the d-pad and arrow keys jump around the old layout. Controller focus is set explicitly to Calcium, because the game focuses its saved character before the reorder and the controller otherwise starts on a stale button. The stock order, flags, tint, overlay and sibling index of every button are snapshotted on first sight and restored when the restriction ends. The screen is built once per session, so nothing is rebuilt or created. A menu with fewer than two buttons is not built yet and is skipped.

The game saves the confirmed character as `Preferences.selectedCharacter` in `config.json` as soon as it is confirmed. `CharacterScreenPatch` records the saved value when the restriction starts and writes it back with `SaveManager.SaveConfig` when the restriction ends, so a custom run leaves the player's own choice unchanged. Backing out of either selection screen cancels a held load and restores the stock character grid and saved preference. Forward navigation from characters to maps preserves the hold: the native menu enables the map tab before disabling the character tab, and the character-disable hook checks that destination. A successful start consumes the hold before the map screen disables, so closing the menus cannot cancel the run's startup cover. Check the preference by confirming a character other than the saved one, quitting the game, and reading `Saves/LocalDir/config.json` (under the bottle's `AppData/LocalLow/Ved/Megabonk`); a mod-loaded run that exits abnormally before the run starts leaves the confirmed character saved.

With `MEGABONK_DEV=true` (environment or `.env`; `task` loads `.env`) the screen is skipped. A load starts at once with Tony McZoom, or with the character named by the `character` field of `load-level` (`run.py load --character calcium`, `run.py relaunch --character calcium`, MCP `load(character="calcium")`). An unknown name rejects the load and logs the allowed names. `relaunch` needs the flag, because without it the load waits for the screen and the kill floor never arms. The flag assigns the static `CharacterMenu.selectedCharacter` directly and never touches the saved preference. If the assignment throws, `CharacterOverride.TryApply` returns a warning that the loader logs, and the run starts with the character the menu last selected.

Calcium's skateboard comes with the character: a run started as Calcium shows the skateboarder without any mod code selecting a skin, hat or mesh, so it is part of the game's own spawn for `ECharacter.Calcium`. Which asset carries it (`CharacterData.prefab` or a skin) is not traced.

To confirm which character spawned, aim the camera at the player (`run.py camera`) and read a screenshot; the editor's own camera can override the aim right after a relaunch, so send it again.

## Map Selection entries

`MapSelectionPatch` (`map_selection_patch.cs`) lists every `.mblevel.json` in `UserData/Levels` that has a `title` on the game's Map Selection screen, after the native maps. `CustomMapEntries` (`custom_map_entries.cs`) picks and orders them by title; an untitled level is not listed. A postfix on `MapSelectionWindow.InitButtons` clones `mapEntryPrefab` once per level under `selectionGroup`, calls `MapEntry.Set` with the level's base `MapData`, then overwrites the name and description (`mapDescription`, or `description` when it is absent) and sets a flat purple placeholder thumbnail. The game wires explicit up and down navigation once when it builds the list, so the patch calls `selectionGroup.FindButtons()` and relinks the navigation of every entry; without that a controller or keyboard cannot reach the appended entries.

A postfix on `MapSelectionUi.OnMapSelected` records whether the selected button is a custom entry. A prefix on `MapSelectionUi.StartMap` handles Confirm. Confirm on a native map drops any level held earlier. Confirm on a custom entry checks `CharacterMenu.selectedCharacter` against the level's `allowedCharacters`: a character outside the list cancels the start, logs the refusal and shows it through `MenuNotice` (`menu_notice.cs`), a short overlay near the top of the screen for refusals on the game's own menus. An allowed character holds the level through `LevelLoaderPatch.HoldForNextStart`, and the `MapController.StartNewMap` call that `StartMap` makes next is swapped for the level's `RunConfig`. Unlike the harness hold, this does not restrict the character screen, because the character is picked before the map. `MEGABONK_DEV` has no effect on this path.

A custom level fixes its own tier, so its entry offers only the first tier button, like Graveyard; the level file still determines the actual run tier. A prefix on `MapSelectionUi.OnMapSelected` records the custom/native selection before the first stats refresh. Each `RefreshTiers` repair explicitly enables and unlocks the first button, hides and locks the others, and redirects navigation away from hidden tiers. Tier 1 links directly to Challenges and back. Navigation values are captured separately before mutation, because generated non-blittable interop values can be reference-backed.

The outer map-selection postfix selects and focuses the first tier after the game has restored the base map's remembered tier. Do not shorten/reindex the selection group during `RefreshTiers`: the native handler still uses that remembered index afterward. Selecting the first tier emits another native stats refresh, so navigation repair must also run on refresh, not just once afterward. Before the next map selection, restore captured navigation and let the native refresh set tier visibility and unlocks. A postfix on `MapStatsInfoUi.SetConfig` blanks only the runs, highscore and speedrun values for custom entries, since the base map's records do not describe the custom level. The name, specs, tier, icons and stat labels remain unchanged; selecting a native entry lets `SetConfig` restore its records. The hover methods of the selection buttons share their native code with unrelated methods and cannot be patched, so nothing reacts to hover.

To check it, run `task thps` to install the level and pack, then run `relaunch(no_level=true)` and click through Play, the character, Map Selection and Confirm by hand. The log shows `MapSelection: listed 'Warehouse'`, `MapSelection: selected thps.mblevel.json` and `LevelLoader: starting map=Forest`. A relaunch starts the game unfocused, so click its window before using the menu.

## Player installer

`task package:linux` builds the player-facing Linux download — the mod, the vendored Windows MelonLoader and .NET 6 archives, the installer, and any levels or packs you name — into `.tools/player-package/` plus a distributable zip, and `task package:check` re-verifies a built package against its manifest. Levels and packs are never bundled unless you pass `LEVELS=` and `PACKS=`, so a dev regression map cannot reach a player by accident. The package format, the manifest contract, and the Proton-specific behaviour are in [player-installer.md](player-installer.md).

## Python tests

The tooling scripts under `scripts/` are covered by pytest tests in `tests/` (the C# tests live in `tests/MegabonkLevels.Tests`). `task scripts:test` runs them, and `task test` runs them after the C# tests. `[tool.pytest.ini_options]` in `pyproject.toml` is the only pytest configuration: it sets `testpaths = tests`, puts `scripts/` on the import path with `pythonpath` so a test does `import game_paths` directly, and runs the suite in parallel across CPU cores through pytest-xdist (`addopts = -n auto`, ~24s serial becomes ~7s). Pass `-n 0` for a serial run, which keeps `--durations` and failures in file order; `-p no:xdist` does not work because `addopts` still passes `-n`. Async tests are marked `pytest.mark.anyio` and select the asyncio backend in `tests/conftest.py`.

`task check` ends with `task lint`, which runs `markdownlint -c .markdownlint.jsonc .` and needs a `markdownlint` binary on `PATH`; a machine without one runs every test and then fails the check with `executable file not found`, so read the output above the final error before assuming a test broke. Install `markdownlint-cli` (`brew install markdownlint-cli`), not `markdownlint-cli2`, which is a different command with no `-c` flag that ignores `.markdownlintignore`.

`pyproject.toml` declares runtime dependencies under `[project.dependencies]`
and test and lint tooling under `[dependency-groups] dev`; `uv.lock` records
their resolved versions. uv installs the `dev` group by default, so a test run
needs no flags:

```sh
uv run pytest
uv run pytest tests/test_build_thps_level.py -q
```

`--with` is not needed: the `dev` group brings pytest and its plugins, and the
project dependencies bring runtime packages such as `python-decouple`, `mcp` and
`pillow`. Reserve `--with` for a genuinely ad-hoc dependency the project does not
declare. `uv run` automatically checks the lockfile and syncs the project
environment; add `--locked` when the command must fail instead of updating an
out-of-date lockfile. Name the group explicitly with `--group dev`, or leave it
out with `--no-dev`.

`tests/conftest.py` has an autouse fixture that removes every `MEGABONK_*` environment variable and points `game_paths.ENV_FILE` at a nonexistent file for each test, so a developer's shell or `.env` (for example `MEGABONK_WINE_PREFIX`) cannot change a result. A test that needs a setting sets it with `monkeypatch.setenv` or passes `env_file_values` to the function under test. Async tests use `@pytest.mark.anyio`; the conftest pins `anyio_backend` to `asyncio`, so no trio dependency is needed.

Tests that read build products the repo does not carry skip rather than fail. The precise form is a module-level `needs_extract` skipif over `build_thps_level`'s `NODES_PATH` and `OBJ_PATH` (over `check_thps_piece_inventory`'s `OBJ_PATH` in the inventory test, and over `pieces.json` and the piece prefabs in `tests/test_thps_pack_pieces.py`); `task thps` provisions the extraction under `.tools/thps1/warehouse`. `tests/conftest.py` backs this with a net so a file that forgets its guard still skips: `GENERATED_ARTIFACTS` names each product as a `module.ATTRIBUTE` reference or a repo-relative path, and a `pytest_runtest_makereport` wrapper turns a `FileNotFoundError` whose `filename` resolves to an absent entry into a skip. Add a new product to that tuple rather than writing another guard. Skips with those reasons are therefore expected on a fresh checkout, and failures are not.

An autouse conftest fixture also replaces `os.kill` with a stub that raises, so a test that reaches a real `os.kill` fails with an instruction to `monkeypatch.setattr(os, "kill", ...)` instead of signalling a live process. Tests that assert on the kills they perform install their own recorder, which replaces the stub. `wait_for_wineserver_to_exit` treats `EPERM` as a server it cannot kill rather than a crash: it counts killed and refused pids separately, prints both, and reports failure.

`task scripts:test` is just `uv run pytest`. Resolution policy lives in
`[tool.uv]`: `exclude-newer = "2026-10-31T00:00:00Z"` caps candidate packages and
`prerelease = "allow"` matches what `uv.lock` records under `[options]`. Both
belong in `pyproject.toml` rather than a Taskfile flag or a shell export:
`uv.lock` records the same values but is a generated file, so a lock regenerated
without them silently drops them and resolves differently. The interpreter comes from
`requires-python`, which already pins `>=3.13,<3.14`, so no `--python` flag is
needed either. Project dependency updates belong in `pyproject.toml` and
`uv.lock`. PEP 723 scripts run with `uv run --script` use their own inline
dependencies rather than the `dev` group; keep their headers/pins current
separately.

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

## Grind gate

On a level with `grindRequiresSlide` (see [level-format.md](level-format.md)), a rail touch starts a grind only while the game's slide button is held. The game's own catch needs nothing from the player: `Rail` (dump.cs:332650, `private void FixedUpdate()` at RVA `0x49B960`) looks for a nearby `PlayerMovement` and calls `PlayerMovement.StartRail(Rail)` (`PlayerMovement` at dump.cs:328257, with `public void StartRail(Rail rail)`, `public void StopRail()` and `public bool IsGrinding()`), so riding over a coping rail or ollieing off one took the player into a grind at `railSpeed` along the rail's tangent. The Warehouse's copings are rails (see "Grind" in [thps-warehouse-layout.md](thps-warehouse-layout.md)), which is what made its lips impossible to skate.

`GrindGate` (`grind_gate.cs`) holds the decision as one function, `AllowsGrind(customLevelActive, levelOptsIn, slideHeld)`, and it is asked in the three places grinding can happen. `GrindGatePatch` (`grind_gate_patch.cs`) asks it as a Harmony prefix on both `PlayerMovement.CanStartGrind` (writes `false`) and `PlayerMovement.StartRail` (skips the call), which is the catch, and as a postfix on `PlayerMovement.RailMovement`, the game's per-frame grind step, which calls `StopRail` the moment the button comes up. `RailHandoffPatch`'s chain asks it before starting the next rail at a joint. Both prefixes are needed because the dump gives signatures only, with no way to tell whether the catch consults `CanStartGrind`; the log names the hook that blocked, and a grind that started logs the same line with `slide held`.

So the button is a hold, not a toggle. Held, a grind runs and chains through joints for as long as the button is down. Released, the player leaves the rail at once instead of riding on to the next junction, and the catch keeps refusing them until it goes down again. The release stop is the game's own `StopRail`, with no dismount hop and no rail cooldown, so pressing the button again immediately catches the same rail.

Because the button now carries the intent, the start on a gated level is also made generous. `GrindAssist` (`grind_assist.cs`) and `GrindAssistWatcher` (`grind_assist_watcher.cs`), ticked from the mod's `OnUpdate`, put a player who is holding the button and not on a rail onto the nearest rail whose collider comes within `GrindAssist.CatchRadius` (2 units) of their feet and is not on cooldown, logging `GrindAssist: caught the rail at (149.4, 5.4, 8.6) from 0.00 units at (150.0, 9.4, 10.2), progress 0.510.` The distance reads 0.00 whenever the feet point is already inside the rail's collider, which is thick: the game's own catch reaches about the same 2 units, so the slack that matters is time rather than distance, the watcher asking on every frame where the game decides on the frames it likes. `GrindAssist.WithinBand` refuses a bar more than `CatchRiseAboveFeet` (1 unit) above the feet, which is a rail the player is passing under rather than one to be pulled onto, and `RailHandoff.DirectionForFreshCatch` starts a catch landed within `NearEndFraction` (0.15) of either end running away from it, so it does not stop the moment it begins. A frozen run (`MyTime.paused`, which covers the editor) and a dead player are skipped, and none of it runs on a level without the key.

The button is read through Rewired in `grind_input.cs`, the mod's only Rewired touchpoint (`Il2CppRewired_Core.dll` from `MelonLoader/Il2CppAssemblies` is referenced by the mod project): `ReInput.players.GetPlayer(0).GetButton("Slide")`, `ReInput` at dump.cs:203551 with `ReInput.PlayerHelper.GetPlayer(int)` at dump.cs:203156 and `Player.GetButton(string)` at dump.cs:199754. A read that throws reports the button **held** and logs once, including the mapping's id for the action, so an unreachable Rewired or an unknown action name leaves the game's own behaviour rather than making grinding impossible.

The harness injects only editor input, never Rewired input (see "Key, mouse and type commands"), so `grind-slide` stands in for the keyboard: `held` `true` or `false` arms an override on `GrindInput` and the same command without `held` hands the read back to the real device. The result is `{"held":<bool|null>,"slideHeld":<bool>}`, `slideHeld` being what the gate sees afterwards. That makes both branches of the gate checkable from the harness; a grind with real speed in it still needs a hand on the keyboard.

An armed override outlives the test that set it: it lasts until the process exits or something sends `grind-slide auto`, so a harness run that ended with the button forced released leaves whoever is at the keyboard unable to grind at all, on a gated level, with no error anywhere. Hand the read back before handing the keyboard to a person.

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

The reward windows are `BaseEncounterWindow` subclasses — `LevelupScreen`, `EncounterUi` (the shady-guy/moai/balance offers, two live instances: `EncounterWindow` and `ItemPickWindow`), `ChestWindowUi` and `MicrowaveUi` — sharing `Open(EEncounter)`, `OnClose()` and `ChooseOffer(int)`. `EncounterWindows` (namespace `Assets.Scripts.UI.InGame.Levelup`) owns all five windows and exposes `encounterInProgress`, true while a reward window is up.

The two commands split by action, not by modal. `dismiss-levelup` only picks an upgrade and only while `LevelupScreen.isLevelingUp` is true, so it reports `dialogWasOpen:false` and changes nothing while a shrine offer window is up (that window shows offers to ignore, not upgrades to pick, and its buttons have no `IUpgradable`). `dismiss-offers` acts on whichever reward window is up, and its `skip` acts only on the level-up window. Neither command touches another modal: with two `EncounterUi` instances (`EncounterWindow`, `ItemPickWindow`) only the active one is considered.

The `dismiss-offers` command acts on whichever window is up. The windows are found with the `Resources.FindObjectsOfTypeAll` sweep `query-objects` uses; `FindObjectsOfType<BaseEncounterWindow>()` and C# type filters over a `MonoBehaviour` sweep both miss them under interop. A `LevelupScreen` counts as open only while `LevelupScreen.isLevelingUp` or `EncounterWindows.encounterInProgress` is true: after `CloseLevelupScreen()` the GameObject stays active, and a second close throws `NullReferenceException` in `EncounterWindows.RewardFinished()`. The other classes are read from `gameObject.activeInHierarchy`. With no window the command succeeds with `{"windowWasOpen":false,"window":null}` and logs the two flags plus each `EncounterUi`'s active state.

Actions, all on the game's own paths. With no `choice` and no `skip` it closes without selecting: `LevelupScreen.CloseLevelupScreen()` (same RVA as `Leave()`) for the level-up window, `OnClose()` for the others. `choice` N on the level-up window runs `upgradePicker.buttons[N].SelectUpgrade()` — `LevelupScreen.ChooseOffer` is a 16-byte empty override, so it leaves the window open — and N past `buttons.Length` is rejected first with the `dismiss-levelup`-style range error; the other windows take `ChooseOffer(N)`. `skip` calls `LevelupScreen.Skip()` and is refused elsewhere with `'<window>' is not the level-up window; skip only applies there`. The result is `{"windowWasOpen":true,"window":"<Class> (<GameObject name>)","action":"close|choose N|skip","closed":<bool>,"reason":<string|null>}`. `closed` for the level-up window is read after the action from the flag that action clears: `!LevelupScreen.isLevelingUp` for `skip` and `choice`, which clear it in the same call (`EncounterWindows` clears `encounterInProgress` later in the frame, so it would report an unaffordable-but-successful skip as still open), and `!EncounterWindows.encounterInProgress` for the plain close, where `isLevelingUp` is already false on a shrine offer window and would report `true` no matter what happened. Like `dismiss-levelup`, it re-applies `MyTime.Pause()` when the close unpauses during an editor session.

A `skip` the game refuses leaves the window up and reports why in `reason`: `no skips left` when the private static `hasSkips` is false, otherwise the game's own numbers, as in `the game refused the skip; skip price 50, skips used 3` (`GetSkipsUsed()` and `GetShopToolPrice()`). Skips cost an escalating amount of the shop currency, so an unaffordable skip looks the same as an exhausted one to the player. A refused skip leaves the window fully usable: `choice` and the default close both still work.

Shrine reward windows — "The shrine offers you a reward" with its Ignore Offers button, from `ChargeShrine` — are the level-up window itself: the same `LevelupScreen` instance, `encounterType` `Levelup`, utility buttons hidden. Their offer buttons carry no `IUpgradable`, so `SelectUpgrade()` throws in `PlayerInventory.AddUpgrade` and `ChooseOffer` does nothing; `choice` on such a window is refused before anything is invoked with `offer N on '<window>' has no upgrade to select; a shrine reward window is dismissed with the default close, not chosen`. Shrine offers are ignore-only through the harness; the default close is the dismissal path.

Confirmed in the running game with `levels/extra-shrines-charge.mblevel.json`: dismissing a Charge shrine offer window reported `windowWasOpen:true`, `window:"LevelupScreen (LevelupScreen)"`, `action:"close"`, `closed:true` and the run resumed; the same call again reported `windowWasOpen:false`. A natural level-up accepted `--choice 0` with `closed:true` and the Scythe appeared in the weapons bar; four `--skip` calls reported `closed:true`, the fifth reported `closed:false` with `reason:"the game refused the skip; skip price 50, skips used 3"` while the window stayed open and `state` stayed frozen, and `--choice 1` on that same window then reported `closed:true`. A plain close on a level-up window (no `choice`, no `skip`) reported `closed:true` and unfroze the run, and the same call again reported `windowWasOpen:false`.

Open questions about the level-up dialog:

- Whether `UpgradePicker.AutoSelectUpgrade()` alone leaves an open dialog behind; it was not called.
- Whether item offers (`isItem` true) and the banish and refresh modes behave the same through `SelectUpgrade`; only upgrade offers were tried.

Result fields for a harness dismiss command: `wasLevelingUp` and `isLevelingUp` (before and after), `chosen` (index), `name` (from `GetName()`), `rarity` (the `ERarity` name), `frozenBefore` and `frozenAfter` (`MyTime.paused`), and `playerLevel` (`MyPlayer.Instance.inventory.playerXp.level`). A call with no dialog open returns `ok:false` with an error rather than throwing an index error.

## Interactables

`interact` activates the nearest `BaseInteractable` through the game's own `CanInteract()`/`Interact()`, bypassing the hover gate in `DetectInteractables`. That gate (its private `interactableRange` and `currentInteractable`, set in `FixedUpdate` physics sweeps) is unreachable from the harness, because harness keys and clicks are injected into `EditorInput.Queue` and never enter Rewired gameplay UI; on macOS the workaround is real keyboard events through `osascript`, which must set the `wine` process frontmost and hold the key across frames (`key down "e"` / `key up "e"`) — a `key code 14` tap can land and unland inside one Rewired poll and is then lost. `interact` skips all of that: `type` filters candidates by substring of the class name or the GameObject name (`--type Magnet`), `maxDistance` bounds the distance from the player, and `force` calls `Interact()` even when `CanInteract()` returns false. Without a filter the nearest active candidate wins. The result carries `name`, `type`, `distance`, `prompt` (from `GetInteractString()`), `canInteract`, `result` (`Interact()`'s return value) and `candidates` (how many active instances matched the filters); with no candidate it fails with `no interactable matched (...)`.

Candidates come from the `Resources.FindObjectsOfTypeAll` sweep `query-objects` uses, one sweep per concrete `BaseInteractable` subclass — the base class is abstract, but its interop wrapper is not, and that wrapper sweep runs last as the fallback that sees every subclass (including any whose own wrapper failed to load); instances are de-duplicated by pointer, so `candidates` counts unique interactables and `type` reports the real class. Prefab assets and inactive copies are skipped via `activeInHierarchy` — note a shrine's alert-icon object drops out of that filter when the shrine is consumed, so a re-query after `interact` reports one fewer instance. Candidates include every interactable in the scene, not only shrines: chests, portals and pickups are `BaseInteractable` subclasses too, so without a filter the nearest one might be a chest.

Confirmed in the running game on an extra Magnet shrine that never surfaced its hover prompt at any stance or distance: `interact --type Magnet` returned `interacted:true` with `prompt:"Shrine of Succ"` and `result:true`, and the shrine showed its own consumed state afterwards — label, outline and alert "!" icon cleared, and the alert-icon object inactive (one fewer instance in a re-query).

Two related gotchas. A `load` into a running game re-enters editor mode and resets invulnerability and enemy spawns, so re-send `editor off`, `spawns off` and `invulnerable` after every load, or keystrokes meant for gameplay land in the editor instead. And `ShrineLogs` keeps its static backlog for the whole game process, so the PAUSED screen's Shrine Logs panel is cumulative across harness `load`s, not per run — trust a row that was not there before, not the panel's contents.

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

While editor mode is active a palette on the left edge shows the placeable prefabs of every native map loaded in the game (`MapData` assets found through `Resources.FindObjectsOfTypeAll`, so Dungeon and Hell appear when their assets are loaded) plus installed pack assets, as a paged grid of icon slots, in a grayscale scheme. The level being edited stays the reference: the title names that map and, when more than one map is listed, how many maps are in the catalog (`Forest (5 maps) palette`). A column of category tabs sits on the far left, the panel title (map and current selection) and the search field are above the grid, and a footer under it shows `<`, `n/m` and `>`, where `n/m` is the current page over the page count. Entering editor mode releases the cursor lock and shows the cursor; leaving restores the lock and visibility the game had. Because the cursor is free, look only applies while the right mouse button is held. Pressing it with the pointer on the palette does not start a look, but a sweep that starts off the palette keeps turning when the pointer crosses it.

The entries come from the game's own prefab catalog, walked per map by `CatalogPrefabs.DescribeAll` (the same code live editing uses to resolve a `catalogId` to a prefab): every `StageData.randomMapObjects[].prefabs[]`, `stageTilePrefabs.flatTilePrefabs[]` and `mapSpecificTilesPrefabs[]` of every stage of the map, `MapData.shrines[]`, and `MapData.randomObjectsOverride[].prefabs[]`. The scene-wide channels come from the loaded scene only, so they are listed once rather than once per map: the `SpawnInteractables` `chest`, `chestFree` and `rails[]`, the `EffectManager` boombox, and the `RandomObjectPlacer` `chargeShrineSpawns` and `greedShrineSpawns` (`RandomMapObject` channels whose `prefabs` are listed as `interactable/chargeShrine/<i>` and `interactable/greedShrine/<i>`; they are not the never-read `randomObjects[]` field). `PaletteCatalogBuilder` turns the counts into `catalogId` strings in the shapes documented in `level-format.md`, grouped by stage and category. Map lookup goes through `CatalogPrefabs.TryFindMap`, which memoizes the last `MapData` it found: the builder resolves a prefab per entry to name and thumbnail it, and scanning every loaded asset per entry made that path quadratic.

The tabs are `All` plus one per category the catalog has (random objects, flat tiles, specific tiles, shrines, interactables, overrides, and `Packs` when a pack asset is listed), so all stages of a category share one tab and the stage is shown in the tooltip. A tab shows the thumbnail of its category's first entry, or a short text label when that entry has no thumbnail. The grid is 4 columns by 6 rows of 61.6 px slots. The wheel over the palette or the `<` and `>` buttons change page, one page per notch, stopping at the first and last page without wrapping. Changing the search or the tab returns to the first page, or to the page holding the selected entry when the filters leave it visible. Selecting an entry elsewhere (picking an object in the world) also jumps to its page. The slots are a fixed pool that is rebound on every filter or page change.

Every entry names the map its asset was walked from (`PaletteEntry.Map`; pack entries have none), and pick-block prefers an entry of the loaded map over an identically named one from another map. Hovering a slot of a cross-map asset shows that map in the tooltip's third line (`Desert · Stage 1 flat tiles`), so an asset that is not from the level's own map is visible before it is placed. Placing one is intentional: the level file stores the id with its own map prefix, and `CatalogPrefabs.Resolve` reads the named map's `MapData` when the id is re-resolved, so the object survives save and reload in a level whose `map` is a different map.

Assets from installed packs under `UserData/LevelPacks/` are appended after the game entries as one `Packs` tab, on every map, because packs are not map-scoped. Each entry has the `catalogId` `bundle:<pack>/<asset>`, the asset name as its display name and stage 0, and `PackPaletteEntries` orders them by pack id and then asset name. A pack with a valid `manifest.json` lists the manifest assets its bundle also holds; a manifest asset the bundle lacks is warned about once and not listed, and a bundle asset the manifest omits is not listed. A pack with no manifest, or an invalid one, lists every prefab in its bundle. Packs load once per session and a missing pack is cached, so a pack installed after launch appears only after a relaunch. With no packs installed the palette has no `Packs` tab and no extra entries. Pack entries behave exactly as before the catalog spanned several maps: they are mapless, they carry no map tag, and the walk never touches them.

Each slot shows a rendered thumbnail of the prefab, or its display name when the prefab could not be rendered. The selected slot has a white border and a lighter fill; the hovered slot has a lighter fill. Hovering a slot shows a tooltip with the display name, the `catalogId` and the stage and category (with the origin map for a cross-map entry); hovering a tab shows the category name. Clicking a slot selects it, and the selection is `EditorPalette.Selection.Current`, a `CatalogId`, with a `Changed` event that the placement tool reads. Clicks and wheel input are read from Unity's `Input` directly instead of through a UGUI `EventSystem`, so the game's Rewired input module is untouched. The palette is rebuilt each time editor mode is entered, so it follows the map; a selection that is not in the new catalog is cleared. Building logs `EditorPalette: built <n> entries for <map> (<map> <n>, ... ) in <ms> ms` with one count per map, one for packs, and the milliseconds the synchronous part took: the catalog walk, the entry list, the canvas and the tab icons. Measured on the Proton build with five maps and 487 entries: 191 ms on the first entry into editor mode in a session, 12-15 ms on every entry after that.

Thumbnails are drawn by `PrefabThumbnails`. It does not instantiate the prefab, because that would run the game's own `Awake` and `Start` code (shrines, chests). Instead it copies each `MeshFilter` and `SkinnedMeshRenderer` mesh, its shared materials and its pose relative to the prefab root onto a proxy object parked at y = -5000 on layer 31, skipping meshes whose names mark a lower LOD (`LODGroup.GetLODs` is not exposed by the interop assemblies). A temporary camera that only sees layer 31, with a transparent background, a 30 degree field of view and a 3/4 view framed from the combined bounds, and a directional light on the same layer render it into a 128x128 render texture, which is read back into a `Texture2D`. Fog is switched off for the render and restored. The proxy, camera and light are destroyed after each render. A prefab with no mesh, empty bounds or a render that throws yields no thumbnail and the slot shows its name instead.

Textures are kept in a static `ThumbnailCache` keyed by `catalogId`, including failed renders, so re-entering editor mode on the same catalog renders nothing. Rendering is spread over frames rather than done in the entry frame: `PaletteThumbnailQueue` holds the ids to draw (the visible page first, then the filtered set, then the whole catalog) and `EditorPalette.Tick` takes four at a time, rebinding the slots after each batch. Opening the palette therefore costs one layout pass no matter how many maps are listed, and a page turn costs at most the batch budget. Only the tab icons are drawn during the rebuild, one per category. When a drain finishes the palette logs `EditorPalette: rendered <n> thumbnails in <ms> ms (cached <k>)`; a cold drain of the five-map catalog logged 480 thumbnails spread over about 119 s of wall clock at the ~4 fps the headless harness runs at, none of it in the entry frame. A few Forest prefabs (the ones labelled `Forest<stage>_Prefab<n>`) show their names instead of an image; the cause per prefab has not been checked.

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

The selection ring marks the object's base footprint, not a cross-section of its overall bounds. Radius (`ObjectTools.RingRadius`) is the enclosing circle of the footprint's XZ extents plus 10% clearance, floored at 0.5. The footprint is the union of the object's enabled colliders — solid colliders first, then trigger colliders (a chest's or pot's only body collider is a trigger), falling back to the model-bounds union when there are none. Base Y (`ObjectTools.RingBaseY`) is the physical ground under the footprint centre: a downward `Physics.RaycastAll` that skips the object's own colliders and triggers, picking the hit nearest the object's origin (`ObjectTools.SupportY`) so overhanging geometry above a chest cannot lift the ring off its floor; clamped to never sink below the object's own base, except that an origin more than 2 units below the probed ground (an object lowered under a floor, or a ceiling picked as ground) keeps its own base so the ring follows it, and falling back to the tile surface under the object when nothing is hit. The model-bounds union (`ObjectTools.IsModelRenderer` — disabled renderers, particles and `MinimapIcon` skipped) also excludes zero-thickness renderers (`FlatDecalEpsilon`): a pot's flat 9x9 indicator `Quad` at y=5 is a decal, not model geometry, and would balloon the ring. The ring material uses the `UI/Default` shader, which honours `unity_GUIZTestMode`, on render queue 4000, so it draws over terrain and mesh that would occlude it (`Sprites/Default` ignores the ZTest override and would silently depth-hide a ring buried in a large rock's mesh). Setting `MEGABONK_RING_DIAG=1` in the game environment logs one `[ring-diag]` block per selected object (bounds, footprint extents, ground/base Y, radius, shader) for diagnosing ring placement. The Forest ruins (`Castle`, `Ruins (1)`, `Pillar`, `Cube`, `Crate (n)` and similar) are deliberately unpickable: they are scene roots without a `(Clone)` suffix placed by the tile-object generator, so they are not in the genId index, and the `tileObject:####` entries are empty `Forest0_PrefabN(Clone)` placeholders with no renderers. Making them editable would need a new genId category and index order, which the edit replay depends on. Selection clears when the tool changes. Nothing is picked or placed while the pointer is over the palette.

Dragging an object with the Select tool moves it horizontally. An object resting on the surface (within 2 units of it) keeps its height over the tile surface as it crosses slopes and height changes (`ObjectTools.DragY`). An object floating more than 2 units above the surface, such as the boss portal inside the hanging box, keeps its own height instead and follows the cursor along a horizontal plane at that height (`ObjectTools.RayPlaneXZ`) rather than the ground far behind it, and is pulled towards the nearest mostly horizontal solid surface (a tile top or a collider with an upward normal, `SurfacesNear`, own colliders and triggers ignored) when one is within 1.5 units (`ObjectTools.SnapDistance`). The pull is zero at the edge of that range and total on the surface (`ObjectTools.SnapY`), so the object slows as it approaches a surface and breaks free again with a little more movement. Holding Shift while dragging freezes the horizontal position and changes the height from the vertical mouse movement (0.05 units per pixel, up raises); the object is then treated as floating, with the same snap. Hold Shift before pressing, otherwise the object follows the cursor horizontally until Shift goes down.

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
