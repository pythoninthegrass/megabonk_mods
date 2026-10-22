# Development harness

The mod ships a development-only command channel so a shell script can run a load-and-check cycle against the running game without simulating keyboard or mouse input: load a level, capture the game's own rendered frame, and quit. It is driven by `scripts/run.py`.

## Enabling

The harness is off by default. It runs only if the marker file `<game dir>/harness/enabled` exists when the game starts, so a normal install exposes no command channel.

```sh
uv run scripts/run.py enable    # creates harness/enabled and harness/commands
uv run scripts/run.py disable   # removes the marker
```

Enabling takes effect on the next game launch. When active, the mod logs `DevHarness: enabled, watching '<dir>'` to `MelonLoader/Latest.log`.

The game directory is resolved the same way as in `scripts/game_paths.py`: process environment, then the nearest `.env` found walking up from the current directory or the script, then the built-in default: the CrossOver Steam bottle (`~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk`) on macOS, `C:\Program Files (x86)\Steam\steamapps\common\Megabonk` on Windows. The keys are `MEGABONK_GAME_DIR` (the game directory itself) and `MEGABONK_BOTTLE` (a bottle's `drive_c`). On macOS, `MEGABONK_MACOS_RUNTIME` (`wine`, the default, or `crossover`) picks the runtime and `MEGABONK_WINE` points at the plain Wine binary.

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
| Start or stop the kill-floor heartbeat | `{"command":"heartbeat","enabled":true}` | `run.py heartbeat <on\|off>` |
| Start or stop the cell-change log | `{"command":"cells","enabled":true}` | `run.py cells <on\|off>` |
| Enter or leave editor mode | `{"command":"editor","enabled":true}` | `run.py editor <on\|off>` |
| Hold the camera at a pose | `{"command":"camera","position":[x,y,z],"rotation":[rx,ry,rz]}` | `run.py camera X Y Z --rot RX RY RZ` |
| Return the camera to the game | `{"command":"camera-clear"}` | `run.py camera --clear` |
| Quit the game | `{"command":"quit"}` | `run.py quit` |
| Relaunch the test level in editor mode | Multiple commands | `run.py relaunch [level]` |

`run.py cycle <level> <out.png>` runs load, waits `--settle` seconds (default 5), takes the screenshot, then quits. `--invulnerable` makes the player invulnerable right after the load, before the settle wait. `--freeze` freezes gameplay and `--camera X Y Z RX RY RZ` poses the camera after the settle wait and before the screenshot. `--timeout` (before the subcommand, default 15 seconds) sets how long to wait for each command and for the PNG to appear. The exit code is 0 only if every step succeeded, 1 if a step failed or timed out, and 2 if the harness is not enabled (`run.py` prints `harness not enabled at <dir>; run 'run.py enable' and relaunch the game`).

`run.py relaunch` quits the running game, starts a fresh process through `task game:run` (`task crossover:run` when `MEGABONK_MACOS_RUNTIME=crossover`), waits for a new `DevHarness: enabled` log entry, then polls the in-game Steamworks client before loading `levels/example-forest.mblevel.json`. It retries the load until `KillFloor: armed` appears, then enables invulnerability and editor mode. It allows at least 60 seconds for readiness checks, even when `--timeout` is lower. Pass an optional level path to use a different level file. Use this command between interactive editor sessions; do not send another `load` to an existing run.

An unknown command, malformed JSON, a missing or empty `path`, or a command that fails while running logs an error and moves the file to `rejected/` without replaying it.

The paths in `load-level` and `screenshot` are interpreted by the game process, so `run.py` converts them (see below).

## Launching under Wine (macOS)

Plain Wine is the default macOS runtime. It runs the same Steam bottle that CrossOver created (`~/Library/Application Support/CrossOver/Bottles/Steam`), so saves, Steam login and the installed game carry over. The setup was verified with Wine 11.18 and DXVK-macOS on Apple silicon with Rosetta.

```sh
task wine:install       # pinned Wine build and DXVK DLLs; skips what is already installed
task game:steam         # Steam client, detached; wait about 30 seconds for logon
task game:melonloader:install
task game:run           # Megabonk.exe, detached
```

`task wine:install` runs `wine:app` and `wine:dxvk` from `taskfiles/wine.yml`. The pins (version, URL, sha256 for each) are defined once in that file's `vars` and can be overridden by exporting `WINE_VERSION`, `WINE_URL`, `WINE_SHA256`, `DXVK_VERSION`, `DXVK_URL` or `DXVK_SHA256`, or by setting them in `.env`, which the root `taskfile.yml` loads with `dotenv` for every task. Each step downloads its archive to a temporary directory and checks the sha256 before extracting or copying anything, so a mismatch stops the task with nothing changed. An unset or empty override falls back to the pin. `wine:dxvk` needs an existing Wine prefix (the Steam bottle, by default under CrossOver's `Bottles/Steam`); on a machine without one it prints `wine:dxvk skipped: no Wine prefix at <path>` and exits 0, leaving the Wine build installed, so run `task wine:dxvk` again once the prefix exists. The repo does not create a prefix.

