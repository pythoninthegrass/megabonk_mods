# Development harness

The mod ships a development-only command channel so a shell script can run a load-and-check cycle against the running game without simulating keyboard or mouse input: load a level, capture the game's own rendered frame, and quit. It is driven by `scripts/run.py`.

## Enabling

The harness is off by default. It runs only if the marker file `<game dir>/harness/enabled` exists when the game starts, so a normal install exposes no command channel.

```sh
uv run scripts/run.py enable    # creates harness/enabled and harness/commands
uv run scripts/run.py disable   # removes the marker
```

Enabling takes effect on the next game launch. When active, the mod logs `DevHarness: enabled, watching '<dir>'` to `MelonLoader/Latest.log`.

The game directory is resolved the same way as in `scripts/game_paths.py`: process environment, then the nearest `.env` found walking up from the current directory or the script, then the built-in default: the CrossOver Steam bottle (`~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk`) on macOS, `C:\Program Files (x86)\Steam\steamapps\common\Megabonk` on Windows. The keys are `MEGABONK_GAME_DIR` (the game directory itself) and `MEGABONK_BOTTLE` (a bottle's `drive_c`).

## Commands

`run.py` writes one JSON file per command into `<game dir>/harness/commands/`. The mod polls that folder twice a second, runs the files in name order, and moves each one to `harness/done/` (accepted) or `harness/rejected/` (unparseable). A command is moved before it runs, so a command that crashes or quits the game is never replayed.

| Command | Wire format | `run.py` |
| --- | --- | --- |
| Load a level and start the run | `{"command":"load-level","path":"<file>"}` | `run.py load <level>` |
| Save the rendered frame as a PNG | `{"command":"screenshot","path":"<file>"}` | `run.py screenshot <out.png>` |
| Freeze gameplay | `{"command":"freeze"}` | `run.py freeze` |
| Resume gameplay | `{"command":"resume"}` | `run.py resume` |
| Make the player survive enemy damage | `{"command":"invulnerable"}` | `run.py invulnerable` |
| Restore normal player damage | `{"command":"vulnerable"}` | `run.py vulnerable` |
| Start or stop the kill-floor heartbeat | `{"command":"heartbeat","enabled":true}` | `run.py heartbeat <on\|off>` |
| Start or stop the cell-change log | `{"command":"cells","enabled":true}` | `run.py cells <on\|off>` |
| Enter or leave editor mode | `{"command":"editor","enabled":true}` | `run.py editor <on\|off>` |
| Hold the camera at a pose | `{"command":"camera","position":[x,y,z],"rotation":[rx,ry,rz]}` | `run.py camera X Y Z --rot RX RY RZ` |
| Return the camera to the game | `{"command":"camera-clear"}` | `run.py camera --clear` |
| Quit the game | `{"command":"quit"}` | `run.py quit` |

`run.py cycle <level> <out.png>` runs load, waits `--settle` seconds (default 5), takes the screenshot, then quits. `--invulnerable` makes the player invulnerable right after the load, before the settle wait. `--freeze` freezes gameplay and `--camera X Y Z RX RY RZ` poses the camera after the settle wait and before the screenshot. `--timeout` (before the subcommand, default 15 seconds) sets how long to wait for each command and for the PNG to appear. The exit code is 0 only if every step succeeded, 1 if a step failed or timed out, and 2 if the harness is not enabled (`run.py` prints `harness not enabled at <dir>; run 'run.py enable' and relaunch the game`).

An unknown command, malformed JSON, or a missing or empty `path` logs `DevHarness: rejected '<file>': <reason>` and moves the file to `rejected/` without touching game state. A command that parses but fails while running logs an error and the game keeps running.

The paths in `load-level` and `screenshot` are interpreted by the game process, so `run.py` converts them (see below).

## Launching under CrossOver

`task game:run` starts `Megabonk.exe` directly in the CrossOver Steam bottle with `cxstart`, with `SteamAppId` and `SteamGameId` set to 3405340. The Steam client must already be running in the bottle; start it from CrossOver first. Launching through the `steam://rungameid` URI is avoided because it can open only the CrossOver window without starting the game, especially from a script. The equivalent command:

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
| What a method actually does | Native code in `GameAssembly`, in Binary Ninja, at the RVA listed above the method in `dump.cs` (also on `DummyDll`'s `[Address]` attribute) |
| A value set in the Unity editor rather than in code | Nowhere in the dump — confirm it in the running game |

`dump.cs` is the complete managed surface and answers most questions on its own, which is why it is worth grepping first; dropping to Binary Ninja is for the cases where the shape of a type is not enough and the actual logic matters.

That last table row covers a whole class of behaviour that is not in code at all. Serialized ScriptableObjects, scene and prefab data are not emitted by the dumper, so the game's Rewired key bindings live in an input-manager asset: `MyInputManager`'s action names (`Jump`, `Interact`, `MapOverlay`, and the rest) are plainly visible in `dump.cs`, but which physical key each action binds is not recorded anywhere the dump can see. Questions of that shape get settled by trying it in the game, not by reading harder.

## Editor mode

Editor mode is a freeze-and-fly overlay for surveying a map while a run is active. It works in any run, not only mod-loaded levels. Toggle it with F8, or with `run.py editor on` and `run.py editor off` when the harness is enabled (the harness cannot press keys). F8 is ignored while the game's debug console (F10) is open and while no run is in progress. The game's own `LookHorizontal` and `LookVertical` Rewired axes read zero while the run is paused, which is why look uses Unity's raw mouse axes. Rewired's key bindings live in a serialized asset that is not readable from code, so that F8 collides with no game binding is only confirmed by pressing it in the game.

Entering calls `MyTime.Pause`, which stops the run timer, enemy spawning, enemies and the player, and detaches the camera from the player. The camera is the game's own `PlayerCamera` camera, rewritten from `OnLateUpdate` the same way the harness `camera` command does it, so no second camera exists to stack across cycles. The free-fly pose starts at the camera's current position and rotation.

| Input | Effect |
| --- | --- |
| W, A, S, D | Move along the view direction and sideways |
| Space, Left Ctrl | Move up and down in world space |
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

While editor mode is active a toolbar at the top centre of the screen shows six tools and a detail line. The digit keys 1 to 6 select Raise, Lower, Slope, Remove, Place and Select (the last two are in "Object tools" below); Raise is selected the first time editor mode is entered, and the choice persists across entries. Pressing 1 to 4 in normal play does nothing, so the game binds no action to them (confirmed in the game, like F8).

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

## Object tools

Tool 5 (Place) and tool 6 (Select) edit objects. Both snap to cell centres, always: the position is the targeted tile's centre (same origin as `PositionReadout.CellOf`, via `PositionReadout.CellCentre`), at the tile's surface (`Height * tileHeight`, plus half a level on a ramp), with `tileHeight` and the spacing read from the live `StageData.mapParameters`. The yellow tile outline shows the cell an object will land in.

| Tool | Input | Edit |
| --- | --- | --- |
| Place | left click on a tile with a palette item selected | `PlaceObject` at the snapped cell; rotation is the prefab's pitch and roll with yaw set to the camera's yaw plus 180 degrees rounded to 90, so the object faces the camera (assumes a prefab's front is +Z; unconfirmed); scale is the prefab's local scale |
| Select | left click an object | selects it (cyan footprint outline from its combined renderer bounds); clicking the selected object again deselects |
| Select | left click ground with an object selected | `MoveObject` to the snapped cell, keeping rotation and scale |
| Select | `R` / `Shift+R` | `MoveObject` with yaw 90 degrees clockwise / counter-clockwise, keeping pitch, roll and position |
| Select | `Delete` or `Backspace` | `RemoveObject` |
| any | middle click an object | pick block: selects the object's palette entry and switches to Place |

Picking tries a physics raycast first and accepts the hit only when its hierarchy resolves to an indexed object in a `tileObject` or `object:*` category or to an editor-placed object; tiles, walls and fill pieces never resolve. When that finds nothing, the pickable object nearest the cursor's ground point on the XZ plane within half a tile is used. The log line names the path (`raycast` or `nearest`). Selection clears when the tool changes. Nothing is picked or placed while the pointer is over the palette.

Pick block matches a generator-spawned object's prefab name (the `object:{prefabName}:{index}` genId category) against the palette's display names, preferring the current stage's entry, then a stage-independent one (shrines, interactables). An editor-placed object uses the catalogId it was placed with. An object with no matching entry, including every `tileObject`, is logged (`pick block found no palette entry`) and the selection is left alone.

Every action logs `EditorObjectTools: <what> -> <opType>`. Removal destroys the object, so undo must respawn it or removal must switch to deactivation. Pure logic lives in `object_tool.cs` (snap, facing, the ops), `object_picker.cs` (nearest object) and `palette_pick.cs` (pick block lookup).