- **Wine build.** The Gcenx `wine-devel` 11.18 build is extracted to `~/Applications/wine11/Wine Devel.app`, then the quarantine attribute is removed and the app is ad-hoc signed so Gatekeeper lets it run. Set `MEGABONK_WINE` to use a different binary. Wine 7.7 (the Game Porting Toolkit cask) crashes Steam with an unhandled page fault, and Homebrew's `wine-stable` is disabled.
- **DXVK.** Wine's own Direct3D path reports no supported feature level on macOS, and Unity fails with `Failed to initialize player`. The task copies the x64 `d3d11.dll` and `d3d10core.dll` from DXVK-macOS (async build, `v1.10.3-20230507-repack`) into the prefix's `drive_c/windows/system32`. The first run saves the DLLs it replaces in `drive_c/windows/dxvk-orig/` and never overwrites that backup. `drive_c/windows/dxvk.installed` records the installed pin. MoltenVK ships inside the Wine build. The DXVK release publishes no checksum for its archive, so the pinned sha256 was computed locally from the downloaded file and is not independently verified.
- **`USER=crossover`.** Wine takes the Windows profile name from the macOS user. Without the override Wine creates `C:\users\<macOS user>` with no saves, and the game starts from an empty profile. CrossOver ran as `crossover`, so the saves live in `drive_c/users/crossover`. `scripts/launch_game.py` sets `USER` and `LOGNAME` to `crossover` for every Wine call it makes.
- **`-silent`.** The Steam UI renders as a black window under Wine because its embedded browser does not draw. `-silent` keeps the main window closed while the client still logs on and serves Steamworks. The client must be logged on before the game starts, or Steamworks fails to initialize. It cannot show a login prompt, so sign in through the macOS Steam client or CrossOver if the session expires.
- **`version.dll`.** MelonLoader needs `version=native,builtin`. `scripts/install_melonloader.py` sets it with `reg add` through the selected runtime's Wine; the game launch also passes it in `WINEDLLOVERRIDES`, along with the native DXVK DLLs.
- **Detaching.** `scripts/launch_game.py` starts Wine with `subprocess.Popen(..., start_new_session=True)`, so the game and Steam survive the task runner and a closed terminal. A trailing `&` does not work: Task's shell kills its background children when the task ends.

Shut Steam down with `wine 'C:\Program Files (x86)\Steam\steam.exe' -shutdown` (same `WINEPREFIX` and `USER`), never while the game is running, because that can break the Steamworks session and Cloud sync.

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

The harness does not skip the level-up dialog, move the player, or press menu buttons. Use `freeze` to stop an idle player dying during a screenshot, or `invulnerable` when enemies must keep moving.

## Character selection

A level started through the mod (`LevelLoaderPatch.LoadAndStart`, used by F6 and `load-level`) spawns Tony McZoom. The loader assigns the static `CharacterMenu.selectedCharacter` (ECharacter 13) just before `MapController.StartNewMap`; the player spawn reads that static, so no `RunConfig` field is involved. `Preferences.selectedCharacter` is the saved setting and is never written: after a mod-loaded run `Saves/LocalDir/config.json` still holds the player's own choice.

If the assignment throws, `CharacterOverride.TryApply` returns a warning that the loader logs, and the run starts with the character the menu last selected. The id lives in `character_override.cs` and mirrors `ECharacter.TonyMcZoom` in the il2cpp dump.

To confirm which character spawned, run `run.py cycle` and read the screenshot; the saved character in `config.json` differs from the one on screen when the override works.

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

## Player teleport: static findings, unconfirmed in the running game

Everything in this section comes from `dump.cs` and from Ghidra pseudocode of `GameAssembly.dll` (sha256 starting `4350a7ae25ba`). Nothing was run in the game, so each behaviour below is an unconfirmed reading of decompiled code. Callee names are inferred by matching the callee's RVA to a `dump.cs` entry; a name marked "inferred from RVA" has no other evidence.

The player is a `MyPlayer` (static `MyPlayer.Instance`, offset `0x8`) with a `PlayerMovement playerMovement` field at `0x28`, a `PlayerRenderer playerRenderer` at `0x20` and a `PlayerInput playerInput` at `0x48`. `PlayerMovement` is a Rigidbody controller, not a `CharacterController`: it has `private Rigidbody rb` at `0x48` and a `CapsuleCollider playerCollider` at `0x140`, and `dump.cs` lists no `CharacterController` field on either class.

| Method | RVA | VA | Signature |
| --- | --- | --- | --- |
| `PlayerMovement.TeleportPlayer` | `0x343A80` | `0x180343A80` | `void TeleportPlayer(Vector3 pos)` |
| `PlayerMovement.TeleportPlayerBackToBounds` | `0x343870` | `0x180343870` | `void TeleportPlayerBackToBounds(Vector3 pos)` |
| `PlayerMovement.VerifyPosition` | `0x344220` | `0x180344220` | `private void VerifyPosition()` |
| `MyPlayer.TeleportPlayerImmediate` | `0x4B6E00` | `0x1804B6E00` | `void TeleportPlayerImmediate(Vector3 position, Vector3 dir, Vector3 cameraDir, float cameraPitch = 20)` |
| `MyPlayer.TeleportPlayerNextStage` | `0x4B6EB0` | `0x1804B6EB0` | `void TeleportPlayerNextStage()` |
| `MyPlayer.TeleportEnd` | `0x4B6D90` | `0x1804B6D90` | `private void TeleportEnd()` |
| `MyPlayer.Spawn` | `0x4B6770` | `0x1804B6770` | `void Spawn(Vector3 position, Vector3 direction, bool useHeightOffset = false)` |

What the decompiled code does:

- `PlayerMovement.TeleportPlayer(pos)` reads `rb` (`this + 0x48`) and `playerHeight` (`this + 0x104`). It calls one Rigidbody setter with `pos + playerHeight * 0.5 * <a Vector3 static>` (the static is read from the `Vector3` class statics at offset `0x18` to `0x20`, which is most likely `Vector3.up`), then a second Rigidbody setter with the `Vector3` static at offset `0`, which is most likely `Vector3.zero`. The two setters sit at RVAs `0x232D2C0` and `0x232E6E0`, which `dump.cs` does not name; from the argument shapes they are probably `Rigidbody.position` and `Rigidbody.velocity`, so the method most likely moves the body and zeroes its velocity. It does not touch `transform` directly and does not touch the camera. Confidence: medium for the shape, low for the two setter names.
- `PlayerMovement.TeleportPlayerBackToBounds(pos)` does the same position and velocity writes with an offset of `4.0` times the same `Vector3` static instead of half the player height, then writes the position `pos - playerHeight * <Vector3 static>` into a `CheckLanding(Vector3 point, Vector3 normal)` call (RVA `0x33C240`, resolved from `dump.cs`) and calls `ResetAerialJumps()` (RVA `0x3424A0`). It is the out-of-bounds recovery path.
- `PlayerMovement.VerifyPosition()` is the game's own recovery from a fall. When `grounded` (`0xDF`) is true it stores the current rigidbody position into `lastGroundedPosition` (`0x244`) as long as the ground object is not a specific component type. When not grounded and the rigidbody `y` is below a static float minus `10.0`, it writes the saved `lastGroundedPosition` back into the rigidbody (the same position and velocity pair as `TeleportPlayer`) and calls `CheckLanding`. The static float is read from a class at RVA-unresolved handle `DAT_182f59150`; it is likely the map's lowest `y` or a kill plane, but that is unconfirmed. Consequence worth testing: a teleport target that is more than 10 units below that static, or a stale `lastGroundedPosition`, may be undone by this method on the next tick.
- `MyPlayer.TeleportPlayerImmediate(position, dir, cameraDir, cameraPitch)` calls `PlayerMovement.TeleportPlayer(position)` on `playerMovement`, `PlayerRenderer.ForceRotation(dir)` (RVA `0x345B50`, resolved from `dump.cs`) on `playerRenderer`, and `PlayerInput.SetSpawnDirection(cameraDir, cameraPitch)` (RVA `0x33ABF0`, resolved from `dump.cs`) on `playerInput`. It therefore sets position, body facing and look direction in one call; the camera is driven through `PlayerInput`'s spawn direction rather than by moving the camera object. It does not set `isTeleporting` and does not touch enemies.
- `MyPlayer.TeleportPlayerNextStage()` activates `teleportEffect` (`this + 0x70`), sets `isTeleporting` (`0x128`) to true and schedules a delayed `Invoke` of a method by name (probably `TeleportEnd`, by name only) after `1.0` second. `TeleportEnd()` calls `RemoveAllStatusEffects` (RVA `0x4495C0`, resolved from `dump.cs`) on the object at `inventory + 0x38` and deactivates the effect object. This is the portal transition between stages, not a position move, and it does not take a position argument.
- `MyPlayer.Spawn(position, direction, useHeightOffset)` is the full respawn: it fires a static `Action` (`A_PrePlayerSpawn`), runs `TryInit`, calls `StartPlayer` and sets the spawn direction through `PlayerInput`. It is heavier than a teleport and is not a candidate.

Candidate call sequence, unconfirmed: with `var me = MyPlayer.Instance;`, call `me.TeleportPlayerImmediate(position, dir, cameraDir)` where `position` is the world position wanted and `dir` and `cameraDir` are the current forward vectors (read from the player's `transform` first so the facing does not change), then read `me.transform.position` after a frame. `PlayerMovement.TeleportPlayer(position)` alone is the narrower call if the facing must be untouched. Both hold the `Vector3` by pointer in native code, so call them through the Il2CppInterop proxies on the main thread.

Open questions about the teleport, all needing the running game:

- Whether `TeleportPlayer` moves the body to exactly `position + playerHeight * 0.5` on `y`, which would put the feet at `position.y`, or whether `position` is already the centre height.
- Whether `VerifyPosition` reverts a teleport whose target is below the threshold static, and what that static holds.
- Whether the camera follows with no extra call, and whether `PlayerCamera` needs a reset after a long jump.
- What a teleport does to enemies already chasing the player (nothing is called on them), to the kill-floor heartbeat, and to `cells` output.
- What field to return from a harness command: the position actually reached is `MyPlayer.Instance.transform.position` read one frame after the call, together with the requested position, so a revert shows up as a difference.

## Level-up dialog: static findings, unconfirmed in the running game

The same caveats as the teleport section apply: `dump.cs` plus Ghidra pseudocode only, nothing run in the game, and callee names inferred from RVA.

The level-up window is `LevelupScreen : BaseEncounterWindow`, owned by `EncounterWindows` (field `levelupScreen`, `0x20`). `LevelupScreen.upgradePicker` (`0x48`) is an `UpgradePicker` whose `UpgradeButton[] buttons` (`0x20`) hold the offers. An `UpgradeButton` keeps its offer as `IUpgradable upgradable` (`0xA8`), `List<StatModifier> upgradeOffer` (`0xB0`), `bool isItem` (`0xC8`) and `ERarity rarity` (`0xD8`).

| Method | RVA | VA |
| --- | --- | --- |
| `LevelupScreen.ShowLevelupScreen()` | `0x54F7E0` | `0x18054F7E0` |
| `LevelupScreen.OnClose()` (override) | `0x54F040` | `0x18054F040` |
| `LevelupScreen.CloseLevelupScreen()` / `Leave()` (same address) | `0x54EA30` | `0x18054EA30` |
| `UpgradeButton.SelectUpgrade()` | `0x55F0A0` | `0x18055F0A0` |
| `UpgradePicker.SelectUpgrade(IUpgradable, List<StatModifier>, UpgradeButton, ERarity)` | `0x561500` | `0x180561500` |
| `UpgradePicker.AutoSelectUpgrade()` (static) | `0x560BE0` | `0x180560BE0` |
| `PlayerInventory.AddUpgrade(IUpgradable, List<StatModifier>, ERarity)` | `0x4DFD80` | `0x1804DFD80` |
| `EncounterWindows.RewardFinished()` | `0x3E09D0` | `0x1803E09D0` |
| `EncounterWindows.OnLevelUp(int level)` | `0x3E02B0` | `0x1803E02B0` |
| `MyTime.Unpause()` | `0x3E5DB0` | `0x1803E5DB0` |

`LevelupScreen.ChooseOffer` and `UpgradeButton.OnClick` are listed at RVA `0x3321E0`, the shared empty stub, so they have no logic of their own and must not be hooked; the choice goes through `UpgradeButton.SelectUpgrade`. `LevelupScreen.Open` (RVA `0x54F110`) could not be decompiled (see "Using Ghidra through REA").

Detecting an open dialog. `LevelupScreen` has `public static bool isLevelingUp` at statics offset `0`. `ShowLevelupScreen` calls `UpgradePicker.ShuffleUpgrades(encounterType)`, writes `isLevelingUp = false`, then writes `isLevelingUp = true` and fires the static `A_LevelupEnabled` action only when `encounterType` (`0x9C`) is `0` (`EEncounter.Levelup`). `OnClose` writes `isLevelingUp = false`, hides `window` (`0x20`) and `effects` (`0x28`), calls `MyTime.Unpause()` and fires the static `A_LevelUpClose` action for `Levelup`. If the picker has no upgrades to offer (`numUpgrades` at `0x30` is below `1`) and the type is not `ShadyGuy` (`7`), `ShowLevelupScreen` calls `CloseLevelupScreen` immediately. So `LevelupScreen.isLevelingUp` is the candidate dialog-open flag for level-ups; `EncounterWindows.encounterInProgress` (`0x58`) is the broader flag for any encounter window, and is true while `activeEncounterWindow` (`0x48`) is set.

Applying a choice. `UpgradeButton.SelectUpgrade()` returns early while `Time.time` is below `UpgradePicker.banishCooldownOverAtTime` (`0x64`). For a non-item offer (`isItem` false) it calls `UpgradePicker.SelectUpgrade(upgradable, upgradeOffer, this, rarity)`. When `banishMode` (`0x60`) is false, that method calls `PlayerInventory.AddUpgrade(upgradable, upgradeOffer, rarity)` on `MyPlayer.Instance.inventory`, then `EncounterWindows.RewardFinished()` on the encounter-windows object reached through a static instance's field at `0x30` (`dump.cs` lists `encounterWindows` at `0x30` of a class at RVA-unresolved statics handle `DAT_182f9a528`), then `UpgradePicker.StopBanishMode()` on the screen's picker. `RewardFinished` calls the active window's `OnClose` virtual (vtable slot at `0x188`), clears `activeEncounterWindow`, sets `encounterInProgress` false and `closedEncounterThisFrame` true, and, when the reward queue is empty, calls `MyTime.Unpause()` and fires `A_WindowClosed`; when the queue is not empty it calls `PopReward` to open the next window. For an item offer (`isItem` true) the button path adds the item through `ItemInventory.AddItem(EItem)` (RVA `0x4421C0`) and charges gold with `PlayerInventory.ChangeGold(-price)` when `price` (`0xDC`) is above zero, then finishes the same way.

`UpgradePicker.AutoSelectUpgrade()` is a static method that picks an offer without any UI. It calls `InventoryUtility.GetRandomUpgrades()` (RVA `0x420EF0`), scores each entry from its rarity (`Rarity.GetUpgradeOfferRarity(luck)` with a `PlayerStats.GetStat` luck value), keeps the highest, calls `PlayerInventory.AddUpgrade` on the player's inventory, and posts a `ServerFeed.SetFeed` message with the upgrade name. It does not call `RewardFinished` or touch `LevelupScreen`. `EncounterWindows.OnLevelUp(level)` calls it for each gained level, instead of queuing a `Levelup` encounter with `AddEncounter`, when a field at `0x68` of an object reached through a static (`DAT_182f7c7c0`, unresolved) equals `1` and a comparison against the current level holds; that reads as a game option or mode that auto-picks upgrades, and what sets it is not established.

Candidate call sequence for choosing without a click, unconfirmed: when `LevelupScreen.isLevelingUp` is true, take the open `LevelupScreen` (the `levelupScreen` field of the `EncounterWindows` instance), read `upgradePicker.buttons`, pick one `UpgradeButton` whose `isItem` is false, and call its `SelectUpgrade()`; this runs the same code path as a click. It is gated by `banishCooldownOverAtTime`, so a call right after the window opens may be ignored and has to be retried. `LevelupScreen.Skip` (RVA `0x54FF20`) and `Refresh` (RVA `0x54F5F0`) were not decompiled.

Open questions about the level-up dialog, all needing the running game:

- How to obtain the `EncounterWindows` instance from the mod, since the decompiled code reaches it through a static whose class was not identified; `Object.FindObjectOfType` on `EncounterWindows` or `LevelupScreen` is the fallback.
- Whether calling `UpgradeButton.SelectUpgrade()` from a mod thread produces the same result as a click, including that `isLevelingUp` goes false, `MyTime.paused` goes false and the stat change is applied; and what a harness freeze (`MyTime.Pause`) does to the window while it is open.
- Whether `OnClose` runs `MyTime.Unpause()` while the editor-mode freeze is active, which would unfreeze a run the harness meant to keep frozen.
- Whether `AutoSelectUpgrade` alone leaves an open dialog behind when called while the window is showing.
- Result fields a harness command should return: `isLevelingUp` before and after, the chosen upgrade's name (read from `UpgradeButton.t_name` or the `upgradable`) and its `rarity`, and the player's character level.

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
